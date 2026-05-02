"""Dummy adapter for local simulation without real quantum hardware.

This adapter provides a drop-in replacement for cloud backends using
local simulation. It's useful for:
- Development and testing without cloud access
- Offline development
- Quick prototyping and debugging
- Running circuits when API tokens are not available

The dummy adapter uses the built-in OriginIR simulator to execute circuits
and returns results in the same format as cloud backends.

Usage:
    from uniqc.task.adapters.dummy_adapter import DummyAdapter

    # Create adapter with default settings (perfect simulator)
    adapter = DummyAdapter()

    # Noisy simulation from chip characterization
    from uniqc.task.adapters.originq_adapter import OriginQAdapter
    originq = OriginQAdapter()
    chip = originq.get_chip_characterization("origin:wuyuan:d5")
    adapter = DummyAdapter(chip_characterization=chip)

    # Explicit noise model
    adapter = DummyAdapter(noise_model={'depol_1q': 0.01, 'depol_2q': 0.05})

    # Submit and query (results are immediately available)
    task_id = adapter.submit(originir_circuit, shots=1000)
    result = adapter.query(task_id)

Environment Variable:
    UNIQC_DUMMY: Set to 'true', '1', or 'yes' to enable dummy mode
    globally. When set, all task submissions use local simulation instead
    of real quantum backends.
"""

from __future__ import annotations

__all__ = ["DummyAdapter", "UNIQC_DUMMY"]

import hashlib
import os
from typing import TYPE_CHECKING, Any

from ..result_types import UnifiedResult
from .base import TASK_STATUS_FAILED, TASK_STATUS_SUCCESS, DryRunResult, QuantumAdapter

if TYPE_CHECKING:
    from uniqc.cli.chip_info import ChipCharacterization

# Check environment variable for global dummy mode
UNIQC_DUMMY = os.environ.get("UNIQC_DUMMY", "").lower() in ("true", "1", "yes")


class DummyAdapter(QuantumAdapter):
    """Local simulator adapter that mimics cloud backends.

    This adapter executes circuits locally using the built-in OriginIR
    simulator instead of submitting to real quantum hardware. It provides
    the same interface as cloud adapters, making it a drop-in replacement.

    Features:
    - Immediate result availability (no waiting for queue)
    - Optional noise simulation from chip characterization or explicit model
    - Same result format as cloud backends
    - Deterministic task IDs (based on circuit hash)

    Attributes:
        name: Adapter identifier ('dummy').
        chip_characterization: Optional chip characterization for realistic noise.
        noise_model: Optional explicit noise configuration dict.
        available_qubits: List of qubit indices available for simulation.

    Example:
        >>> from uniqc.task.adapters.originq_adapter import OriginQAdapter
        >>> originq = OriginQAdapter()
        >>> chip = originq.get_chip_characterization("origin:wuyuan:d5")
        >>> adapter = DummyAdapter(chip_characterization=chip)
        >>> task_id = adapter.submit("QINIT 2\\nH q[0]\\nCNOT q[0] q[1]\\nMEASURE")
        >>> result = adapter.query(task_id)
        >>> print(result['status'])
        'success'
    """

    name = "dummy"

    def __init__(
        self,
        noise_model: dict[str, Any] | None = None,
        available_qubits: list[int] | None = None,
        available_topology: list[list[int]] | None = None,
        chip_characterization: ChipCharacterization | None = None,
    ) -> None:
        """Initialize the DummyAdapter.

        Args:
            noise_model: Optional noise model configuration.
                Supported keys:
                - 'depol_1q': Depolarizing error rate for single-qubit gates (0.0 to 1.0)
                - 'depol_2q': Depolarizing error rate for two-qubit gates
                - 'readout': Readout error rate
                - 'depol': Fallback depolarizing rate for both 1Q and 2Q (used if
                  depol_1q/depol_2q not set)
            available_qubits: List of available qubit indices.
            available_topology: List of [u, v] edges for qubit connectivity.
            chip_characterization: Chip characterization data. When provided, the
                adapter automatically derives realistic noise parameters from the
                per-qubit and per-pair calibration data (T1/T2, gate fidelities,
                readout errors). This is the recommended way to configure noise.

        Raises:
            MissingDependencyError: If the C++ simulator extension (`uniqc_cpp`)
                required by the simulation path is not available.
        """
        from ..optional_deps import MissingDependencyError, check_simulation

        if not check_simulation("cpp"):
            raise MissingDependencyError(
                "uniqc_cpp",
                install_hint=(
                    "Reinstall unified-quantum for the current Python version "
                    "or build the package from source so the C++ simulator extension is available."
                ),
            )

        self.chip_characterization = chip_characterization
        self.noise_model = noise_model
        self.available_qubits = available_qubits or []
        self.available_topology = available_topology or []
        self._cache: dict[str, dict[str, Any]] = {}
        self._simulator_cls: type | None = None
        self._error_loader: Any | None = None

    def _get_simulator_cls(self) -> type:
        """Lazily load the simulator class."""
        if self._simulator_cls is None:
            from uniqc.simulator import OriginIR_Simulator

            self._simulator_cls = OriginIR_Simulator
        return self._simulator_cls

    def _get_error_loader(self) -> Any | None:
        """Build error loader from chip characterization or explicit noise model.

        This is called lazily on first simulation to avoid importing heavy
        dependencies at construction time.
        """
        if self._error_loader is not None:
            return self._error_loader

        if self.chip_characterization is not None:
            self._error_loader = self._build_error_loader_from_chip(
                self.chip_characterization
            )
        elif self.noise_model is not None:
            self._error_loader = self._build_error_loader_from_model(self.noise_model)
        else:
            self._error_loader = None

        return self._error_loader

    def _build_error_loader_from_chip(self, chip: ChipCharacterization) -> Any:
        """Convert chip characterization data to a gate-specific error loader.

        Uses per-qubit single-gate fidelity and per-pair two-qubit gate fidelity
        to derive realistic gate error rates. Readout errors are also extracted.

        Args:
            chip: Chip characterization with calibration data.

        Returns:
            ErrorLoader_GateSpecificError instance, or None if chip has no gate data.
        """
        from uniqc.simulator.error_model import (
            ErrorLoader_GateSpecificError,
            Depolarizing,
            TwoQubitDepolarizing,
        )

        # Collect single-qubit gate errors
        sq_errors: dict[int, float] = {}
        for sq_data in chip.single_qubit_data:
            if sq_data.single_gate_fidelity is not None:
                sq_errors[sq_data.qubit_id] = 1.0 - sq_data.single_gate_fidelity

        # Collect two-qubit gate errors (use best fidelity per edge)
        tq_errors: dict[tuple[int, int], float] = {}
        for tq_data in chip.two_qubit_data:
            for gate in tq_data.gates:
                if gate.fidelity is not None:
                    edge = tuple(sorted((tq_data.qubit_u, tq_data.qubit_v)))
                    existing = tq_errors.get(edge)
                    if existing is None or (1.0 - gate.fidelity) < existing:
                        tq_errors[edge] = 1.0 - gate.fidelity

        # Collect readout errors: p(misread | prepared 0), p(misread | prepared 1)
        ro_errors: dict[int, list[float]] = {}
        for sq_data in chip.single_qubit_data:
            if sq_data.avg_readout_fidelity is not None:
                err = 1.0 - sq_data.avg_readout_fidelity
                ro_errors[sq_data.qubit_id] = [err / 2.0, err / 2.0]

        # Build generic_error: average over all qubits for gates not explicitly listed
        all_sq_errors = list(sq_errors.values())
        generic_1q = sum(all_sq_errors) / len(all_sq_errors) if all_sq_errors else 0.01
        all_tq_errors = list(tq_errors.values())
        generic_2q = sum(all_tq_errors) / len(all_tq_errors) if all_tq_errors else 0.05

        # generic_error: applied to every gate. Depolarizing(p) iterates over all
        # qubits in the opcode and emits a 1q depolarizing error per qubit, so it
        # works correctly for both 1q and 2q gates without needing to distinguish
        # gate arity here.
        generic_error: list[Depolarizing] = [Depolarizing(generic_1q)]
        # gatetype_error: same reasoning — Depolarizing handles any qubit count.
        # Only use TwoQubitDepolarizing in gate_specific_error (exact edge match).
        gatetype_error: dict[str, list[Depolarizing]] = {
            "CNOT": [Depolarizing(generic_2q)],
            "CZ": [Depolarizing(generic_2q)],
            "ISWAP": [Depolarizing(generic_2q)],
        }

        # Per-instance gate errors: use TwoQubitDepolarizing for exact edge matches.
        gate_specific_error: dict[tuple[str, tuple[int, int]], list[Depolarizing]] = {}
        for edge, err in tq_errors.items():
            gate_specific_error[("CNOT", edge)] = [Depolarizing(err)]
            gate_specific_error[("CZ", edge)] = [Depolarizing(err)]

        loader = ErrorLoader_GateSpecificError(
            generic_error=generic_error,
            gatetype_error=gatetype_error,  # type: ignore[arg-type]
            gate_specific_error=gate_specific_error,
        )
        return loader

    def _build_error_loader_from_model(
        self, noise_model: dict[str, Any]
    ) -> Any:
        """Build error loader from an explicit noise model dict.

        Args:
            noise_model: Noise model with optional 'depol_1q', 'depol_2q', 'depol'.

        Returns:
            ErrorLoader_GateSpecificError instance.
        """
        from uniqc.simulator.error_model import (
            ErrorLoader_GateSpecificError,
            Depolarizing,
            TwoQubitDepolarizing,
        )

        depol_1q = noise_model.get("depol_1q", noise_model.get("depol", 0.0))
        depol_2q = noise_model.get("depol_2q", noise_model.get("depol", 0.0))

        generic_error: list[Depolarizing] = [Depolarizing(depol_1q)]
        gatetype_error: dict[str, list[Depolarizing]] = {
            "CNOT": [Depolarizing(depol_2q)],
            "CZ": [Depolarizing(depol_2q)],
            "ISWAP": [Depolarizing(depol_2q)],
        }
        return ErrorLoader_GateSpecificError(
            generic_error=generic_error,
            gatetype_error=gatetype_error,  # type: ignore[arg-type]
            gate_specific_error={},
        )

    def _generate_task_id(self, circuit: str) -> str:
        """Generate a deterministic task ID from circuit content.

        Uses SHA256 hash of the circuit string to create a unique
        but reproducible task identifier.

        Args:
            circuit: The circuit string.

        Returns:
            16-character hex task ID.
        """
        return hashlib.sha256(circuit.encode()).hexdigest()[:16]

    # -------------------------------------------------------------------------
    # Circuit translation
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> str:
        """Return the OriginIR string unchanged.

        The dummy adapter accepts OriginIR directly, so no translation needed.

        Args:
            originir: Circuit in OriginIR format.

        Returns:
            The same OriginIR string.
        """
        return originir

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(
        self,
        circuit: str,
        *,
        shots: int = 1000,
        **kwargs: Any,
    ) -> str:
        """Simulate a circuit locally and cache the result.

        The circuit is executed immediately using the local simulator,
        and results are cached for later retrieval via query().

        Args:
            circuit: Circuit in OriginIR format (or pre-translated).
            shots: Number of measurement shots.
            **kwargs: Additional parameters (ignored for dummy adapter).

        Returns:
            Task ID for result retrieval.
        """
        task_id = self._generate_task_id(circuit)
        try:
            unified_result = self._simulate(circuit, shots)
            self._cache[task_id] = {
                "status": TASK_STATUS_SUCCESS,
                "result": unified_result.to_dict(),
                "unified_result": unified_result,
            }
        except Exception as e:
            self._cache[task_id] = {
                "status": TASK_STATUS_FAILED,
                "error": str(e),
            }
        return task_id

    def submit_batch(
        self,
        circuits: list[str],
        *,
        shots: int = 1000,
        **kwargs: Any,
    ) -> list[str]:
        """Simulate multiple circuits locally.

        Args:
            circuits: List of circuits in OriginIR format.
            shots: Number of measurement shots per circuit.
            **kwargs: Additional parameters (ignored).

        Returns:
            List of task IDs, one per circuit.
        """
        return [self.submit(c, shots=shots) for c in circuits]

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    def query(self, taskid: str) -> dict[str, Any]:
        """Retrieve the cached result for a task.

        Since dummy tasks are executed immediately on submission,
        results are always available instantly.

        Args:
            taskid: Task identifier.

        Returns:
            Result dict with 'status' and 'result' (or 'error') keys.
        """
        cached = self._cache.get(taskid)
        if cached is None:
            return {
                "status": TASK_STATUS_FAILED,
                "error": f"Task '{taskid}' not found in dummy cache",
            }
        result = {"status": cached["status"]}
        if "result" in cached:
            result["result"] = cached["result"]
        if "error" in cached:
            result["error"] = cached["error"]
        return result

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        """Query multiple tasks and merge results.

        Args:
            taskids: List of task identifiers.

        Returns:
            Combined result dict with overall status and merged results.
        """
        results = []
        overall_status = TASK_STATUS_SUCCESS

        for taskid in taskids:
            task_result = self.query(taskid)
            results.append(task_result.get("result", {}))
            if task_result["status"] == TASK_STATUS_FAILED:
                overall_status = TASK_STATUS_FAILED

        return {
            "status": overall_status,
            "result": results,
        }

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if the dummy adapter is available.

        Returns:
            True if the C++ simulation backend is available.
        """
        from ..optional_deps import check_simulation

        return check_simulation("cpp")

    def clear_cache(self) -> None:
        """Clear the internal result cache."""
        self._cache.clear()

    # -------------------------------------------------------------------------
    # Dry-run validation
    # -------------------------------------------------------------------------

    def dry_run(self, originir: str, *, shots: int = 1000, **kwargs: Any) -> DryRunResult:
        """Dry-run validation for the dummy local simulator.

        The dummy adapter always succeeds — it accepts any valid OriginIR string
        and simulates it locally. There are no backend constraints.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        from .base import _dry_run_success

        # Extract qubit count from OriginIR QINIT line
        circuit_qubits: int | None = None
        try:
            for line in originir.splitlines():
                line = line.strip()
                if line.startswith("QINIT"):
                    parts = line.split()
                    if len(parts) >= 2:
                        circuit_qubits = int(parts[1])
                    break
        except Exception:
            pass

        return _dry_run_success(
            (f"Dry-run passed for dummy simulator: OriginIR is valid. Qubits={circuit_qubits}, shots={shots}"),
            backend_name="dummy",
            circuit_qubits=circuit_qubits,
            supported_gates=(
                "H",
                "X",
                "Y",
                "Z",
                "S",
                "T",
                "SX",
                "RX",
                "RY",
                "RZ",
                "CNOT",
                "CZ",
                "SWAP",
                "ISWAP",
                "TOFFOLI",
                "CSWAP",
                "XX",
                "YY",
                "ZZ",
                "XY",
                "MEASURE",
                "BARRIER",
            ),
        )

    def simulate_pmeasure(self, originir: str) -> list[float]:
        """Return exact measurement probabilities (noiseless or noisy).

        Unlike ``_simulate`` (which uses shot sampling), this always returns
        the exact probability vector from ``simulate_pmeasure`` — no sampling
        noise. This is the correct method for fidelity computation where you
        compare two exact distributions.

        Args:
            originir: Circuit in OriginIR format.

        Returns:
            List of probabilities (length = 2 ** n_qubits).
        """
        Simulator = self._get_simulator_cls()
        error_loader = self._get_error_loader()

        if error_loader is not None:
            try:
                from uniqc.simulator import OriginIR_NoisySimulator
            except ImportError:
                sim = Simulator(
                    available_qubits=self.available_qubits,
                    available_topology=self.available_topology,
                )
            else:
                sim = OriginIR_NoisySimulator(
                    backend_type="density_operator",
                    error_loader=error_loader,
                    available_qubits=self.available_qubits,
                    available_topology=self.available_topology,
                    readout_error={},
                )
        else:
            sim = Simulator(
                available_qubits=self.available_qubits,
                available_topology=self.available_topology,
            )

        return sim.simulate_pmeasure(originir)

    def _simulate(self, originir: str, shots: int) -> UnifiedResult:
        """Run simulation using the OriginIR simulator (noiseless or noisy).

        Args:
            originir: Circuit in OriginIR format.
            shots: Number of shots.

        Returns:
            UnifiedResult with measurement probabilities.

        Raises:
            RuntimeError: If simulation fails.
        """
        Simulator = self._get_simulator_cls()
        error_loader = self._get_error_loader()

        # Determine which simulator to use
        if error_loader is not None:
            # Noisy simulation
            try:
                from uniqc.simulator import OriginIR_NoisySimulator
            except ImportError:
                # Fall back to noiseless
                sim = Simulator(
                    available_qubits=self.available_qubits,
                    available_topology=self.available_topology,
                )
            else:
                # Collect readout errors from chip characterization
                readout_error: dict[int, list[float]] = {}
                if self.chip_characterization is not None:
                    for sq_data in self.chip_characterization.single_qubit_data:
                        if sq_data.avg_readout_fidelity is not None:
                            err = 1.0 - sq_data.avg_readout_fidelity
                            readout_error[sq_data.qubit_id] = [err / 2.0, err / 2.0]

                sim = OriginIR_NoisySimulator(
                    backend_type="density_operator",
                    error_loader=error_loader,
                    available_qubits=self.available_qubits,
                    available_topology=self.available_topology,
                    readout_error=readout_error,
                )
        else:
            # Noiseless simulation
            sim = Simulator(
                available_qubits=self.available_qubits,
                available_topology=self.available_topology,
            )

        # Run simulation to get probability distribution
        probs = sim.simulate_pmeasure(originir)
        n_qubits = sim.qubit_num

        # Convert probability list to dict
        prob_dict = {}
        for i, p in enumerate(probs):
            if p > 0:
                bin_key = bin(i)[2:].zfill(n_qubits)
                prob_dict[bin_key] = float(p)

        # Create unified result
        return UnifiedResult.from_probabilities(
            probabilities=prob_dict,
            shots=shots,
            platform="dummy",
            task_id=self._generate_task_id(originir),
        )
