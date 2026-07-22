"""Tests for OriginIR-ext ↔ official OriginIR conversion pipeline."""

from __future__ import annotations

from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.originir_spec import OFFICIAL_ORIGINIR_GATES
from uniqc.compile.converter import convert_originir_ext_to_originir
from uniqc.compile.decompose import (
    ORIGINIR_EXT_DECOMPOSABLE_GATES,
    decompose_for_originir,
)

# ─── Helpers ───────────────────────────────────────────────────────────


def _circuit_matrix(c: Circuit):
    """Return the unitary matrix of a circuit (numpy array)."""
    return c.get_matrix()


def _assert_unitaries_close(mat_a, mat_b, *, atol: float = 1e-10):
    """Assert two unitaries are equal up to a global phase."""
    # Find a non-zero entry to determine the phase ratio
    import numpy as np

    flat_a = mat_a.ravel()
    flat_b = mat_b.ravel()
    idx = int(np.argmax(np.abs(flat_a)))
    if np.abs(flat_a[idx]) < 1e-12:
        return  # both near zero — trivially equal
    phase = flat_b[idx] / flat_a[idx]
    np.testing.assert_allclose(mat_a * phase, mat_b, atol=atol)


# ─── Decomposition per-gate tests ─────────────────────────────────────


class TestDecomposeForOriginirGates:
    """Verify that each extended gate decomposes to official gates only."""

    def _assert_official_only(self, c: Circuit):
        c2 = decompose_for_originir(c)
        gate_names = {op[0].upper() for op in c2.opcode_list}
        assert gate_names.isdisjoint(ORIGINIR_EXT_DECOMPOSABLE_GATES), (
            f"Extended gates remain after decomposition: "
            f"{gate_names & ORIGINIR_EXT_DECOMPOSABLE_GATES}"
        )

    def test_ecr(self):
        c = Circuit(2)
        c.add_gate("ECR", [0, 1])
        self._assert_official_only(c)

    def test_iswap(self):
        c = Circuit(2)
        c.iswap(0, 1)
        self._assert_official_only(c)

    def test_xx(self):
        c = Circuit(2)
        c.xx(0, 1, 0.5)
        self._assert_official_only(c)

    def test_yy(self):
        c = Circuit(2)
        c.yy(0, 1, 0.3)
        self._assert_official_only(c)

    def test_zz(self):
        c = Circuit(2)
        c.zz(0, 1, 0.7)
        self._assert_official_only(c)

    def test_xy(self):
        c = Circuit(2)
        c.xy(0, 1, 0.4)
        self._assert_official_only(c)

    def test_phase2q(self):
        c = Circuit(2)
        c.phase2q(0, 1, 0.1, 0.2, 0.3)
        self._assert_official_only(c)

    def test_uu15(self):
        c = Circuit(2)
        c.uu15(0, 1, [0.1] * 15)
        self._assert_official_only(c)

    def test_rphi(self):
        c = Circuit(1)
        c.rphi(0, 0.5, 0.7)
        self._assert_official_only(c)

    def test_no_decompose_needed(self):
        """Circuit with only official gates should pass through unchanged."""
        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        c.rz(0, 0.5)
        c2 = decompose_for_originir(c)
        assert c2 is c  # identity (no copy) when nothing to decompose


# ─── Matrix equivalence tests ─────────────────────────────────────────


class TestMatrixEquivalence:
    """Verify decomposed circuits produce the same unitary (up to global phase)."""

    def test_ecr_matrix(self):
        c_orig = Circuit(2)
        c_orig.add_gate("ECR", [0, 1])
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_iswap_matrix(self):
        c_orig = Circuit(2)
        c_orig.iswap(0, 1)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_xx_matrix(self):
        c_orig = Circuit(2)
        c_orig.xx(0, 1, 0.8)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_yy_matrix(self):
        c_orig = Circuit(2)
        c_orig.yy(0, 1, 0.6)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_zz_matrix(self):
        c_orig = Circuit(2)
        c_orig.zz(0, 1, 0.4)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_xy_matrix(self):
        c_orig = Circuit(2)
        c_orig.xy(0, 1, 0.5)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_phase2q_matrix(self):
        c_orig = Circuit(2)
        c_orig.phase2q(0, 1, 0.1, 0.2, 0.3)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_rphi_matrix(self):
        c_orig = Circuit(1)
        c_orig.rphi(0, 0.5, 0.7)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))

    def test_ecr_dagger_matrix(self):
        c_orig = Circuit(2)
        c_orig.add_gate("ECR", [0, 1], dagger=True)
        c_decomp = decompose_for_originir(c_orig)
        _assert_unitaries_close(_circuit_matrix(c_orig), _circuit_matrix(c_decomp))


# ─── Official serializer tests ────────────────────────────────────────


class TestOfficialSerializer:
    """Verify to_originir_official() produces correct block-format output."""

    def test_basic_circuit(self):
        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        c.measure(0, 1)
        out = c.to_originir_official()
        assert "QINIT 2" in out
        assert "CREG 2" in out
        assert "H q[0]" in out
        assert "CNOT q[0], q[1]" in out
        assert "MEASURE q[0], c[0]" in out

    def test_no_inline_dagger(self):
        """Dagger should be in block format, not inline."""
        c = Circuit(1)
        c.add_gate("H", 0, dagger=True)
        out = c.to_originir_official()
        assert "DAGGER" in out
        assert "ENDDAGGER" in out
        assert "H q[0] dagger" not in out  # no inline dagger

    def test_no_inline_controlled_by(self):
        """Control should be in block format, not inline."""
        c = Circuit(2)
        c.add_gate("X", 1, control_qubits=[0])
        out = c.to_originir_official()
        assert "CONTROL q[0]" in out
        assert "ENDCONTROL" in out
        assert "controlled_by" not in out  # no inline controlled_by

    def test_extended_gates_decomposed(self):
        """Extended gates should be decomposed in official output."""
        c = Circuit(2)
        c.iswap(0, 1)
        out = c.to_originir_official()
        assert "ISWAP" not in out.upper()
        # Should contain official gates
        assert any(g in out for g in ["S ", "H ", "CNOT"])


# ─── Converter end-to-end tests ──────────────────────────────────────


class TestConvertOriginirExtToOriginir:
    """End-to-end conversion from originir-ext string to official originir."""

    def test_basic_roundtrip(self):
        originir_ext = (
            "QINIT 2\n"
            "CREG 2\n"
            "H q[0]\n"
            "CNOT q[0], q[1]\n"
            "MEASURE q[0], c[0]\n"
            "MEASURE q[1], c[1]\n"
        )
        official = convert_originir_ext_to_originir(originir_ext)
        assert "QINIT 2" in official
        assert "H q[0]" in official
        assert "CNOT q[0], q[1]" in official

    def test_extended_gate_converted(self):
        originir_ext = (
            "QINIT 2\n"
            "CREG 0\n"
            "ISWAP q[0], q[1]\n"
        )
        official = convert_originir_ext_to_originir(originir_ext)
        assert "ISWAP" not in official.upper()

    def test_inline_dagger_converted(self):
        originir_ext = (
            "QINIT 1\n"
            "CREG 0\n"
            "H q[0] dagger\n"
        )
        official = convert_originir_ext_to_originir(originir_ext)
        assert "dagger" not in official.lower() or "DAGGER" in official
        # Should have block format DAGGER
        assert "DAGGER" in official
        assert "ENDDAGGER" in official


# ─── Spec tests ───────────────────────────────────────────────────────


class TestSpec:
    """Verify spec definitions are correct."""

    def test_official_gates_subset_of_ext(self):
        from uniqc.circuit_builder.originir_ext_spec import available_originir_ext_gates

        assert OFFICIAL_ORIGINIR_GATES.issubset(set(available_originir_ext_gates))

    def test_extended_gates_only_nonempty(self):
        from uniqc.circuit_builder.originir_ext_spec import EXTENDED_GATES_ONLY

        assert len(EXTENDED_GATES_ONLY) > 0
        assert EXTENDED_GATES_ONLY.isdisjoint(OFFICIAL_ORIGINIR_GATES)

    def test_official_gates_count(self):
        """Official gate set should contain exactly the expected gates."""
        expected = {
            "H", "X", "Y", "Z", "S", "SX", "T", "I",
            "RX", "RY", "RZ", "U1", "U2", "U3",
            "CNOT", "CZ", "SWAP",
            "TOFFOLI", "CSWAP",
            "BARRIER",
        }
        assert expected == OFFICIAL_ORIGINIR_GATES
