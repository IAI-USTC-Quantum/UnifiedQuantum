"""
Comprehensive unit tests for OriginIR-ext DEF block support.

Tests cover:
- DEF block generation from NamedCircuit (register-declaration header syntax)
- DEF header/call parsing
- DEF call expansion (inlining) through the base parser
- Roundtrip DEF export/import
"""

import pytest

from uniqc.circuit_builder.named_circuit import circuit_def
from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser
from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

# =============================================================================
# TestOriginIRDefExport
# =============================================================================


class TestOriginIRDefExport:
    """Tests for generating DEF blocks from NamedCircuit."""

    def test_def_export_simple(self):
        """Simple DEF block export uses the register-declaration header."""

        @circuit_def(name="bell_pair", qregs={"q": 2})
        def bell_pair(circ, q):
            circ.h(q[0])
            circ.cnot(q[0], q[1])
            return circ

        def_str = bell_pair.to_originir_def()
        assert "DEF bell_pair(q[2])" in def_str
        assert "H q[0]" in def_str
        assert "CNOT q[0], q[1]" in def_str
        assert "ENDDEF" in def_str

    def test_def_export_with_params(self):
        """DEF block export with scalar parameters."""

        @circuit_def(name="rx_gate", qregs={"q": 1}, params=["theta"])
        def rx_gate(circ, q, theta):
            circ.rx(q[0], theta)
            return circ

        def_str = rx_gate.to_originir_def()
        assert "DEF rx_gate(q[1]) (theta)" in def_str
        assert "RX q[0], (theta)" in def_str
        assert "ENDDEF" in def_str

    def test_def_export_multi_register(self):
        """DEF block export with multiple named registers."""

        @circuit_def(name="entangle", qregs={"a": 2, "b": 1}, params=["t1", "t2"])
        def entangle(circ, a, b, t1, t2):
            circ.rx(a[0], t1)
            circ.ry(b[0], t2)
            circ.cnot(a[1], b[0])
            return circ

        def_str = entangle.to_originir_def()
        assert "DEF entangle(a[2], b[1]) (t1, t2)" in def_str
        assert "RX a[0], (t1)" in def_str
        assert "RY b[0], (t2)" in def_str
        assert "CNOT a[1], b[0]" in def_str


# =============================================================================
# TestOriginIRDefHeaderParse
# =============================================================================


class TestOriginIRDefHeaderParse:
    """Tests for parsing DEF header lines (register-declaration syntax)."""

    def test_parse_def_header(self):
        """Parse DEF header with a single register declaration."""
        op, formal_qregs, params, name = OriginIR_LineParser.handle_def("DEF bell_pair(q[2])")
        assert op == "DEF"
        assert name == "bell_pair"
        assert formal_qregs == [("q", 2)]
        assert params == []

    def test_parse_def_header_with_params(self):
        """Parse DEF header with a single scalar parameter."""
        op, formal_qregs, params, name = OriginIR_LineParser.handle_def("DEF rx_gate(q[1]) (theta)")
        assert op == "DEF"
        assert name == "rx_gate"
        assert formal_qregs == [("q", 1)]
        assert params == ["theta"]

    def test_parse_def_header_multiple_params(self):
        """Parse DEF header with multiple scalar parameters."""
        op, formal_qregs, params, name = OriginIR_LineParser.handle_def("DEF u3(q[1]) (theta, phi, lam)")
        assert name == "u3"
        assert formal_qregs == [("q", 1)]
        assert params == ["theta", "phi", "lam"]

    def test_parse_def_header_multi_register(self):
        """Parse DEF header with multiple named registers."""
        op, formal_qregs, params, name = OriginIR_LineParser.handle_def("DEF foo(a[2], anc[1]) (t1, t2)")
        assert name == "foo"
        assert formal_qregs == [("a", 2), ("anc", 1)]
        assert params == ["t1", "t2"]

    def test_parse_def_header_requires_register(self):
        """A DEF header with no register declaration is rejected."""
        with pytest.raises(ValueError):
            OriginIR_LineParser.handle_def("DEF foo()")

    def test_parse_enddef(self):
        """Parse ENDDEF line."""
        assert OriginIR_LineParser.regexp_enddef.match("ENDDEF") is not None


# =============================================================================
# TestOriginIRDefCallParse
# =============================================================================


class TestOriginIRDefCallParse:
    """Tests for parsing DEF subroutine call lines."""

    def test_parse_call_simple(self):
        name, qargs, pargs = OriginIR_LineParser.handle_def_call("bell(q[0], q[1])")
        assert name == "bell"
        assert qargs.replace(" ", "") == "q[0],q[1]"
        assert pargs is None

    def test_parse_call_with_params(self):
        name, qargs, pargs = OriginIR_LineParser.handle_def_call("rx_gate(a[3]) (1.57)")
        assert name == "rx_gate"
        assert qargs.strip() == "a[3]"
        assert pargs.strip() == "1.57"

    def test_parse_call_whole_register(self):
        name, qargs, pargs = OriginIR_LineParser.handle_def_call("bell(a)")
        assert name == "bell"
        assert qargs.strip() == "a"
        assert pargs is None


# =============================================================================
# TestOriginIRDefExpansion
# =============================================================================


class TestOriginIRDefExpansion:
    """Integration tests for DEF definition + call expansion."""

    def test_def_call_expands_inline(self):
        program = (
            "QINIT 4\nCREG 2\nDEF bell(q[2])\nH q[0]\nCNOT q[0], q[1]\nENDDEF\nbell(q[0], q[1])\nbell(q[2], q[3])\n"
        )
        parser = OriginIR_BaseParser()
        parser.parse(program)
        flat = parser.to_extended_originir()
        assert "H q[0]" in flat
        assert "CNOT q[0], q[1]" in flat
        assert "H q[2]" in flat
        assert "CNOT q[2], q[3]" in flat
        # DEF definitions are inlined, not emitted.
        assert "DEF" not in flat
        assert "bell" not in flat

    def test_def_call_scalar_params(self):
        program = (
            "QINIT 2\nCREG 0\nDEF rot(q[1]) (theta)\nRX q[0], (theta)\nENDDEF\nrot(q[0]) (1.57)\nrot(q[1]) (0.5)\n"
        )
        parser = OriginIR_BaseParser()
        parser.parse(program)
        flat = parser.to_extended_originir()
        assert "RX q[0], (1.57)" in flat
        assert "RX q[1], (0.5)" in flat

    def test_def_multi_register_call(self):
        program = (
            "QINIT 5\nCREG 0\n"
            "DEF entangle(a[2], b[1]) (t1, t2)\nRX a[0], (t1)\nRY b[0], (t2)\nCNOT a[1], b[0]\nENDDEF\n"
            "entangle(q[0], q[1], q[2]) (1.5, 0.7)\n"
        )
        parser = OriginIR_BaseParser()
        parser.parse(program)
        flat = parser.to_extended_originir()
        assert "RX q[0], (1.5)" in flat
        assert "RY q[2], (0.7)" in flat
        assert "CNOT q[1], q[2]" in flat

    def test_def_whole_register_call(self):
        program = (
            "QINIT q[2]\nQINIT anc[2]\nCREG 0\nDEF bell(x[2])\nH x[0]\nCNOT x[0], x[1]\nENDDEF\nbell(q)\nbell(anc)\n"
        )
        parser = OriginIR_BaseParser()
        parser.parse(program)
        flat = parser.to_extended_originir()
        # q -> physical 0,1 ; anc -> physical 2,3
        assert "H q[0]" in flat
        assert "CNOT q[0], q[1]" in flat
        assert "H q[2]" in flat
        assert "CNOT q[2], q[3]" in flat

    def test_def_qubit_count_mismatch(self):
        program = "QINIT 4\nCREG 0\nDEF bell(q[2])\nH q[0]\nCNOT q[0], q[1]\nENDDEF\nbell(q[0])\n"
        with pytest.raises(ValueError, match="expects 2 qubit"):
            OriginIR_BaseParser().parse(program)

    def test_def_param_count_mismatch(self):
        program = "QINIT 1\nCREG 0\nDEF rot(q[1]) (theta)\nRX q[0], (theta)\nENDDEF\nrot(q[0])\n"
        with pytest.raises(ValueError, match="expects 1 parameter"):
            OriginIR_BaseParser().parse(program)

    def test_def_unclosed_block(self):
        program = "QINIT 2\nCREG 0\nDEF bell(q[2])\nH q[0]\n"
        with pytest.raises(ValueError, match="not closed"):
            OriginIR_BaseParser().parse(program)

    def test_def_to_circuit_roundtrip(self):
        """A defined+called program builds a Circuit with the expanded gates."""

        @circuit_def(name="bell", qregs={"q": 2})
        def bell(circ, q):
            circ.h(q[0])
            circ.cnot(q[0], q[1])
            return circ

        program = f"QINIT 4\nCREG 0\n{bell.to_originir_def()}\nbell(q[0], q[1])\nbell(q[2], q[3])\n"
        parser = OriginIR_BaseParser()
        parser.parse(program)
        circuit = parser.to_circuit()
        # Two bell pairs -> 4 gate opcodes.
        assert len(circuit.opcode_list) == 4
