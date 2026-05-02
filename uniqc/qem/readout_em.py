"""Unified readout error mitigation.

Provides a single interface for applying readout EM to measurement counts,
automatically dispatching to 1-qubit or 2-qubit calibration as needed.
Internally calls the ``ReadoutCalibrator`` from ``uniqc.calibration.readout``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from uniqc.task.adapters.base import QuantumAdapter

__all__ = ["ReadoutEM"]


class ReadoutEM:
    """Unified readout error mitigator.

    This is the primary interface for applying readout EM to measurement results.
    It wraps a ``ReadoutCalibrator`` and provides mitigation for arbitrary
    measurement counts.

    The mitigator automatically selects:
    - **1-qubit calibration** for single-qubit measurement results
    - **2-qubit calibration** for two-qubit joint measurement results
    - **Per-qubit 1-qubit calibration** (sequential approximation) for >2 qubits

    Args:
        adapter: A ``QuantumAdapter`` instance for running calibration circuits.
        max_age_hours: Maximum acceptable age of cached calibration data in hours.
        cache_dir: Directory for calibration cache. Defaults to
            ``~/.uniqc/calibration_cache/``.
        shots: Number of shots per calibration circuit.
    """

    def __init__(
        self,
        adapter: QuantumAdapter,
        max_age_hours: float = 24.0,
        cache_dir: str | None = None,
        shots: int = 1000,
    ) -> None:
        from uniqc.calibration.readout import ReadoutCalibrator

        self.adapter = adapter
        self.max_age_hours = max_age_hours
        self.shots = shots
        self._calibrator = ReadoutCalibrator(
            adapter=adapter, shots=shots, cache_dir=cache_dir
        )
        # Cache of loaded M3Mitigator instances: (qubit_ident) → M3Mitigator
        self._mitigators: dict[str, Any] = {}

    def mitigate_counts(
        self,
        counts: dict[int, int],
        measured_qubits: list[int],
    ) -> dict[int, float]:
        """Apply readout EM to measurement counts.

        Automatically dispatches to the appropriate calibration:
        - 1 qubit → 1q calibrator
        - 2 qubits → 2q calibrator
        - N>2 qubits → sequential per-qubit 1q mitigation

        Args:
            counts: Dict mapping outcome (int) → observed count.
            measured_qubits: List of qubit indices that were measured.
                The order matters for the bitstring encoding.

        Returns:
            Dict mapping outcome → corrected count (float, total preserved).
        """
        n = len(measured_qubits)
        if n == 1:
            return self._mitigate_1q(counts, measured_qubits[0])
        elif n == 2:
            return self._mitigate_2q(counts, measured_qubits[0], measured_qubits[1])
        else:
            return self._mitigate_nq(counts, measured_qubits)

    def mitigate_probabilities(
        self,
        probs: dict[int, float] | dict[str, float],
        measured_qubits: list[int],
    ) -> dict[int, float]:
        """Apply readout EM to a probability dictionary.

        Args:
            probs: Dict mapping outcome → probability.
            measured_qubits: List of measured qubit indices.

        Returns:
            Dict mapping outcome (int) → corrected probability.
        """
        # Normalize string keys to int
        if probs and isinstance(next(iter(probs)), str):
            probs = {int(k): v for k, v in probs.items()}
        n = len(measured_qubits)
        if n == 1:
            return self._mitigate_probs_1q(probs, measured_qubits[0])
        elif n == 2:
            return self._mitigate_probs_2q(probs, measured_qubits[0], measured_qubits[1])
        else:
            return self._mitigate_probs_nq(probs, measured_qubits)

    # -------------------------------------------------------------------------
    # 1q mitigation
    # -------------------------------------------------------------------------

    def _mitigate_1q(
        self, counts: dict[int, int], qubit: int
    ) -> dict[int, float]:
        """Apply 1-qubit readout EM to counts."""
        mit = self._get_mitigator_1q(qubit)
        return mit.mitigate_counts(counts)

    def _mitigate_probs_1q(
        self, probs: dict[int, float], qubit: int
    ) -> dict[int, float]:
        """Apply 1-qubit readout EM to probabilities."""
        mit = self._get_mitigator_1q(qubit)
        return mit.mitigate_probabilities(probs)

    def _get_mitigator_1q(self, qubit: int):
        """Get or create a cached M3Mitigator for a single qubit."""
        key = f"1q_{qubit}"
        if key not in self._mitigators:
            from uniqc.qem.m3 import M3Mitigator

            self._mitigators[key] = M3Mitigator(
                max_age_hours=self.max_age_hours,
                backend=getattr(self.adapter, "name", "unknown"),
                qubit=qubit,
            )
        return self._mitigators[key]

    # -------------------------------------------------------------------------
    # 2q mitigation
    # -------------------------------------------------------------------------

    def _mitigate_2q(
        self, counts: dict[int, int], q0: int, q1: int
    ) -> dict[int, float]:
        """Apply 2-qubit joint readout EM to counts."""
        mit = self._get_mitigator_2q(q0, q1)
        return mit.mitigate_counts(counts)

    def _mitigate_probs_2q(
        self, probs: dict[int, float], q0: int, q1: int
    ) -> dict[int, float]:
        """Apply 2-qubit joint readout EM to probabilities."""
        mit = self._get_mitigator_2q(q0, q1)
        return mit.mitigate_probabilities(probs)

    def _get_mitigator_2q(self, q0: int, q1: int):
        """Get or create a cached M3Mitigator for a qubit pair."""
        key = f"2q_{q0}_{q1}"
        if key not in self._mitigators:
            from uniqc.qem.m3 import M3Mitigator

            self._mitigators[key] = M3Mitigator(
                max_age_hours=self.max_age_hours,
                backend=getattr(self.adapter, "name", "unknown"),
                qubit=(q0, q1),
            )
        return self._mitigators[key]

    # -------------------------------------------------------------------------
    # Nq mitigation (per-qubit sequential approximation)
    # -------------------------------------------------------------------------

    def _mitigate_nq(
        self, counts: dict[int, int], qubits: list[int]
    ) -> dict[int, float]:
        """Apply per-qubit readout EM sequentially for n>2 qubits.

        This is an approximation: each qubit is corrected independently
        using its 1-qubit confusion matrix, applied in order.
        """
        result = {int(k): float(v) for k, v in counts.items()}
        for q in qubits:
            result = self._apply_1q_matrix(result, q)
        return result

    def _mitigate_probs_nq(
        self, probs: dict[int, float], qubits: list[int]
    ) -> dict[int, float]:
        """Apply per-qubit readout EM sequentially to probabilities."""
        result = {int(k): float(v) for k, v in probs.items()}
        for q in qubits:
            result = self._apply_1q_matrix_probs(result, q)
        return result

    def _apply_1q_matrix(
        self, counts: dict[int, float], qubit: int
    ) -> dict[int, float]:
        """Apply 1-qubit confusion matrix to an N-qubit counts vector.

        This marginalizes over all other qubits and applies the 1q correction.
        """
        mit = self._get_mitigator_1q(qubit)
        # Get the 1q confusion matrix
        cal = mit.calibration_result
        C = np.array(cal["confusion_matrix"])  # 2x2: [p(meas|prep)]

        n_qubits = int(np.log2(max(counts.keys()) + 1))
        # _mitigate_nq uses tensor-product approximation: handled by _tensor_apply below

        # Proper implementation: apply 1q matrix via tensor product with identity
        return self._tensor_apply(counts, C, n_qubits, qubit)

    def _tensor_apply(
        self, counts: dict[int, float], C: np.ndarray, n_total: int, target_qubit: int
    ) -> dict[int, float]:
        """Apply a 2x2 1q confusion matrix C to the target qubit in an n-qubit system.

        Uses the tensor product structure: full_matrix = I⊗...⊗C⊗...⊗I.
        """
        n = 2 ** n_total
        full_C = np.eye(n)
        # Build full matrix via iterative Kronecker product
        # Start from rightmost qubit (LSB)
        mat = C.copy()
        for _ in range(n_total - 1):
            mat = np.kron(mat, np.eye(2))

        # Shift the matrix to the correct position (target_qubit from LSB)
        # Already in correct order since we iterate from target to MSB
        # Actually, Kronecker order: result[i] = Σ_j mat[i,j] * counts[j]
        # For target_qubit=0 (LSB): full = C ⊗ I ⊗ I ⊗ ...
        # For target_qubit=1: full = I ⊗ C ⊗ I ⊗ ...
        if target_qubit != 0:
            # Build with correct ordering
            mats = [np.eye(2) if i != target_qubit else C for i in range(n_total - 1, -1, -1)]
            full_C = mats[0]
            for m in mats[1:]:
                full_C = np.kron(full_C, m)

        n_obs = np.zeros(n)
        for outcome, cnt in counts.items():
            n_obs[int(outcome)] = float(cnt)

        n_corr = full_C @ n_obs
        n_corr = np.clip(n_corr, 0, None)
        total = n_obs.sum()
        if total > 0 and n_corr.sum() > 0:
            n_corr *= total / n_corr.sum()

        return {int(i): float(v) for i, v in enumerate(n_corr)}

    def _apply_1q_matrix_probs(
        self, probs: dict[int, float], qubit: int
    ) -> dict[int, float]:
        """Apply 1-qubit confusion matrix to an N-qubit probability vector."""
        counts = {k: int(v * 1000) for k, v in probs.items()}  # scale to counts
        corrected = self._apply_1q_matrix(counts, qubit)
        total_counts = sum(counts.values())
        if total_counts > 0:
            factor = total_counts / sum(corrected.values())
            return {k: v * factor for k, v in corrected.items()}
        return corrected
