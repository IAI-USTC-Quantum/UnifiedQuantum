"""Tests for the ansatz module."""

import numpy as np
import pytest

from uniqc.circuit_builder import Circuit
from uniqc.simulator import Simulator
from uniqc.algorithms.core.ansatz import (
    hea,
    hva,
    qaoa_ansatz,
    uccsd_ansatz,
    hea_param_count,
    EntanglingGate,
    EntanglementTopology,
    RotationGate,
)


def _statevector(circuit: Circuit) -> np.ndarray:
    sim = Simulator(backend_type='statevector', least_qubit_remapping=False)
    return sim.simulate_statevector(circuit.originir)


class TestHEA:

    def run_test_basic(self):
        c = hea(n_qubits=3, depth=1)
        assert c.max_qubit + 1 == 3

    def run_test_custom_params(self):
        params = np.zeros(2 * 4 * 2)
        c = hea(n_qubits=4, depth=2, params=params)
        assert c.max_qubit + 1 == 4

    def run_test_wrong_params_raises(self):
        with pytest.raises(ValueError):
            hea(n_qubits=3, depth=1, params=np.zeros(5))

    def run_test_produces_statevector(self):
        c = hea(n_qubits=2, depth=1, params=np.array([0.5, 0.3, 0.7, 0.1]))
        sv = _statevector(c)
        assert len(sv) == 4
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10

    def run_test_depth_0(self):
        params = np.array([])
        c = hea(n_qubits=2, depth=0, params=params)
        # No gates → empty circuit, skip simulation
        # Just verify it doesn't crash and returns a circuit
        assert isinstance(c, Circuit)


class TestQAOAAnsatz:

    def run_test_basic(self):
        H = [("Z0Z1", 1.0)]
        c = qaoa_ansatz(H, p=1, betas=np.array([0.5]), gammas=np.array([0.3]))
        assert c.max_qubit + 1 == 2

    def run_test_produces_statevector(self):
        H = [("Z0Z1", 1.0), ("Z1Z2", 0.5)]
        c = qaoa_ansatz(H, p=1, betas=np.array([0.5]), gammas=np.array([0.3]))
        sv = _statevector(c)
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10

    def run_test_wrong_betas_raises(self):
        H = [("Z0Z1", 1.0)]
        with pytest.raises(ValueError):
            qaoa_ansatz(H, p=2, betas=np.array([0.5]), gammas=np.array([0.3, 0.2]))

    def run_test_multi_layer(self):
        H = [("Z0Z1", 1.0)]
        c = qaoa_ansatz(H, p=3, betas=np.zeros(3), gammas=np.zeros(3))
        sv = _statevector(c)
        # With β=0, γ=0: only Hadamards applied → uniform superposition
        expected = np.ones(4, dtype=complex) / 2.0
        np.testing.assert_allclose(np.abs(sv), np.abs(expected), atol=1e-8)

    def run_test_x_hamiltonian(self):
        H = [("X0", 1.0)]
        c = qaoa_ansatz(H, p=1, betas=np.array([0.0]), gammas=np.array([np.pi]))
        sv = _statevector(c)
        # With γ=π, exp(-iπ X) flips |+> → |->, so uniform → still uniform
        expected = np.ones(2, dtype=complex) / np.sqrt(2)
        np.testing.assert_allclose(np.abs(sv), np.abs(expected), atol=1e-8)


class TestUCCSD:

    def run_test_basic(self):
        c = uccsd_ansatz(n_qubits=4, n_electrons=2)
        # X(0), X(1) → max_qubit at least 1
        assert c.max_qubit + 1 >= 2

    def run_test_zero_params_hf(self):
        # With zero params, should be Hartree-Fock: |0011> (first 2 occupied)
        c = uccsd_ansatz(n_qubits=4, n_electrons=2, params=np.zeros(5))
        # Only X(0) and X(1) are applied
        sim = Simulator(backend_type='statevector', least_qubit_remapping=False)
        # Need to ensure 4 qubits — touch all
        c.x(2); c.x(2)
        c.x(3); c.x(3)
        sv = sim.simulate_statevector(c.originir)
        expected = np.zeros(16, dtype=complex)
        expected[3] = 1.0  # |0011> = q0=1,q1=1
        np.testing.assert_allclose(sv, expected, atol=1e-10)

    def run_test_n_electrons_exceeds_n_qubits(self):
        with pytest.raises(ValueError):
            uccsd_ansatz(n_qubits=2, n_electrons=3)

    def run_test_wrong_params_raises(self):
        with pytest.raises(ValueError):
            uccsd_ansatz(n_qubits=4, n_electrons=2, params=np.zeros(3))

    def run_test_produces_statevector(self):
        c = uccsd_ansatz(n_qubits=4, n_electrons=2, params=np.ones(5) * 0.1)
        sv = _statevector(c)
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10


class TestEnhancedHEA:

    def run_test_backward_compat(self):
        # Default HEA should work the same as before
        c = hea(n_qubits=4, depth=2)
        assert c.max_qubit + 1 == 4
        # Default is RZ+RY rotations: 2 * n_qubits * depth = 16 params
        params = np.zeros(16)
        c = hea(n_qubits=4, depth=2, params=params)
        assert c.max_qubit + 1 == 4

    def run_test_custom_rotation_gates(self):
        # Rx+Rz gates: 2 params per qubit per layer
        params = np.zeros(2 * 4 * 2)  # 2 gates * 4 qubits * 2 layers
        c = hea(n_qubits=4, depth=2, rotation_gates=["rx", "rz"], params=params)
        assert c.max_qubit + 1 == 4

        # Rx+Ry+Rz gates: 3 params per qubit per layer
        params = np.zeros(3 * 4 * 2)
        c = hea(n_qubits=4, depth=2, rotation_gates=["rx", "ry", "rz"], params=params)
        assert c.max_qubit + 1 == 4

    def run_test_cz_gate(self):
        # CZ entangling gate
        c = hea(n_qubits=4, depth=2, entangling_gate="cz")
        assert c.max_qubit + 1 == 4

    def run_test_linear_topology(self):
        c = hea(n_qubits=4, depth=1, topology="linear")
        assert c.max_qubit + 1 == 4
        # Linear topology: 3 edges for 4 qubits

    def run_test_brickwork_topology(self):
        c = hea(n_qubits=4, depth=1, topology="brickwork")
        assert c.max_qubit + 1 == 4

    def run_test_custom_edges(self):
        c = hea(n_qubits=4, depth=1, topology="custom", custom_edges=[(0, 1), (2, 3)])
        assert c.max_qubit + 1 == 4

    def run_test_xx_parametric_gate(self):
        # XX gate consumes extra params per edge
        # For 4 qubits ring topology: 4 edges, so 4 extra params per layer
        # Total: 2*4*1 (rotations) + 4*1 (XX params) = 12 params
        n_params = hea_param_count(4, depth=1, entangling_gate="xx")
        assert n_params == 12
        params = np.zeros(n_params)
        c = hea(n_qubits=4, depth=1, entangling_gate="xx", params=params)
        assert c.max_qubit + 1 == 4

    def run_test_statevector_validity(self):
        c = hea(n_qubits=3, depth=1, rotation_gates=["rx", "ry"])
        sv = _statevector(c)
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10

    def run_test_enum_gates(self):
        c = hea(n_qubits=3, depth=1, rotation_gates=[RotationGate.RX], entangling_gate=EntanglingGate.CNOT)
        assert c.max_qubit + 1 == 3
        sv = _statevector(c)
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10


class TestQAOAVariants:

    def run_test_xy_mixer(self):
        H = [("Z0Z1", 1.0)]
        c = qaoa_ansatz(H, p=1, mixer="xy")
        assert c.max_qubit + 1 >= 2

    def run_test_multi_angle(self):
        H = [("Z0Z1", 1.0), ("Z1Z2", 0.5)]
        c = qaoa_ansatz(H, p=1, multi_angle=True)
        assert c.max_qubit + 1 >= 3

    def run_test_statevector_validity(self):
        H = [("Z0Z1", 1.0)]
        c = qaoa_ansatz(H, p=1, mixer="xy")
        sv = _statevector(c)
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10


class TestHVA:

    def run_test_basic(self):
        groups = [[("Z0Z1", 1.0)], [("Z1Z2", 0.5)]]
        c = hva(groups, p=2)
        assert c.max_qubit + 1 >= 3

    def run_test_param_count(self):
        groups = [[("Z0Z1", 1.0)], [("Z1Z2", 0.5)], [("Z0Z2", 0.3)]]
        # 3 groups * 2 layers = 6 params
        c = hva(groups, p=2, params=np.zeros(6))
        assert c.max_qubit + 1 >= 3

    def run_test_hf_state(self):
        groups = [[("Z0Z1", 1.0)]]
        c = hva(groups, p=1, hf_state=[0, 1])
        assert c.max_qubit + 1 >= 2

    def run_test_statevector_validity(self):
        groups = [[("Z0Z1", 1.0)]]
        c = hva(groups, p=1)
        sv = _statevector(c)
        assert abs(np.linalg.norm(sv) - 1.0) < 1e-10


class TestTopologyGenerator:

    def run_test_linear_edges(self):
        from uniqc.algorithms.core.ansatz._topology import generate_edges
        edges = generate_edges([0, 1, 2, 3], EntanglementTopology.LINEAR)
        assert len(edges) == 3
        assert (0, 1) in edges
        assert (1, 2) in edges
        assert (2, 3) in edges

    def run_test_ring_edges(self):
        from uniqc.algorithms.core.ansatz._topology import generate_edges
        edges = generate_edges([0, 1, 2, 3], EntanglementTopology.RING)
        assert len(edges) == 4
        assert (0, 1) in edges
        assert (1, 2) in edges
        assert (2, 3) in edges
        assert (3, 0) in edges

    def run_test_full_edges(self):
        from uniqc.algorithms.core.ansatz._topology import generate_edges
        edges = generate_edges([0, 1, 2], EntanglementTopology.FULL)
        assert len(edges) == 3
        assert (0, 1) in edges
        assert (0, 2) in edges
        assert (1, 2) in edges

    def run_test_brickwork_alternation(self):
        from uniqc.algorithms.core.ansatz._topology import generate_edges
        edges_even = generate_edges([0, 1, 2, 3], EntanglementTopology.BRICKWORK, layer_index=0)
        edges_odd = generate_edges([0, 1, 2, 3], EntanglementTopology.BRICKWORK, layer_index=1)
        # Even: (0,1), (2,3)
        # Odd: (1,2)
        assert (0, 1) in edges_even
        assert (2, 3) in edges_even
        assert len(edges_even) == 2
        assert (1, 2) in edges_odd
        assert len(edges_odd) == 1
