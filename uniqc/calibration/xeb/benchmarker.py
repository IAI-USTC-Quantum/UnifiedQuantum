"""XEB benchmarker: executes XEB circuits and fits fidelity curves.

The benchmarker integrates readout EM by optionally applying it to raw
measurement counts before computing the linear XEB estimator against the
noiseless ideal distribution.
"""

from __future__ import annotations

import pathlib
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import numpy as np

from uniqc.calibration.results import XEBResult, save_calibration_result
from uniqc.calibration.xeb.circuits import (
    generate_1q_xeb_circuits,
    generate_2q_xeb_circuit,
)
from uniqc.calibration.xeb.fitter import compute_linear_xeb, fit_exponential

if TYPE_CHECKING:
    from uniqc.backend_adapter.task.adapters.base import QuantumAdapter

__all__ = ["XEBenchmarker"]


class XEBenchmarker:
    """Cross-entropy benchmarking engine.

    Executes random XEB circuits on a quantum adapter (or dummy backend),
    computes normalized linear XEB values against the noiseless ideal distribution,
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
        self.cache_dir = pathlib.Path(cache_dir) if cache_dir is not None else None
        self._noiseless_sim = self._build_noiseless_simulator()
        self.query_timeout = 300.0
        self.query_interval = 2.0

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
        save_calibration_result(result, type_prefix="xeb_1q", cache_dir=self.cache_dir)
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
        circuits = []
        circuit_depths = []
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
                circuits.append(c)
                circuit_depths.append(d)

        fidelities = _circuit_fidelities(circuits, self)
        for d, fid in zip(circuit_depths, fidelities, strict=True):
            fidelity_by_depth[d].append(fid)

        avg_fidelities = [_finite_mean(fidelity_by_depth[d], depth=d) for d in depths]
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
        save_calibration_result(result, type_prefix="xeb_2q", cache_dir=self.cache_dir)
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

        for fid in _circuit_fidelities(circuits, self):
            fidelity_by_depth[depth].append(fid)

        avg_fid = _finite_mean(fidelity_by_depth[depth], depth=depth)
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
        save_calibration_result(result, type_prefix="xeb_2q_parallel", cache_dir=self.cache_dir)
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
        """Get noisy probability distribution.

        Tries adapter.simulate_pmeasure (DummyAdapter with chip characterization)
        for exact probabilities without shot noise. Falls back to submit/query
        for real cloud backends.
        """
        try:
            # Path 1: DummyAdapter with chip characterization — exact probabilities
            if hasattr(self.adapter, "simulate_pmeasure"):
                probs_list = self.adapter.simulate_pmeasure(originir)
                arr = np.array(probs_list, dtype=float)
                # Apply readout EM in probability space if available
                if self.readout_em is not None:
                    arr = _apply_readout_em_to_probs(arr, self.readout_em, measured_qubits)
                return arr

            # Path 2: Real cloud backends — use shot sampling via submit/query.
            # Cloud jobs are asynchronous; wait for terminal status before reading counts.
            counts = self._submit_and_wait_counts(originir)
            probs = _counts_to_probs(counts, measured_qubits)

            if self.readout_em is not None:
                int_counts: dict[int, int] = {}
                for k, v in counts.items():
                    idx = _outcome_to_int(k, len(measured_qubits))
                    int_counts[idx] = int_counts.get(idx, 0) + int(v)
                mitigated = self.readout_em.mitigate_counts(int_counts, measured_qubits)
                total = sum(mitigated.values())
                if total > 0:
                    probs = {int(k): v / total for k, v in mitigated.items()}

            p_ideal = self._get_ideal_probs(originir)
            n = len(p_ideal) if p_ideal is not None else (2 ** len(measured_qubits))
            arr = np.zeros(n)
            for k, v in probs.items():
                idx = int(k)
                if 0 <= idx < n:
                    arr[idx] = v
            return arr
        except Exception:
            return None

    def _submit_and_wait_counts(self, originir: str) -> dict[Any, int]:
        """Submit a circuit and wait until a cloud backend returns shot counts."""
        task_id = self.adapter.submit(originir, shots=self.shots)
        deadline = time.time() + self.query_timeout

        while True:
            result = self.adapter.query(task_id)
            status = result.get("status", "")
            if status == "success":
                raw = result.get("result", {})
                if hasattr(raw, "counts"):
                    return raw.counts
                if isinstance(raw, dict):
                    return raw
                return {}
            if status == "failed":
                raise RuntimeError(f"XEB circuit failed on backend: {result.get('result') or result.get('error')}")
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for XEB task {task_id}")
            time.sleep(self.query_interval)

    def _submit_batch_and_wait_counts(self, originirs: list[str]) -> list[dict[Any, int]]:
        """Submit circuits as a backend batch and wait for per-circuit counts."""
        if not hasattr(self.adapter, "submit_batch") or not hasattr(self.adapter, "query_batch"):
            return [self._submit_and_wait_counts(originir) for originir in originirs]

        task_ids = self.adapter.submit_batch(originirs, shots=self.shots)
        deadline = time.time() + max(self.query_timeout, self.query_timeout * len(originirs) / 20)

        while True:
            result = self.adapter.query_batch(task_ids)
            status = result.get("status", "")
            if status == "success":
                payload = result.get("result", [])
                if isinstance(payload, dict):
                    return [payload]
                if isinstance(payload, list):
                    if all(isinstance(item, dict) for item in payload):
                        return payload
                    raise RuntimeError(f"Unexpected batch result payload: {payload!r}")
                raise RuntimeError(f"Unexpected batch result payload: {payload!r}")
            if status == "failed":
                raise RuntimeError(f"XEB batch failed on backend: {result.get('result') or result.get('error')}")
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for XEB batch task(s) {task_ids}")
            time.sleep(self.query_interval)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_mean(values: list[float], *, depth: int) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        raise RuntimeError(f"No valid XEB values for depth={depth}")
    return float(np.mean(arr))


def _counts_to_probs(counts: dict, measured_qubits: list[int]) -> dict[int, float]:
    """Normalize counts dict to integer-indexed probabilities."""
    total = sum(counts.values())
    if total == 0:
        return {}
    width = len(measured_qubits)
    probs: dict[int, float] = {}
    for key, value in counts.items():
        idx = _outcome_to_int(key, width)
        probs[idx] = probs.get(idx, 0.0) + (value / total)
    return probs


def _outcome_to_int(outcome: Any, width: int) -> int:
    """Convert backend outcome keys to the local probability-vector index."""
    if isinstance(outcome, int):
        return outcome
    text = str(outcome).strip()
    if text.startswith("0b"):
        return int(text, 2)
    if set(text) <= {"0", "1"} and len(text) > 1:
        return int(text[-width:] if width > 0 else text, 2)
    return int(text)


def _mean_fidelities_by_depth(
    circuits: list, depths: list[int], n_circuits: int, benchmarker: XEBenchmarker
) -> list[float]:
    """Compute mean normalized XEB value for each depth from a flat circuit list."""
    fidelity_by_depth: dict[int, list[float]] = {d: [] for d in depths}
    fidelities = _circuit_fidelities(circuits, benchmarker)
    idx = 0
    for d in depths:
        for _ in range(n_circuits):
            if idx >= len(fidelities):
                break
            fid = fidelities[idx]
            idx += 1
            fidelity_by_depth[d].append(fid)
    means = []
    for d in depths:
        vals = np.asarray(fidelity_by_depth[d], dtype=float)
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            raise RuntimeError(f"No valid XEB values for depth={d}")
        means.append(float(np.mean(vals)))
    return means


def _circuit_fidelities(circuits: list, benchmarker: XEBenchmarker) -> list[float]:
    """Compute circuit fidelities, using backend batch submission when available."""
    if not circuits:
        return []

    if hasattr(benchmarker.adapter, "simulate_pmeasure"):
        return [_circuit_fidelity(c, benchmarker) for c in circuits]

    originirs = [c.originir for c in circuits]
    measured_qubits_list = [
        list(getattr(c, "measure_list", None) or range(c.qubit_num))
        for c in circuits
    ]
    counts_list = benchmarker._submit_batch_and_wait_counts(originirs)
    if len(counts_list) != len(circuits):
        raise RuntimeError(
            f"Batch returned {len(counts_list)} result(s) for {len(circuits)} circuit(s)"
        )

    fidelities = []
    for originir, counts, measured_qubits in zip(originirs, counts_list, measured_qubits_list, strict=True):
        p_ideal = benchmarker._get_ideal_probs(originir)
        if p_ideal is None:
            raise RuntimeError("Failed to compute ideal probability distribution for XEB circuit")
        probs = _counts_to_probs(counts, measured_qubits)
        if benchmarker.readout_em is not None:
            int_counts: dict[int, int] = {}
            for k, v in counts.items():
                idx = _outcome_to_int(k, len(measured_qubits))
                int_counts[idx] = int_counts.get(idx, 0) + int(v)
            mitigated = benchmarker.readout_em.mitigate_counts(int_counts, measured_qubits)
            total = sum(mitigated.values())
            if total > 0:
                probs = {int(k): v / total for k, v in mitigated.items()}

        p_noisy = np.zeros(len(p_ideal))
        for k, v in probs.items():
            idx = int(k)
            if 0 <= idx < len(p_noisy):
                p_noisy[idx] = v
        fidelities.append(compute_linear_xeb(p_ideal, p_noisy, normalized=True))
    return fidelities


def _apply_readout_em_to_probs(
    probs_arr: np.ndarray, readout_em: Any, measured_qubits: list[int]
) -> np.ndarray:
    """Apply readout EM confusion matrix to a probability vector.

    Works in probability space (exact pmeasure output) rather than counts,
    using the public ReadoutEM probability interface.
    """
    from uniqc.qem import ReadoutEM

    if not isinstance(readout_em, ReadoutEM):
        return probs_arr
    try:
        probs = {i: float(p) for i, p in enumerate(probs_arr)}
        mitigated = readout_em.mitigate_probabilities(probs, measured_qubits)
    except Exception:
        return probs_arr
    result = np.zeros_like(probs_arr, dtype=float)
    for k, v in mitigated.items():
        idx = int(k)
        if 0 <= idx < len(result):
            result[idx] = float(v)
    return result


def _circuit_fidelity(circuit, benchmarker: XEBenchmarker) -> float:
    """Compute normalized linear XEB for one circuit against its ideal distribution."""
    originir = circuit.originir
    measured_qubits = list(getattr(circuit, "measure_list", None) or range(circuit.qubit_num))

    # Get ideal probabilities
    p_ideal = benchmarker._get_ideal_probs(originir)
    # Get noisy probabilities
    p_noisy = benchmarker._get_noisy_probs(originir, measured_qubits)

    if p_ideal is None:
        raise RuntimeError("Failed to compute ideal probability distribution for XEB circuit")
    if p_noisy is None:
        raise RuntimeError("Failed to compute measured probability distribution for XEB circuit")

    return compute_linear_xeb(p_ideal, p_noisy, normalized=True)
