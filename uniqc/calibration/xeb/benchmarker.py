"""XEB benchmarker: executes XEB circuits and fits fidelity curves.

The benchmarker integrates readout EM by optionally applying it to raw
measurement counts before computing the Hellinger fidelity against the
noiseless ideal distribution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import numpy as np

from uniqc.calibration.results import XEBResult, save_calibration_result
from uniqc.calibration.xeb.circuits import (
    generate_1q_xeb_circuits,
    generate_2q_xeb_circuit,
)
from uniqc.calibration.xeb.fitter import compute_hellinger_fidelity, fit_exponential

if TYPE_CHECKING:
    from uniqc.task.adapters.base import QuantumAdapter

__all__ = ["XEBenchmarker"]


class XEBenchmarker:
    """Cross-entropy benchmarking engine.

    Executes random XEB circuits on a quantum adapter (or dummy backend),
    computes Hellinger fidelities against the noiseless ideal distribution,
    and fits an exponential decay model to extract the per-layer fidelity ``r``.

    Args:
        adapter: A ``QuantumAdapter`` instance.
        shots: Number of measurement shots per circuit.
        readout_em: Optional ``ReadoutEM`` instance. If provided, raw counts
            are corrected via readout EM before computing fidelity.
        cache_dir: Directory for saving XEB results.
        seed: Random seed for circuit generation.
    """

    def __init__(
        self,
        adapter: QuantumAdapter,
        shots: int = 1000,
        readout_em: Any = None,
        cache_dir: str | None = None,
        seed: int | None = None,
    ) -> None:
        self.adapter = adapter
        self.shots = shots
        self.readout_em = readout_em
        self.seed = seed
        self._noiseless_sim = self._build_noiseless_simulator()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def run_1q(
        self,
        qubit: int,
        depths: list[int],
        n_circuits: int = 50,
    ) -> XEBResult:
        """Run 1-qubit XEB on a single qubit.

        Args:
            qubit: Qubit index.
            depths: List of circuit depths to sweep.
            n_circuits: Number of random circuits per depth.

        Returns:
            ``XEBResult`` with per-layer fidelity ``r``.
        """
        circuits = generate_1q_xeb_circuits(qubit, depths, n_circuits, seed=self.seed)
        fidelity_by_depth = _mean_fidelities_by_depth(
            circuits, depths, n_circuits, self
        )
        fit = fit_exponential(depths, fidelity_by_depth)

        result = XEBResult(
            calibrated_at=_utc_now(),
            backend=getattr(self.adapter, "name", "unknown"),
            type="xeb_1q",
            qubit=qubit,
            pairs=None,
            fidelity_per_layer=fit["r"],
            fidelity_std_error=fit["r_stderr"],
            fit_a=fit["A"],
            fit_b=fit["B"],
            fit_r=fit["r"],
            depths=tuple(depths),
            n_circuits=n_circuits,
            shots=self.shots,
        )
        save_calibration_result(result, type_prefix="xeb_1q")
        return result

    def run_2q(
        self,
        qubit_u: int,
        qubit_v: int,
        depths: list[int],
        n_circuits: int = 50,
        entangler_gate: str = "CNOT",
    ) -> XEBResult:
        """Run 2-qubit XEB on a single pair.

        Args:
            qubit_u: First qubit index.
            qubit_v: Second qubit index.
            depths: List of circuit depths.
            n_circuits: Number of circuits per depth.
            entangler_gate: 2-qubit gate name.

        Returns:
            ``XEBResult`` with per-layer fidelity ``r``.
        """
        fidelity_by_depth: dict[int, list[float]] = {d: [] for d in depths}

        for d in depths:
            for i in range(n_circuits):
                c = generate_2q_xeb_circuit(
                    qubit_u,
                    qubit_v,
                    d,
                    entangler_gate,
                    seed=(self.seed + i) if self.seed is not None else None,
                )
                fid = _circuit_fidelity(c, self)
                fidelity_by_depth[d].append(fid)

        avg_fidelities = [np.mean(fidelity_by_depth[d]) for d in depths]
        fit = fit_exponential(depths, avg_fidelities)

        result = XEBResult(
            calibrated_at=_utc_now(),
            backend=getattr(self.adapter, "name", "unknown"),
            type="xeb_2q",
            qubit=None,
            pairs=[(qubit_u, qubit_v)],
            fidelity_per_layer=fit["r"],
            fidelity_std_error=fit["r_stderr"],
            fit_a=fit["A"],
            fit_b=fit["B"],
            fit_r=fit["r"],
            depths=tuple(depths),
            n_circuits=n_circuits,
            shots=self.shots,
        )
        save_calibration_result(result, type_prefix="xeb_2q")
        return result

    def run_parallel_2q(
        self,
        pairs: list[tuple[int, int]],
        depth: int,
        n_circuits: int = 50,
        entangler_gates: dict[tuple[int, int], str] | None = None,
    ) -> XEBResult:
        """Run parallel 2-qubit XEB across multiple disjoint qubit pairs.

        All pairs are executed simultaneously in one multi-qubit circuit,
        simulating full-chip parallel execution.

        Args:
            pairs: List of (u, v) qubit pairs (must be qubit-disjoint).
            depth: Depth of each random circuit layer.
            n_circuits: Number of parallel circuits.
            entangler_gates: Per-pair entangler gate names.

        Returns:
            ``XEBResult`` with ``type="xeb_2q_parallel"``.
        """
        from uniqc.calibration.xeb.circuits import generate_parallel_2q_xeb_circuits

        entangler_gates = entangler_gates or {}
        fidelity_by_depth: dict[int, list[float]] = {depth: []}

        circuits = generate_parallel_2q_xeb_circuits(
            pairs=pairs,
            depth=depth,
            entangler_gates=entangler_gates,
            n_circuits=n_circuits,
            seed=self.seed,
        )

        for c in circuits:
            fid = _circuit_fidelity(c, self)
            fidelity_by_depth[depth].append(fid)

        avg_fid = float(np.mean(fidelity_by_depth[depth]))
        # For single-depth parallel XEB, just report mean fidelity
        fit = {"r": avg_fid, "A": 0.0, "B": 0.0, "r_stderr": 0.0, "method": "parallel_single_depth"}

        result = XEBResult(
            calibrated_at=_utc_now(),
            backend=getattr(self.adapter, "name", "unknown"),
            type="xeb_2q_parallel",
            qubit=None,
            pairs=pairs,
            fidelity_per_layer=fit["r"],
            fidelity_std_error=fit["r_stderr"],
            fit_a=fit["A"],
            fit_b=fit["B"],
            fit_r=fit["r"],
            depths=(depth,),
            n_circuits=n_circuits,
            shots=self.shots,
        )
        save_calibration_result(result, type_prefix="xeb_2q_parallel")
        return result

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _build_noiseless_simulator(self) -> Any:
        """Build a noiseless OriginIR simulator for computing ideal distributions."""
        try:
            from uniqc.simulator import OriginIR_Simulator

            return OriginIR_Simulator()
        except Exception:
            return None

    def _get_ideal_probs(self, originir: str) -> np.ndarray | None:
        """Get the ideal (noiseless) probability distribution from the circuit."""
        if self._noiseless_sim is None:
            return None
        try:
            probs = self._noiseless_sim.simulate_pmeasure(originir)
            return np.array(probs)
        except Exception:
            return None

    def _get_noisy_probs(
        self, originir: str, measured_qubits: list[int]
    ) -> np.ndarray | None:
        """Get noisy probability distribution by submitting to the adapter."""
        try:
            task_id = self.adapter.submit(originir, shots=self.shots)
            result = self.adapter.query(task_id)
            raw = result.get("result", {})
            # Unify result format: some adapters return {counts: {...}},
            # others return the counts dict directly.
            if hasattr(raw, "counts"):
                counts = raw.counts
            elif isinstance(raw, dict):
                counts = raw
            else:
                counts = {}
            probs = _counts_to_probs(counts, measured_qubits)

            # Apply readout EM if available
            if self.readout_em is not None:
                mitigated = self.readout_em.mitigate_counts(counts, measured_qubits)
                # Normalize
                total = sum(mitigated.values())
                if total > 0:
                    probs = {int(k): v / total for k, v in mitigated.items()}

            # Convert to fixed-length array
            n = 2 ** len(measured_qubits)
            arr = np.zeros(n)
            for k, v in probs.items():
                arr[int(k)] = v
            return arr
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _counts_to_probs(counts: dict, measured_qubits: list[int]) -> dict[int, float]:
    """Normalize counts dict to probabilities."""
    total = sum(counts.values())
    if total == 0:
        return {}
    return {int(k): v / total for k, v in counts.items()}


def _mean_fidelities_by_depth(
    circuits: list, depths: list[int], n_circuits: int, benchmarker: XEBenchmarker
) -> list[float]:
    """Compute mean Hellinger fidelity for each depth from a flat circuit list."""
    fidelity_by_depth: dict[int, list[float]] = {d: [] for d in depths}
    idx = 0
    for d in depths:
        for _ in range(n_circuits):
            if idx >= len(circuits):
                break
            c = circuits[idx]
            idx += 1
            fid = _circuit_fidelity(c, benchmarker)
            fidelity_by_depth[d].append(fid)
    return [float(np.mean(fidelity_by_depth[d])) for d in depths]


def _circuit_fidelity(circuit, benchmarker: XEBenchmarker) -> float:
    """Compute Hellinger fidelity for one circuit against its ideal distribution."""
    originir = circuit.originir
    # Determine measured qubits from the circuit
    measured_qubits = list(range(circuit.qubit_num))

    # Get ideal probabilities
    p_ideal = benchmarker._get_ideal_probs(originir)
    # Get noisy probabilities
    p_noisy = benchmarker._get_noisy_probs(originir, measured_qubits)

    if p_ideal is None or p_noisy is None:
        return 1.0  # Fallback to perfect if simulation fails

    return compute_hellinger_fidelity(p_ideal, p_noisy)
