"""Readout calibrator for single-qubit and two-qubit measurement errors.

Generates calibration circuits for all computational basis states,
executes them on the given adapter, builds confusion matrices,
and saves results to the calibration cache.
"""

from __future__ import annotations

import pathlib
import time
from datetime import datetime, timezone
from typing import Any

from uniqc.circuit_builder import Circuit

if False:
    from uniqc.backend_adapter.task.adapters.base import QuantumAdapter

__all__ = ["ReadoutCalibrator"]


class ReadoutCalibrator:
    """Calibrates readout (measurement) errors for 1-qubit and 2-qubit systems.

    For 1-qubit: runs two circuits to build a 2×2 confusion matrix:
        [[P(0|0), P(1|0)],
         [P(0|1), P(1|1)]]

    For 2-qubit: runs four circuits to build a 4×4 confusion matrix:
        rows = measured outcome (00,01,10,11)
        cols = prepared state (00,01,10,11)

    Results are automatically saved to ``~/.uniqc/calibration_cache/`` with
    an ISO-8601 ``calibrated_at`` timestamp.

    Args:
        adapter: A ``QuantumAdapter`` instance (e.g. ``DummyAdapter``).
            Must implement ``submit`` and ``query`` methods.
        shots: Number of measurement shots per calibration circuit.
        cache_dir: Directory to save calibration results.
            Defaults to ``~/.uniqc/calibration_cache/``.
    """

    def __init__(
        self,
        adapter: QuantumAdapter,
        shots: int = 1000,
        cache_dir: str | pathlib.Path | None = None,
    ) -> None:
        self.adapter = adapter
        self.shots = shots
        if cache_dir is None:
            cache_dir = pathlib.Path.home() / ".uniqc" / "calibration_cache"
        self.cache_dir = pathlib.Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def calibrate_1q(self, qubit: int) -> dict[str, Any]:
        """Calibrate readout for a single qubit.

        Args:
            qubit: Qubit index.

        Returns:
            A dict with keys: ``qubit``, ``type="readout_1q"``,
            ``confusion_matrix`` (2×2 list), ``assignment_fidelity``,
            ``calibrated_at``, ``backend``.
        """
        from uniqc.calibration.results import ReadoutCalibrationResult, save_calibration_result

        # Run calibration circuits
        counts_0 = self._run_prepared_state([], qubit)  # |0⟩: identity
        counts_1 = self._run_prepared_state([("X", qubit)], qubit)  # |1⟩

        # Build 2×2 confusion matrix
        # Row 0: measured=0; Row 1: measured=1
        # Col 0: prepared=0; Col 1: prepared=1
        n0 = sum(counts_0.values())
        n1 = sum(counts_1.values())

        p00 = counts_0.get(0, 0) / n0 if n0 > 0 else 0.0  # P(meas=0|prep=0)
        p10 = counts_0.get(1, 0) / n0 if n0 > 0 else 0.0  # P(meas=1|prep=0)
        p01 = counts_1.get(0, 0) / n1 if n1 > 0 else 0.0  # P(meas=0|prep=1)
        p11 = counts_1.get(1, 0) / n1 if n1 > 0 else 0.0  # P(meas=1|prep=1)

        confusion = [[p00, p01], [p10, p11]]
        assignment_fid = (p00 + p11) / 2.0

        result = ReadoutCalibrationResult(
            calibrated_at=_utc_now(),
            backend=getattr(self.adapter, "name", "unknown"),
            type="readout_1q",
            qubit=qubit,
            confusion_matrix=tuple(tuple(row) for row in confusion),
            assignment_fidelity=assignment_fid,
        )
        save_calibration_result(result, type_prefix="readout_1q", cache_dir=self.cache_dir)
        return result.to_dict()

    def calibrate_2q(self, qubit_u: int, qubit_v: int) -> dict[str, Any]:
        """Calibrate joint readout for a two-qubit pair.

        Args:
            qubit_u: First qubit index.
            qubit_v: Second qubit index.

        Returns:
            A dict with keys: ``qubit`` (tuple), ``type="readout_2q"``,
            ``confusion_matrix`` (4×4 list), ``assignment_fidelity``,
            ``calibrated_at``, ``backend``.
        """
        from uniqc.calibration.results import ReadoutCalibrationResult, save_calibration_result

        # 4 basis states: |00⟩, |01⟩, |10⟩, |11⟩
        # Index in confusion matrix: 0=|00⟩, 1=|01⟩, 2=|10⟩, 3=|11⟩
        prep_circuits = [
            ([], 0),                                         # |00⟩ → idx 0
            ([("X", qubit_v)], 2),                          # |01⟩ → idx 2
            ([("X", qubit_u)], 1),                          # |10⟩ → idx 1
            ([("X", qubit_u), ("X", qubit_v)], 3),          # |11⟩ → idx 3
        ]

        confusion = [[0.0] * 4 for _ in range(4)]
        ns = [0.0] * 4

        for gates, prep_idx in prep_circuits:
            counts = self._run_prepared_state_2q(gates, qubit_u, qubit_v)
            n_total = sum(counts.values())
            ns[prep_idx] = n_total
            for outcome, cnt in counts.items():
                confusion[outcome][prep_idx] = cnt / n_total if n_total > 0 else 0.0

        assignment_fid = sum(confusion[i][i] for i in range(4)) / 4.0

        result = ReadoutCalibrationResult(
            calibrated_at=_utc_now(),
            backend=getattr(self.adapter, "name", "unknown"),
            type="readout_2q",
            qubit=(qubit_u, qubit_v),
            confusion_matrix=tuple(tuple(row) for row in confusion),
            assignment_fidelity=assignment_fid,
        )
        save_calibration_result(result, type_prefix="readout_2q", cache_dir=self.cache_dir)
        return result.to_dict()

    def calibrate_qubits(self, qubits: list[int]) -> dict[int, dict[str, Any]]:
        """Calibrate readout for multiple single qubits.

        Args:
            qubits: List of qubit indices.

        Returns:
            Dict mapping qubit index → calibration result dict.
        """
        return {q: self.calibrate_1q(q) for q in qubits}

    def calibrate_pairs(
        self, pairs: list[tuple[int, int]]
    ) -> dict[tuple[int, int], dict[str, Any]]:
        """Calibrate joint readout for multiple qubit pairs.

        Args:
            pairs: List of (qubit_u, qubit_v) tuples.

        Returns:
            Dict mapping (u, v) → calibration result dict.
        """
        return {(u, v): self.calibrate_2q(u, v) for u, v in pairs}

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _run_prepared_state(
        self, prep_gates: list[tuple[str, int]], qubit: int
    ) -> dict[int, int]:
        """Run a 1-qubit calibration circuit and return measurement counts.

        Args:
            prep_gates: List of (gate_name, qubit) gates to apply before measure.
            qubit: Qubit index.

        Returns:
            Dict mapping measured bit (0 or 1) → count.
        """
        c = Circuit(1)
        for gate, q in prep_gates:
            c.add_gate(gate, qubits=[q])
        c.measure(qubit)  # measure qubit to next available classical bit
        return self._submit_and_measure(c)

    def _run_prepared_state_2q(
        self,
        prep_gates: list[tuple[str, int]],
        qubit_u: int,
        qubit_v: int,
    ) -> dict[int, int]:
        """Run a 2-qubit calibration circuit and return measurement counts.

        Args:
            prep_gates: List of (gate_name, qubit) gates.
            qubit_u: First qubit index.
            qubit_v: Second qubit index.

        Returns:
            Dict mapping measured bitstring (0-3) → count.
            Bitstring encoding: bit 0 = qubit_u (LSB), bit 1 = qubit_v.
        """
        c = Circuit(2)
        for gate, q in prep_gates:
            c.add_gate(gate, qubits=[q])
        c.measure(qubit_u)
        c.measure(qubit_v)
        return self._submit_and_measure_2q(c, qubit_u, qubit_v)

    def _submit_and_measure(self, circuit: Circuit) -> dict[int, int]:
        """Submit a 1-qubit circuit and return counts as {0: n0, 1: n1}.

        Polls the cloud backend until the task completes (up to 60s timeout)
        to ensure we get actual shot counts rather than a "running" status.
        """
        originir = circuit.originir
        task_id = self.adapter.submit(originir, shots=self.shots)

        # Poll until task completes (cloud backends are async by default)
        timeout = 300.0
        interval = 2.0
        elapsed = 0.0
        while elapsed < timeout:
            result = self.adapter.query(task_id)
            status = result.get("status", "")
            if status == "success":
                unified = result.get("result")
                if hasattr(unified, "counts"):
                    counts = unified.counts
                elif isinstance(unified, dict):
                    counts = unified
                else:
                    counts = {}
                return {_outcome_to_int(k, 1): v for k, v in counts.items()}
            if status == "failed":
                raise RuntimeError(f"Readout calibration circuit failed: {result.get('result') or result.get('error')}")
            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(f"Timed out waiting for readout calibration task {task_id}")

    def _submit_and_measure_2q(
        self, circuit: Circuit, qubit_u: int, qubit_v: int
    ) -> dict[int, int]:
        """Submit a 2-qubit circuit, return counts as {0..3: n}.

        Converts simulator outcome indices (0="00", 1="01", 2="10", 3="11")
        to integers where qubit_u is the LSB.
        Polls the cloud backend until the task completes (up to 60s timeout).
        """
        originir = circuit.originir
        task_id = self.adapter.submit(originir, shots=self.shots)

        # Poll until task completes
        timeout = 300.0
        interval = 2.0
        elapsed = 0.0
        while elapsed < timeout:
            result = self.adapter.query(task_id)
            status = result.get("status", "")
            if status == "success":
                unified = result.get("result")
                if hasattr(unified, "counts"):
                    counts = unified.counts
                elif isinstance(unified, dict):
                    counts = unified
                else:
                    counts = {}
                out = {}
                for k, v in counts.items():
                    k_int = _outcome_to_int(k, 2)
                    out[k_int] = v
                return out
            if status == "failed":
                raise RuntimeError(f"Readout calibration circuit failed: {result.get('result') or result.get('error')}")
            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(f"Timed out waiting for readout calibration task {task_id}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _outcome_to_int(outcome: Any, width: int) -> int:
    if isinstance(outcome, int):
        return outcome
    text = str(outcome).strip()
    if text.startswith("0b"):
        return int(text, 2)
    if set(text) <= {"0", "1"}:
        return int(text[-width:] if width > 0 else text, 2)
    return int(text)
