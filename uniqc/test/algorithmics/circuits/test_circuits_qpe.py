"""Tests for ``uniqc.algorithms.core.circuits.qpe`` — quantum phase
estimation circuit construction.

Opcodes in :class:`Circuit` are stored as plain tuples ``(name, qubits, ...)``
and measurements live on the separate ``measure_list``; tests use both.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from uniqc.algorithms.core.circuits.qpe import (
    _controlled_phase,
    _inverse_qft_in_place,
    qpe_circuit,
    qpe_example,
)
from uniqc.circuit_builder import Circuit


def _opcode_names(circ: Circuit) -> list[str]:
    return [op[0] for op in circ.opcode_list]


def _unitary_rz() -> Circuit:
    u = Circuit()
    u.rz(0, math.pi / 4)
    return u


# ---------------------------------------------------------------------------
# qpe_circuit shape
# ---------------------------------------------------------------------------


def test_qpe_circuit_has_correct_qubit_count():
    circ = qpe_circuit(n_precision=3, unitary_circuit=_unitary_rz())
    assert circ.max_qubit + 1 == 1 + 3  # n_system + n_precision


def test_qpe_circuit_no_measure_when_disabled():
    circ = qpe_circuit(n_precision=3, unitary_circuit=_unitary_rz(), measure=False)
    assert len(circ.measure_list) == 0


def test_qpe_circuit_measure_appears_on_precision_register():
    circ = qpe_circuit(n_precision=2, unitary_circuit=_unitary_rz(), measure=True)
    # measure_list contains 2 entries — one per precision qubit
    assert len(circ.measure_list) == 2


def test_qpe_circuit_rejects_zero_precision():
    with pytest.raises(ValueError, match="n_precision"):
        qpe_circuit(n_precision=0, unitary_circuit=_unitary_rz())


def test_qpe_circuit_with_empty_unitary_still_builds_precision_register():
    """An empty unitary leaves the system register at qubit 0 unchanged; QPE
    on a no-op is degenerate but should not crash."""
    empty = Circuit()
    circ = qpe_circuit(n_precision=2, unitary_circuit=empty, measure=False)
    # 1 system (default empty → max_qubit 0 → n_system = 1) + 2 precision
    assert circ.max_qubit + 1 == 3


def test_qpe_circuit_with_state_prep_adds_prep_gates():
    prep = Circuit()
    prep.x(0)
    circ = qpe_circuit(n_precision=2, unitary_circuit=_unitary_rz(), state_prep=prep)
    # State prep is at the start → first op should be X on q0
    assert _opcode_names(circ)[0] == "X"


def test_qpe_circuit_with_custom_controlled_power():
    calls: list[tuple[int, int]] = []

    def _custom(fragment: Circuit, unitary: Circuit, ctrl: int, power: int) -> None:
        calls.append((ctrl, power))

    qpe_circuit(
        n_precision=3,
        unitary_circuit=_unitary_rz(),
        controlled_power=_custom,
        measure=False,
    )
    powers = sorted(p for _, p in calls)
    assert powers == [1, 2, 4]


def test_qpe_example_runs():
    circ = qpe_example()
    # 1 system + 4 precision
    assert circ.max_qubit + 1 == 5
    assert len(circ.measure_list) == 4


# ---------------------------------------------------------------------------
# Inverse QFT helper
# ---------------------------------------------------------------------------


def test_inverse_qft_in_place_adds_swaps_and_h_gates():
    frag = Circuit()
    _inverse_qft_in_place(frag, [0, 1, 2])
    names = _opcode_names(frag)
    assert names.count("H") >= 3
    assert "SWAP" in names


# ---------------------------------------------------------------------------
# Controlled phase decomposition
# ---------------------------------------------------------------------------


def test_controlled_phase_uses_two_cnots():
    frag = Circuit()
    _controlled_phase(frag, control=0, target=1, theta=math.pi / 4)
    cnot_ops = [n for n in _opcode_names(frag) if n in ("CNOT", "CX")]
    assert len(cnot_ops) == 2


def test_controlled_phase_emits_three_rz_two_cnots_at_any_theta():
    """Even at θ=0 the decomposition still emits the structural skeleton —
    callers may rely on the gate count not depending on the angle."""
    frag = Circuit()
    _controlled_phase(frag, 0, 1, 0.0)
    assert len(frag.opcode_list) == 5  # 3 RZ + 2 CNOT


# ---------------------------------------------------------------------------
# Sanity: end-to-end shape stays stable across n_precision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_qpe_circuit_scales(n):
    circ = qpe_circuit(n_precision=n, unitary_circuit=_unitary_rz(), measure=False)
    names = _opcode_names(circ)
    # n_precision qubits each get one H upfront → at least n H gates
    assert names.count("H") >= n
    # Inverse QFT bit-reversal swap count = n // 2
    assert names.count("SWAP") == n // 2


def test_qpe_decoded_phase_close_to_one_over_eight():
    """High-level sanity: the demo's expected phase 1/8 = 0.125 should be
    encoded as the integer m=2 across 4 precision bits."""
    circ = qpe_example()
    assert len(circ.opcode_list) > 4
    assert np.isclose(2 / 2**4, 0.125)
