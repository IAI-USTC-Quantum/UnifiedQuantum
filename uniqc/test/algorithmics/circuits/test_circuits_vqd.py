"""Tests for VQD circuit components."""

import numpy as np
import pytest

from uniqc.algorithms.core.circuits import vqd_circuit, vqd_overlap_circuit
from uniqc.algorithms.core.circuits.vqd import _hea_ansatz
from uniqc.circuit_builder import Circuit
from uniqc.simulator.opcode_simulator import OpcodeSimulator


def _statevector(circuit: Circuit) -> np.ndarray:
    return np.asarray(
        OpcodeSimulator("statevector").simulate_opcodes_statevector(
            circuit.qubit_num,
            circuit.opcode_list,
        )
    )


def _ancilla_zero_probability(circuit: Circuit) -> float:
    ancilla = circuit.measure_list[0]
    unitary_opcodes = [opcode for opcode in circuit.opcode_list if opcode[0] != "MEASURE"]
    probabilities = OpcodeSimulator("statevector").simulate_opcodes_pmeasure(
        circuit.qubit_num,
        unitary_opcodes,
        [ancilla],
    )
    return float(probabilities[0])


def _expected_overlap_probability(
    previous_state: np.ndarray,
    ansatz_params: list[float],
    n_layers: int,
) -> float:
    n_qubits = int(np.log2(len(previous_state)))
    ansatz = Circuit(n_qubits)
    _hea_ansatz(ansatz, ansatz_params, n_layers, list(range(n_qubits)))
    ansatz_state = _statevector(ansatz)
    normalized_previous = previous_state / np.linalg.norm(previous_state)
    fidelity = abs(np.vdot(ansatz_state, normalized_previous)) ** 2
    return float((1.0 + fidelity) / 2.0)


class TestVQDCircuit:
    """Tests for vqd_circuit function."""

    def test_vqd_circuit_nonempty(self):
        """vqd_circuit should produce a non-empty circuit."""
        c = Circuit()
        gs = np.array([1, 0, 0, 0], dtype=complex)
        vqd_circuit(c, ansatz_params=[0.1, 0.2, 0.3, 0.4], prev_states=[gs], qubits=[0, 1], n_layers=2)
        assert len(c.opcode_list) > 0

    def test_vqd_different_param_counts(self):
        """Different parameter counts should match n_qubits * n_layers."""
        gs = np.array([1, 0, 0, 0], dtype=complex)

        # 2 qubits, 1 layer = 2 params
        c1 = Circuit()
        vqd_circuit(c1, [0.1, 0.2], prev_states=[gs], qubits=[0, 1], n_layers=1)
        assert len(c1.opcode_list) > 0

        # 2 qubits, 3 layers = 6 params
        c2 = Circuit()
        vqd_circuit(c2, [0.1] * 6, prev_states=[gs], qubits=[0, 1], n_layers=3)
        assert len(c2.opcode_list) > len(c1.opcode_list)

    def test_vqd_wrong_param_count_raises(self):
        """Wrong number of parameters should raise ValueError."""
        c = Circuit()
        gs = np.array([1, 0, 0, 0], dtype=complex)
        with pytest.raises(ValueError, match="Expected"):
            vqd_circuit(c, [0.1], prev_states=[gs], qubits=[0, 1], n_layers=2)

    def test_vqd_empty_prev_states_raises(self):
        """Empty prev_states should raise ValueError (use VQE instead)."""
        c = Circuit()
        with pytest.raises(ValueError, match="VQE"):
            vqd_circuit(c, [0.1, 0.2, 0.3, 0.4], prev_states=[], qubits=[0, 1], n_layers=2)


class TestVQDOverlapCircuit:
    """Tests for vqd_overlap_circuit function."""

    def test_overlap_returns_circuit(self):
        """vqd_overlap_circuit should return a Circuit object."""
        gs = np.array([1, 0, 0, 0], dtype=complex)
        circ = vqd_overlap_circuit(gs, [0.1, 0.2, 0.3, 0.4], n_layers=2)
        assert isinstance(circ, Circuit)

    def test_overlap_nonempty(self):
        """Overlap circuit should have gates."""
        gs = np.array([1, 0, 0, 0], dtype=complex)
        circ = vqd_overlap_circuit(gs, [0.1, 0.2, 0.3, 0.4], n_layers=2)
        assert len(circ.opcode_list) > 0

    def test_overlap_invalid_state_dimension_raises(self):
        """Non-power-of-2 state dimension should raise ValueError."""
        state = np.array([1, 0, 0], dtype=complex)  # length 3
        with pytest.raises(ValueError, match="power of 2"):
            vqd_overlap_circuit(state, [0.1, 0.2], n_layers=1)

    def test_overlap_custom_qubits(self):
        """Custom qubit indices should be used by the ansatz register."""
        gs = np.array([1, 0, 0, 0], dtype=complex)
        params = [0.1, 0.2, 0.3, 0.4]
        circ = vqd_overlap_circuit(gs, params, n_layers=2, qubits=[5, 6])
        used = {
            qubit
            for _name, qubits, _cbits, _params, _dagger, controls in circ.opcode_list
            for qubit in (
                ([qubits] if isinstance(qubits, int) else qubits or [])
                + ([controls] if isinstance(controls, int) else controls or [])
            )
        }
        assert used == {0, 1, 2, 5, 6}
        assert _ancilla_zero_probability(circ) == pytest.approx(
            _expected_overlap_probability(gs, params, 2),
            abs=1e-7,
        )

    @pytest.mark.parametrize(
        "previous_state,params,n_layers",
        [
            (np.array([1, 1j], dtype=complex) / np.sqrt(2), [0.37], 1),
            (np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2), [0.3, -0.7], 1),
            (np.array([0, 0, 0, 1], dtype=complex), [0.0, 0.0], 1),
        ],
    )
    def test_overlap_probability_matches_numerical_fidelity(
        self,
        previous_state: np.ndarray,
        params: list[float],
        n_layers: int,
    ):
        circ = vqd_overlap_circuit(previous_state, params, n_layers=n_layers)
        assert sum(opcode[0] == "CSWAP" for opcode in circ.opcode_list) == int(
            np.log2(len(previous_state))
        )
        assert _ancilla_zero_probability(circ) == pytest.approx(
            _expected_overlap_probability(previous_state, params, n_layers),
            abs=1e-7,
        )

    def test_overlap_rejects_wrong_qubit_count(self):
        state = np.array([1, 0, 0, 0], dtype=complex)
        with pytest.raises(ValueError, match="Expected 2 ansatz qubits"):
            vqd_overlap_circuit(state, [0.1, 0.2], n_layers=1, qubits=[3])
