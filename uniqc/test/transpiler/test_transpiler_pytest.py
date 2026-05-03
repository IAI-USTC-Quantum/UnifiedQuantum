"""Pytest tests for transpiler module."""
import pytest


class TestTranspilerLazyImport:
    """Tests for transpiler lazy imports."""

    def test_draw_lazy_import(self):
        """Test that draw function can be imported without pyqpanda3."""
        from uniqc.compile import draw

        # Verify it's a callable (the lazy import wrapper)
        assert callable(draw)

    def test_converter_imports(self):
        """Test that converter functions are importable."""
        from uniqc.compile import convert_oir_to_qasm, convert_qasm_to_oir

        assert callable(convert_oir_to_qasm)
        assert callable(convert_qasm_to_oir)

    def test_qasm_to_oir_conversion(self):
        """Test QASM to OriginIR conversion via transpiler."""
        from uniqc.compile import convert_qasm_to_oir

        qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
"""
        originir = convert_qasm_to_oir(qasm_str)
        assert "QINIT" in originir
        assert "H" in originir
