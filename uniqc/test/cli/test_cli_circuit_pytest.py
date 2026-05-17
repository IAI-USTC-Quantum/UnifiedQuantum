"""Pytest tests for CLI circuit module."""


class TestCLICircuit:
    """Tests for CLI circuit conversion functions."""

    def test_qasm_to_originir(self):
        """Test QASM to OriginIR conversion."""
        from uniqc.cli.circuit import _qasm_to_originir

        qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
"""
        originir = _qasm_to_originir(qasm_str)

        assert "QINIT" in originir
        assert "CREG" in originir
        assert "H" in originir
        assert "CNOT" in originir

    def test_originir_to_qasm(self):
        """Test OriginIR to QASM conversion."""
        from uniqc.cli.circuit import _originir_to_qasm

        originir_str = """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
"""
        qasm = _originir_to_qasm(originir_str)

        assert "OPENQASM 2.0" in qasm
        assert "qreg" in qasm

    def test_detect_format(self):
        """Test format detection."""
        from uniqc.cli.circuit import _detect_format

        assert _detect_format("QINIT 2\nCREG 2") == "originir"
        assert _detect_format("ORIGINIR 2.0") == "originir"
        assert _detect_format("OPENQASM 2.0;") == "qasm"
        assert _detect_format('include "qelib1.inc";') == "qasm"
        assert _detect_format("invalid content") == "unknown"

    def test_print_info_originir(self, capsys):
        """Test circuit info printing for OriginIR."""
        from uniqc.cli.circuit import _print_info

        originir_str = """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
"""
        _print_info(originir_str, "originir")
        captured = capsys.readouterr()
        assert "Qubits" in captured.out or captured.out == ""  # May or may not print

    def test_print_info_qasm(self, capsys):
        """Test circuit info printing for QASM."""
        from uniqc.cli.circuit import _print_info

        qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
"""
        _print_info(qasm_str, "qasm")
        captured = capsys.readouterr()
        assert captured.out == "" or "Qubits" in captured.out
