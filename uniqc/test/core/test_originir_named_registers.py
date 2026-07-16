"""Unit tests for OriginIR-ext named quantum/classical registers.

Covers:
- Backward-compatible bare-integer QINIT/CREG (default ``q`` / ``c`` registers).
- Named-register declarations in both multi-line and single-line comma forms.
- Flattening of multiple registers into a single physical index space.
- Register-qualified references resolving to physical indices.
- Named classical registers (CREG).
- Error cases: out-of-range index, unknown register, duplicate/collision.
"""

import pytest

from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser


def _parse(program: str) -> OriginIR_BaseParser:
    parser = OriginIR_BaseParser()
    parser.parse(program)
    return parser


# =============================================================================
# Backward compatibility
# =============================================================================


class TestBareIntBackwardCompat:
    def test_bare_int_qinit_creg(self):
        parser = _parse("QINIT 3\nCREG 2\nX q[0]\n")
        assert parser.n_qubit == 3
        assert parser.n_cbit == 2
        assert parser.qreg_map == {"q": (0, 3)}
        assert parser.creg_map == {"c": (0, 2)}

    def test_bare_int_equivalent_to_named_default(self):
        """``QINIT 6`` is equivalent to ``QINIT q[6]`` (and CREG likewise)."""
        a = _parse("QINIT 6\nCREG 4\nH q[5]\nMEASURE q[0], c[3]\n")
        b = _parse("QINIT q[6]\nCREG c[4]\nH q[5]\nMEASURE q[0], c[3]\n")
        assert a.n_qubit == b.n_qubit == 6
        assert a.n_cbit == b.n_cbit == 4
        assert a.to_extended_originir() == b.to_extended_originir()


# =============================================================================
# Named-register declarations
# =============================================================================


class TestNamedRegisterDeclarations:
    def test_multiline_named_qregs(self):
        parser = _parse("QINIT q[6]\nQINIT q1[6]\nCREG 0\nH q1[0]\nCNOT q[0], q1[5]\n")
        assert parser.n_qubit == 12
        assert parser.qreg_map == {"q": (0, 6), "q1": (6, 6)}
        flat = parser.to_extended_originir()
        assert "QINIT 12" in flat
        # q1[0] -> physical 6 ; q1[5] -> physical 11
        assert "H q[6]" in flat
        assert "CNOT q[0], q[11]" in flat

    def test_single_line_comma_qregs(self):
        parser = _parse("QINIT q[2], q1[3]\nCREG 0\nX q1[2]\n")
        assert parser.n_qubit == 5
        assert parser.qreg_map == {"q": (0, 2), "q1": (2, 3)}
        # q1[2] -> physical 4
        assert "X q[4]" in parser.to_extended_originir()

    def test_flatten_always_single_qinit(self):
        parser = _parse("QINIT a[2]\nQINIT b[2]\nQINIT c_reg[1]\nCREG 0\nH b[1]\n")
        flat = parser.to_extended_originir()
        assert flat.count("QINIT") == 1
        assert "QINIT 5" in flat
        # b[1] -> physical 3
        assert "H q[3]" in flat


# =============================================================================
# Named classical registers
# =============================================================================


class TestNamedClassicalRegisters:
    def test_multiline_named_cregs(self):
        parser = _parse("QINIT 4\nCREG c[2]\nCREG c1[2]\nMEASURE q[0], c1[1]\n")
        assert parser.n_cbit == 4
        assert parser.creg_map == {"c": (0, 2), "c1": (2, 2)}
        # c1[1] -> physical cbit 3
        assert "MEASURE q[0], c[3]" in parser.to_extended_originir()

    def test_single_line_comma_cregs(self):
        parser = _parse("QINIT 2\nCREG c[1], c1[1]\nMEASURE q[1], c1[0]\n")
        assert parser.n_cbit == 2
        assert parser.creg_map == {"c": (0, 1), "c1": (1, 1)}
        assert "MEASURE q[1], c[1]" in parser.to_extended_originir()


# =============================================================================
# Register-qualified references
# =============================================================================


class TestRegisterReferences:
    def test_named_qubit_reference_resolution(self):
        parser = _parse("QINIT data[3]\nQINIT anc[2]\nCREG 0\nCNOT data[2], anc[0]\n")
        # data[2] -> physical 2 ; anc[0] -> physical 3
        assert "CNOT q[2], q[3]" in parser.to_extended_originir()

    def test_physical_q_reference_still_works(self):
        parser = _parse("QINIT data[4]\nCREG 0\nH q[3]\n")
        assert "H q[3]" in parser.to_extended_originir()

    def test_reference_in_controlled_by(self):
        parser = _parse("QINIT ctrl[1]\nQINIT tgt[1]\nCREG 0\nX tgt[0] controlled_by (ctrl[0])\n")
        flat = parser.to_extended_originir()
        # ctrl[0] -> physical 0 ; tgt[0] -> physical 1
        assert "X q[1]" in flat
        assert "controlled_by (q[0])" in flat


# =============================================================================
# Error cases
# =============================================================================


class TestNamedRegisterErrors:
    def test_qubit_index_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            _parse("QINIT data[2]\nCREG 0\nH data[2]\n")

    def test_unknown_register(self):
        with pytest.raises(ValueError, match="Unknown register"):
            _parse("QINIT data[2]\nCREG 0\nH other[0]\n")

    def test_duplicate_quantum_register(self):
        with pytest.raises(ValueError, match="Duplicate quantum register"):
            _parse("QINIT data[2]\nQINIT data[1]\nCREG 0\n")

    def test_name_collision_across_namespaces(self):
        with pytest.raises(ValueError, match="both a quantum and a classical"):
            _parse("QINIT foo[2]\nCREG foo[2]\n")

    def test_invalid_register_declaration(self):
        with pytest.raises(ValueError):
            _parse("QINIT q[\nCREG 0\n")


# =============================================================================
# Fuzz round-trip: named-register form is equivalent to the bare-integer form
# =============================================================================


class TestNamedRegisterRoundtrip:
    def test_named_form_matches_bare_form(self):
        """A randomly generated program emitted with named registers parses to
        the exact same flat program as its bare-integer twin."""
        import random

        from uniqc.circuit_builder.originir_spec import generate_sub_gateset_originir
        from uniqc.circuit_builder.random_originir import random_originir

        gate_set = generate_sub_gateset_originir(["H", "X", "Y", "Z", "CNOT", "CZ", "RX", "RY"])
        layout = [("data", 3), ("anc", 3)]
        for seed in range(25):
            random.seed(seed)
            bare = random_originir(6, 15, instruction_set=gate_set, allow_control=True, allow_dagger=True)
            random.seed(seed)
            named = random_originir(
                6, 15, instruction_set=gate_set, allow_control=True, allow_dagger=True, named_qregs=layout
            )
            # The named form uses register-qualified references.
            assert "data[" in named and "anc[" in named

            pb = _parse(bare)
            pn = _parse(named)
            assert pn.n_qubit == pb.n_qubit == 6
            assert pn.program_body == pb.program_body
            assert pn.measure_qubits == pb.measure_qubits

    def test_named_qregs_size_mismatch(self):
        from uniqc.circuit_builder.random_originir import random_originir

        with pytest.raises(ValueError, match="sum to"):
            random_originir(6, 5, named_qregs=[("a", 2), ("b", 2)])
