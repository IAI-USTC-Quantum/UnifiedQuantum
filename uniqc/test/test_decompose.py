"""Tests for :mod:`uniqc.compile.decompose`.

Verifies that the IR-level rewrite of OriginIR-native gates (``RPhi``,
``PHASE2Q``, ``UU15``) produces a circuit whose unitary matches the
original up to global phase, and that the rewritten circuit no longer
contains any QASM2-unrepresentable opcode.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.matrix import get_matrix
from uniqc.compile.decompose import (
    QASM2_UNREPRESENTABLE_GATES,
    decompose_for_qasm2,
    decompose_opcode_for_qasm2,
)


def _matrices_equal_up_to_global_phase(a: np.ndarray, b: np.ndarray, atol: float = 1e-9) -> bool:
    """Return True iff ``a`` and ``b`` differ at most by an overall complex scalar."""
    assert a.shape == b.shape
    flat_a = a.ravel()
    flat_b = b.ravel()
    nz = np.argmax(np.abs(flat_a) + np.abs(flat_b))
    if abs(flat_a[nz]) < atol and abs(flat_b[nz]) < atol:
        return np.allclose(a, b, atol=atol)
    if abs(flat_a[nz]) < atol or abs(flat_b[nz]) < atol:
        return False
    phase = flat_b[nz] / flat_a[nz]
    return np.allclose(a * phase, b, atol=atol)


def _no_unrepresentable(circuit: Circuit) -> bool:
    return not any(
        str(op[0]).upper() in QASM2_UNREPRESENTABLE_GATES
        for op in circuit.opcode_list
    )


# ---------------------------------------------------------------------------
# RPhi family
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "theta,phi",
    [(0.4, 0.7), (math.pi, -1.3), (-0.5, 2.1), (0.0, 0.0)],
)
def test_rphi_decomposition_matches_matrix(theta: float, phi: float) -> None:
    original = Circuit(1)
    original.rphi(0, theta, phi)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


@pytest.mark.parametrize("phi", [0.0, 0.7, -1.3, math.pi / 3])
def test_rphi90_decomposition_matches_matrix(phi: float) -> None:
    original = Circuit(1)
    original.add_gate("RPhi90", 0, params=phi)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


@pytest.mark.parametrize("phi", [0.0, 0.7, -1.3, math.pi / 3])
def test_rphi180_decomposition_matches_matrix(phi: float) -> None:
    original = Circuit(1)
    original.add_gate("RPhi180", 0, params=phi)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


def test_rphi_dagger_decomposition() -> None:
    theta, phi = 0.7, -0.4
    original = Circuit(1)
    original.add_gate("RPhi", 0, params=[theta, phi], dagger=True)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


# ---------------------------------------------------------------------------
# PHASE2Q
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [(0.1, 0.2, 0.3), (-0.7, 1.3, -0.2), (math.pi, 0.0, math.pi / 2)],
)
def test_phase2q_decomposition_matches_matrix(params: tuple[float, float, float]) -> None:
    original = Circuit(2)
    original.add_gate("PHASE2Q", [0, 1], params=list(params))

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


def test_phase2q_dagger_decomposition() -> None:
    original = Circuit(2)
    original.add_gate("PHASE2Q", [0, 1], params=[0.4, -0.3, 1.1], dagger=True)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


# ---------------------------------------------------------------------------
# UU15
# ---------------------------------------------------------------------------


def test_uu15_decomposition_matches_matrix() -> None:
    rng = np.random.default_rng(0xC0FFEE)
    params = rng.uniform(-math.pi, math.pi, size=15).tolist()

    original = Circuit(2)
    original.uu15(0, 1, params)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


def test_uu15_dagger_decomposition() -> None:
    rng = np.random.default_rng(0xBADBEEF)
    params = rng.uniform(-math.pi, math.pi, size=15).tolist()

    original = Circuit(2)
    original.add_gate("UU15", [0, 1], params=params, dagger=True)

    decomposed = decompose_for_qasm2(original)

    assert _no_unrepresentable(decomposed)
    assert _matrices_equal_up_to_global_phase(
        get_matrix(original), get_matrix(decomposed)
    )


# ---------------------------------------------------------------------------
# Mixed circuits / pass-through behaviour
# ---------------------------------------------------------------------------


def test_decompose_no_op_when_no_unrepresentable_gates() -> None:
    c = Circuit(2)
    c.h(0)
    c.cnot(0, 1)
    c.rx(0, 0.4)

    out = decompose_for_qasm2(c)
    # No unrepresentable gates → returned unchanged (same object).
    assert out is c


def test_decompose_mixed_circuit_preserves_other_opcodes() -> None:
    c = Circuit(3)
    c.h(0)
    c.rphi(1, 0.3, 0.7)
    c.cnot(0, 2)
    c.add_gate("PHASE2Q", [0, 1], params=[0.1, 0.2, 0.3])
    c.measure(0)
    c.measure(1)

    out = decompose_for_qasm2(c)
    assert _no_unrepresentable(out)

    # Non-target opcodes are preserved (H, CNOT) and measure_list survives.
    surviving_kinds = [op[0] for op in out.opcode_list if op[0] in {"H", "CNOT"}]
    assert "H" in surviving_kinds
    assert "CNOT" in surviving_kinds
    assert sorted(out.measure_list) == [0, 1]
    # Controlled-RPhi cannot be lowered by this lightweight pass.
    op = ("RPhi", 0, None, [0.4, 0.7], False, [1])
    with pytest.raises(NotImplementedError):
        decompose_opcode_for_qasm2(op)


def test_decompose_unknown_gate_pass_through() -> None:
    op = ("H", 0, None, None, False, None)
    assert decompose_opcode_for_qasm2(op) == [op]


# ---------------------------------------------------------------------------
# Integration with submit_task validation
# ---------------------------------------------------------------------------


def test_qasm2_emission_after_decomposition_no_custom_gates() -> None:
    """After decomposition, ``Circuit.qasm`` must not need custom gate defs."""
    from uniqc.circuit_builder.translate_qasm2_oir import collect_qasm2_custom_gates

    c = Circuit(2)
    c.rphi(0, 0.3, 0.6)
    c.add_gate("PHASE2Q", [0, 1], params=[0.1, 0.2, 0.3])
    c.measure(0)
    c.measure(1)

    decomposed = decompose_for_qasm2(c)
    custom = collect_qasm2_custom_gates(decomposed.opcode_list)
    # The replacements use only qelib1.inc gates (rz, rx, u1, cu1).
    assert "rphi" not in custom
    assert "phase2q" not in custom
