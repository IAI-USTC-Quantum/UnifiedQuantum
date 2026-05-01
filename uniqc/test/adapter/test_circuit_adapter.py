"""Tests for circuit_adapter module."""

import pytest

from uniqc.circuit_adapter import (
    CircuitAdapter,
    IBMCircuitAdapter,
    OriginQCircuitAdapter,
    QuafuCircuitAdapter,
)
from uniqc.circuit_builder import Circuit


class TestCircuitAdapterInterface:
    """Test the CircuitAdapter abstract base class interface."""

    def test_abstract_methods(self):
        """Test that CircuitAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CircuitAdapter()

    def test_adapt_batch(self):
        """Test that adapt_batch calls adapt for each circuit."""
        # Create a concrete adapter for testing
        class MockAdapter(CircuitAdapter):
            def adapt(self, circuit):
                return f"adapted_{circuit}"
            def get_supported_gates(self):
                return ["H"]

        adapter = MockAdapter()
        circuits = [Circuit(), Circuit()]
        circuits[0].h(0)
        circuits[1].x(0)

        results = adapter.adapt_batch(circuits)
        assert len(results) == 2

    def test_get_originir(self):
        """Test _get_originir extracts OriginIR string."""
        class MockAdapter(CircuitAdapter):
            def adapt(self, circuit):
                return None
            def get_supported_gates(self):
                return []

        adapter = MockAdapter()
        circuit = Circuit()
        circuit.h(0)

        originir = adapter._get_originir(circuit)
        assert "QINIT" in originir
        assert "H" in originir


class TestOriginQCircuitAdapter:
    """Test OriginQCircuitAdapter."""

    def test_get_supported_gates(self):
        """Test that supported gates are returned."""
        adapter = OriginQCircuitAdapter()
        gates = adapter.get_supported_gates()
        assert isinstance(gates, list)
        assert "H" in gates
        assert "CNOT" in gates
        assert "MEASURE" in gates

    def test_supported_gates_includes_rotation_gates(self):
        """Test that rotation gates are included."""
        adapter = OriginQCircuitAdapter()
        gates = adapter.get_supported_gates()
        assert "RX" in gates
        assert "RY" in gates
        assert "RZ" in gates
        assert "U1" in gates
        assert "U2" in gates
        assert "U3" in gates

    def test_supported_gates_includes_two_qubit_gates(self):
        """Test that two-qubit gates are included."""
        adapter = OriginQCircuitAdapter()
        gates = adapter.get_supported_gates()
        assert "CNOT" in gates
        assert "CZ" in gates
        assert "SWAP" in gates
        assert "ISWAP" in gates


@pytest.mark.requires_pyqpanda3
class TestOriginQCircuitAdapterIntegration:
    """Integration tests for OriginQCircuitAdapter with real pyqpanda3."""

    @pytest.fixture(autouse=True)
    def check_pyqpanda3(self):
        """Skip tests if pyqpanda3 is not available."""
        pytest.importorskip("pyqpanda3")

    def test_adapt_simple_circuit(self):
        """Test adapt returns OriginIR string (not QProg)."""
        adapter = OriginQCircuitAdapter()
        circuit = Circuit()
        circuit.h(0)
        circuit.cnot(0, 1)
        circuit.measure(0, 1)

        result = adapter.adapt(circuit)
        assert isinstance(result, str)
        assert "QINIT" in result
        assert "H" in result
        assert "CNOT" in result

    def test_adapt_rotation_gates(self):
        """Test adapt with rotation gates returns OriginIR string."""
        adapter = OriginQCircuitAdapter()
        circuit = Circuit()
        circuit.rx(0, 0.5)
        circuit.ry(1, 0.3)
        circuit.rz(2, 0.1)
        circuit.measure(0, 1, 2)

        result = adapter.adapt(circuit)
        assert isinstance(result, str)
        assert "RX" in result
        assert "RY" in result
        assert "RZ" in result


class TestQuafuCircuitAdapter:
    """Test QuafuCircuitAdapter."""

    def test_get_supported_gates(self):
        """Test that supported gates are returned."""
        adapter = QuafuCircuitAdapter()
        gates = adapter.get_supported_gates()
        assert isinstance(gates, list)
        assert "H" in gates
        assert "CNOT" in gates
        assert "MEASURE" in gates


@pytest.mark.requires_quafu
class TestQuafuCircuitAdapterIntegration:
    """Integration tests for QuafuCircuitAdapter with real quafu."""

    @pytest.fixture(autouse=True)
    def check_quafu(self):
        """Skip tests if quafu is not available."""
        pytest.importorskip("quafu")

    def test_adapt_simple_circuit(self):
        """Test adapt with real quafu."""
        adapter = QuafuCircuitAdapter()
        circuit = Circuit()
        circuit.h(0)
        circuit.cnot(0, 1)
        circuit.measure(0, 1)

        result = adapter.adapt(circuit)
        # Verify result is a quafu.QuantumCircuit
        assert result is not None
        assert hasattr(result, 'h')
        assert hasattr(result, 'cnot')

    def test_adapt_rotation_gates(self):
        """Test adapt with rotation gates."""
        adapter = QuafuCircuitAdapter()
        circuit = Circuit()
        circuit.rx(0, 0.5)
        circuit.ry(1, 0.3)
        circuit.rz(2, 0.1)
        circuit.measure(0, 1, 2)

        result = adapter.adapt(circuit)
        assert result is not None

    def test_adapt_two_qubit_gates(self):
        """Test adapt with two-qubit gates."""
        adapter = QuafuCircuitAdapter()
        circuit = Circuit()
        circuit.cnot(0, 1)
        circuit.cz(1, 2)
        circuit.measure(0, 1, 2)

        result = adapter.adapt(circuit)
        assert result is not None

    def test_adapt_with_dagger_block(self):
        """Test adapt with DAGGER block."""
        adapter = QuafuCircuitAdapter()
        circuit = Circuit()
        circuit.s(0)
        circuit.t(1)
        with circuit.dagger():
            circuit.h(0)
        circuit.measure(0, 1)

        result = adapter.adapt(circuit)
        assert result is not None

    def test_adapt_with_barrier(self):
        """Test adapt with BARRIER."""
        adapter = QuafuCircuitAdapter()
        circuit = Circuit()
        circuit.h(0)
        circuit.barrier(0)
        circuit.measure(0)

        result = adapter.adapt(circuit)
        assert result is not None


class TestIBMCircuitAdapter:
    """Test IBMCircuitAdapter."""

    def test_get_supported_gates(self):
        """Test that supported gates are returned."""
        adapter = IBMCircuitAdapter()
        gates = adapter.get_supported_gates()
        assert isinstance(gates, list)
        assert "H" in gates
        assert "CNOT" in gates
        assert "CX" in gates  # IBM uses CX for CNOT
        assert "MEASURE" in gates

    def test_supported_gates_includes_u_gates(self):
        """Test that U gates are included."""
        adapter = IBMCircuitAdapter()
        gates = adapter.get_supported_gates()
        assert "U1" in gates
        assert "U2" in gates
        assert "U3" in gates


@pytest.mark.requires_qiskit
class TestIBMCircuitAdapterIntegration:
    """Integration tests for IBMCircuitAdapter with real qiskit."""

    @pytest.fixture(autouse=True)
    def check_qiskit(self):
        """Skip tests if qiskit is not available."""
        pytest.importorskip("qiskit")

    def test_adapt_simple_circuit(self):
        """Test adapt with real qiskit."""
        adapter = IBMCircuitAdapter()
        circuit = Circuit()
        circuit.h(0)
        circuit.cnot(0, 1)
        circuit.measure(0, 1)

        result = adapter.adapt(circuit)
        # Verify result is a qiskit.QuantumCircuit
        assert result is not None
        assert hasattr(result, 'num_qubits')
        assert result.num_qubits == 2

    def test_adapt_batch(self):
        """Test batch adaptation with real qiskit."""
        adapter = IBMCircuitAdapter()

        circuit1 = Circuit()
        circuit1.h(0)
        circuit1.measure(0)

        circuit2 = Circuit()
        circuit2.x(0)
        circuit2.measure(0)

        results = adapter.adapt_batch([circuit1, circuit2])
        assert len(results) == 2

    def test_adapt_with_transpilation(self):
        """Test adapt_with_transpilation with real qiskit."""
        adapter = IBMCircuitAdapter()
        circuit = Circuit()
        circuit.h(0)
        circuit.measure(0)

        # Without backend
        result = adapter.adapt_with_transpilation(circuit, backend=None)
        assert result is not None


class TestGateCoverage:
    """Test that adapters cover the expected gate sets."""

    def test_originq_covers_basic_gates(self):
        """Test that OriginQ adapter covers basic quantum gates."""
        adapter = OriginQCircuitAdapter()
        gates = set(adapter.get_supported_gates())

        basic_gates = {"H", "X", "Y", "Z", "CNOT", "CZ", "RX", "RY", "RZ"}
        assert basic_gates.issubset(gates)

    def test_ibm_covers_qasm_gates(self):
        """Test that IBM adapter covers standard QASM gates."""
        adapter = IBMCircuitAdapter()
        gates = set(adapter.get_supported_gates())

        qasm_gates = {"H", "X", "Y", "Z", "CNOT", "CX", "CZ"}
        assert qasm_gates.issubset(gates)

    def test_quafu_covers_basic_gates(self):
        """Test that Quafu adapter covers basic gates."""
        adapter = QuafuCircuitAdapter()
        gates = set(adapter.get_supported_gates())

        basic_gates = {"H", "X", "Y", "Z", "RX", "RY", "RZ", "CNOT"}
        assert basic_gates.issubset(gates)
