"""Tests for the enhanced transpiler compiler module."""

from __future__ import annotations

import pytest

from uniqc.backend_info import BackendInfo, Platform, QubitTopology
from uniqc.task.optional_deps import QISKIT_AVAILABLE

pytestmark = pytest.mark.skipif(not QISKIT_AVAILABLE, reason="Qiskit not installed")


@pytest.fixture
def linear_topology():
    """A 5-qubit linear topology 0-1-2-3-4."""
    return BackendInfo(
        platform=Platform.ORIGINQ,
        name="test",
        num_qubits=5,
        topology=(
            QubitTopology(u=0, v=1),
            QubitTopology(u=1, v=2),
            QubitTopology(u=2, v=3),
            QubitTopology(u=3, v=4),
        ),
        avg_1q_fidelity=None,
        avg_2q_fidelity=None,
        avg_readout_fidelity=None,
    )


class TestTranspilerConfig:
    """Tests for TranspilerConfig validation."""

    def test_defaults(self):
        from uniqc.transpiler.compiler import TranspilerConfig

        cfg = TranspilerConfig()
        assert cfg.type == "qiskit"
        assert cfg.level == 2
        assert cfg.basis_gates == ("cz", "sx", "rz")
        assert cfg.chip_characterization is None

    def test_custom_basis_gates_normalised_to_tuple(self):
        from uniqc.transpiler.compiler import TranspilerConfig

        cfg = TranspilerConfig(basis_gates=["cx", "u3"])
        assert cfg.basis_gates == ("cx", "u3")

    def test_invalid_type_raises(self):
        from uniqc.transpiler.compiler import TranspilerConfig

        with pytest.raises(ValueError) as exc_info:
            TranspilerConfig(type="unknown")
        assert "unknown" in str(exc_info.value)

    def test_invalid_level_raises(self):
        from uniqc.transpiler.compiler import TranspilerConfig

        with pytest.raises(ValueError):
            TranspilerConfig(level=5)


class TestCompileOutputFormats:
    """Tests for compile() output format handling."""

    def test_compile_returns_circuit_by_default(self, linear_topology):
        from uniqc.circuit_builder import Circuit
        from uniqc.transpiler.compiler import compile

        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)
        result = compile(circuit, backend_info=linear_topology, output_format="circuit")
        assert isinstance(result, Circuit)

    def test_compile_returns_originir_string(self, linear_topology):
        from uniqc.circuit_builder import Circuit
        from uniqc.transpiler.compiler import compile

        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)
        result = compile(circuit, backend_info=linear_topology, output_format="originir")
        assert isinstance(result, str)
        assert "QINIT" in result

    def test_compile_returns_qasm_string(self, linear_topology):
        from uniqc.circuit_builder import Circuit
        from uniqc.transpiler.compiler import compile

        circuit = Circuit(2)
        circuit.h(0)
        circuit.cnot(0, 1)
        result = compile(circuit, backend_info=linear_topology, output_format="qasm")
        assert isinstance(result, str)
        assert "OPENQASM" in result


class TestCompileWithChipCharacterization:
    """Tests for chip-characterization-aware compilation."""

    def test_compile_uses_backend_info_topology(self, linear_topology):
        """compile() uses BackendInfo.topology as coupling map when provided."""
        from uniqc.circuit_builder import Circuit
        from uniqc.transpiler.compiler import compile

        circuit = Circuit(3)
        circuit.h(0)
        circuit.cnot(0, 1)
        circuit.cnot(1, 2)
        result = compile(circuit, backend_info=linear_topology, output_format="circuit")
        assert isinstance(result, Circuit)

    def test_compile_raises_on_no_topology(self):
        """compile() raises ValueError when no topology info is available."""
        from uniqc.circuit_builder import Circuit
        from uniqc.transpiler.compiler import compile

        circuit = Circuit(3)
        circuit.h(0)
        with pytest.raises(ValueError) as exc_info:
            compile(circuit, output_format="circuit")
        msg = str(exc_info.value).lower()
        assert "topology" in msg or "backend_info" in msg or "chip_characterization" in msg
