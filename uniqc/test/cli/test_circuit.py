"""Tests for CLI circuit conversion functions."""

from uniqc.test._utils import uniq_test


@uniq_test("Test CLI _qasm_to_originir")
def test_qasm_to_originir():
    """Test QASM to OriginIR conversion in CLI."""
    from uniqc.cli.circuit import _qasm_to_originir

    qasm_str = """
OPENQASM 2.0;
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
    print(f"Converted OriginIR:\n{originir}")


@uniq_test("Test CLI _originir_to_qasm")
def test_originir_to_qasm():
    """Test OriginIR to QASM conversion in CLI."""
    from uniqc.cli.circuit import _originir_to_qasm

    originir_str = """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
"""
    qasm = _originir_to_qasm(originir_str)

    assert "OPENQASM 2.0" in qasm
    assert "qreg" in qasm
    assert "h" in qasm.lower()
    print(f"Converted QASM:\n{qasm}")


@uniq_test("Test CLI _detect_format")
def test_detect_format():
    """Test format detection in CLI."""
    from uniqc.cli.circuit import _detect_format

    # Test OriginIR detection
    assert _detect_format("QINIT 2\nCREG 2") == "originir"
    assert _detect_format("ORIGINIR 2.0") == "originir"

    # Test QASM detection
    assert _detect_format("OPENQASM 2.0;") == "qasm"
    assert _detect_format('include "qelib1.inc";') == "qasm"

    # Test unknown
    assert _detect_format("invalid content") == "unknown"


@uniq_test("Test CLI _print_info")
def test_print_info():
    """Test circuit info printing in CLI."""
    from uniqc.cli.circuit import _print_info

    originir_str = """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
"""
    # Should not raise
    _print_info(originir_str, "originir")

    qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
"""
    # Should not raise
    _print_info(qasm_str, "qasm")


def run_test_cli_circuit():
    """Run all CLI circuit tests."""
    test_qasm_to_originir()
    test_originir_to_qasm()
    test_detect_format()
    test_print_info()


if __name__ == "__main__":
    run_test_cli_circuit()
