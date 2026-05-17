"""Tests for ``uniqc.qem.readout_em.ReadoutEM``.

These tests exercise the mitigator end-to-end using a fake adapter and a
hand-built :class:`ReadoutCalibrationResult` so no cloud round-trip occurs.
"""

from __future__ import annotations

import pytest

from uniqc.calibration.results import ReadoutCalibrationResult
from uniqc.qem.readout_em import ReadoutEM, _outcome_to_int


class _FakeAdapter:
    """Minimal adapter — only the ``name`` attribute is read by ReadoutEM."""

    name = "dummy:local:simulator"


def _identity_1q_cal(qubit: int = 0) -> ReadoutCalibrationResult:
    """Calibration with no readout error (diagonal confusion matrix)."""
    return ReadoutCalibrationResult(
        calibrated_at="2026-05-01T00:00:00Z",
        backend="dummy:local:simulator",
        type="readout_1q",
        qubit=qubit,
        confusion_matrix=((1.0, 0.0), (0.0, 1.0)),
        assignment_fidelity=1.0,
    )


def _flip_1q_cal(qubit: int = 0, p_flip: float = 0.1) -> ReadoutCalibrationResult:
    """A symmetric bit-flip channel with flip probability ``p_flip``."""
    return ReadoutCalibrationResult(
        calibrated_at="2026-05-01T00:00:00Z",
        backend="dummy:local:simulator",
        type="readout_1q",
        qubit=qubit,
        confusion_matrix=((1 - p_flip, p_flip), (p_flip, 1 - p_flip)),
        assignment_fidelity=1 - p_flip,
    )


@pytest.fixture
def em():
    return ReadoutEM(adapter=_FakeAdapter(), max_age_hours=24.0)


def _preload(em: ReadoutEM, qubit: int, cal: ReadoutCalibrationResult) -> None:
    """Inject a pre-built M3Mitigator into the cache so no cache I/O happens."""
    from uniqc.qem.m3 import M3Mitigator

    em._mitigators[f"1q_{qubit}"] = M3Mitigator(calibration_result=cal, max_age_hours=None)


def _preload_2q(em: ReadoutEM, q0: int, q1: int, cal: ReadoutCalibrationResult) -> None:
    from uniqc.qem.m3 import M3Mitigator

    em._mitigators[f"2q_{q0}_{q1}"] = M3Mitigator(calibration_result=cal, max_age_hours=None)


# ---------------------------------------------------------------------------
# _outcome_to_int
# ---------------------------------------------------------------------------


def test_outcome_to_int_handles_int():
    assert _outcome_to_int(3) == 3


def test_outcome_to_int_handles_binary_str():
    assert _outcome_to_int("101") == 5


def test_outcome_to_int_handles_decimal_str():
    assert _outcome_to_int("42") == 42


def test_outcome_to_int_handles_int_like():
    assert _outcome_to_int(7.0) == 7


# ---------------------------------------------------------------------------
# 1q mitigation
# ---------------------------------------------------------------------------


def test_mitigate_counts_1q_identity_passthrough(em):
    _preload(em, 0, _identity_1q_cal())
    counts = {0: 800, 1: 200}
    out = em.mitigate_counts(counts, [0])
    # Identity confusion matrix → output ≈ input
    assert pytest.approx(out[0], abs=1) == 800
    assert pytest.approx(out[1], abs=1) == 200


def test_mitigate_counts_1q_corrects_bit_flip(em):
    """Apply a 10 % flip channel; mitigation should pull counts back."""
    _preload(em, 0, _flip_1q_cal(p_flip=0.1))
    # Suppose the device measured 700/300 (pulled towards 50/50 by the flip);
    # mitigation should produce a more polarised distribution.
    out = em.mitigate_counts({0: 700, 1: 300}, [0])
    assert out[0] > 700  # more polarised
    assert out[1] < 300


def test_mitigate_probabilities_1q(em):
    _preload(em, 0, _identity_1q_cal())
    out = em.mitigate_probabilities({0: 0.8, 1: 0.2}, [0])
    assert pytest.approx(out[0], abs=1e-6) == 0.8


def test_mitigate_probabilities_1q_with_str_keys(em):
    _preload(em, 0, _identity_1q_cal())
    out = em.mitigate_probabilities({"0": 0.6, "1": 0.4}, [0])
    assert pytest.approx(out[0], abs=1e-6) == 0.6


# ---------------------------------------------------------------------------
# 2q mitigation
# ---------------------------------------------------------------------------


def test_mitigate_counts_2q_identity_passthrough(em):
    cal = ReadoutCalibrationResult(
        calibrated_at="2026-05-01T00:00:00Z",
        backend="dummy:local:simulator",
        type="readout_2q",
        qubit=(0, 1),
        confusion_matrix=tuple(tuple(1.0 if i == j else 0.0 for j in range(4)) for i in range(4)),
        assignment_fidelity=1.0,
    )
    _preload_2q(em, 0, 1, cal)
    counts = {0b00: 400, 0b01: 100, 0b10: 100, 0b11: 400}
    out = em.mitigate_counts(counts, [0, 1])
    for k, v in counts.items():
        assert pytest.approx(out[k], abs=1) == v


# ---------------------------------------------------------------------------
# Nq mitigation (sequential per-qubit)
# ---------------------------------------------------------------------------


def test_mitigate_counts_nq_identity_per_qubit(em):
    for q in (0, 1, 2):
        _preload(em, q, _identity_1q_cal(qubit=q))
    counts = {0b000: 500, 0b111: 500}
    out = em.mitigate_counts(counts, [0, 1, 2])
    # Identity per-qubit calibration → unchanged counts
    assert pytest.approx(out[0], abs=1) == 500
    assert pytest.approx(out[7], abs=1) == 500
    # Total preserved
    assert pytest.approx(sum(out.values()), abs=1) == sum(counts.values())


def test_mitigate_probabilities_nq_preserves_normalisation(em):
    for q in (0, 1, 2):
        _preload(em, q, _identity_1q_cal(qubit=q))
    probs = {0b000: 0.7, 0b111: 0.3}
    out = em.mitigate_probabilities(probs, [0, 1, 2])
    assert pytest.approx(sum(out.values()), abs=1e-6) == 1.0


# ---------------------------------------------------------------------------
# UnifiedResult round-trip via apply()
# ---------------------------------------------------------------------------


def test_apply_with_unified_result(em):
    from uniqc.backend_adapter.task.result_types import UnifiedResult

    cal_2q = ReadoutCalibrationResult(
        calibrated_at="2026-05-01T00:00:00Z",
        backend="dummy:local:simulator",
        type="readout_2q",
        qubit=(0, 1),
        confusion_matrix=tuple(tuple(1.0 if i == j else 0.0 for j in range(4)) for i in range(4)),
        assignment_fidelity=1.0,
    )
    _preload_2q(em, 0, 1, cal_2q)
    result = UnifiedResult(
        counts={"00": 500, "11": 500},
        probabilities={"00": 0.5, "11": 0.5},
        shots=1000,
        platform="dummy",
        task_id="t1",
        backend_name="dummy:local:simulator",
        execution_time=0.0,
    )
    mitigated = em.apply(result)
    assert mitigated.shots == 1000
    assert sum(mitigated.counts.values()) == 1000
    # All width-2 bitstrings should be preserved
    assert {len(k) for k in mitigated.counts} == {2}


def test_apply_rejects_non_unified_result(em):
    with pytest.raises(TypeError):
        em.apply({"not": "a result"})


def test_apply_passes_through_empty_counts(em):
    from uniqc.backend_adapter.task.result_types import UnifiedResult

    result = UnifiedResult(
        counts={},
        probabilities={},
        shots=0,
        platform="dummy",
        task_id="t1",
        backend_name="dummy:local:simulator",
        execution_time=0.0,
    )
    out = em.apply(result)
    assert out is result  # short-circuited


def test_apply_infers_measured_qubits_from_width(em):
    from uniqc.backend_adapter.task.result_types import UnifiedResult

    _preload(em, 0, _identity_1q_cal())
    _preload(em, 1, _identity_1q_cal(qubit=1))
    _preload(em, 2, _identity_1q_cal(qubit=2))
    result = UnifiedResult(
        counts={"000": 1, "111": 1},
        probabilities={"000": 0.5, "111": 0.5},
        shots=2,
        platform="dummy",
        task_id="t1",
        backend_name="dummy:local:simulator",
        execution_time=0.0,
    )
    out = em.apply(result)
    # Inferred width 3 → qubits [0,1,2]; outputs preserve width 3 bitstrings
    assert all(len(k) == 3 for k in out.counts)
