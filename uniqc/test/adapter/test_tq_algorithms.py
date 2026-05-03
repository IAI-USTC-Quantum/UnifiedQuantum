"""Tests for variational algorithms using TorchQuantum backend."""

from __future__ import annotations

import pytest

torchquantum = pytest.importorskip("torchquantum", reason="torchquantum not installed")


from uniqc.algorithms.core.training.qaoa_torch import QAOASolver
from uniqc.algorithms.core.training.vqe_torch import VQESolver, build_h2_hamiltonian


class TestVQE:
    def test_vqe_h2_converges(self):
        pauli_terms, nuclear_repulsion = build_h2_hamiltonian()
        solver = VQESolver(
            hamiltonian=pauli_terms,
            nuclear_repulsion=nuclear_repulsion,
            n_qubits=4,
            n_params=16,
            lr=0.05,
        )
        final_energy, _ = solver.solve(n_iters=50, verbose=False)
        # Energy should decrease
        assert solver.history[-1] < solver.history[0]
        # Should be below 0 (ground state)
        assert final_energy < 0.0

    def test_vqe_gradient_flows(self):
        pauli_terms, nuclear_repulsion = build_h2_hamiltonian()
        solver = VQESolver(
            hamiltonian=pauli_terms,
            nuclear_repulsion=nuclear_repulsion,
            n_qubits=4,
            n_params=16,
        )
        # Verify params have grad after a step
        solver.step()
        assert solver.params.grad is not None


class TestQAOA:
    def test_qaoa_triangle_converges(self):
        edges = [(0, 1), (1, 2), (0, 2)]
        solver = QAOASolver(edges=edges, n_qubits=3, p=1, lr=0.05)
        cut_value, _ = solver.solve(n_iters=50, verbose=False)
        # Should find positive cut value
        assert cut_value > 0.0
        # Max cut for triangle is 2.0, approximation ratio > 0.25
        assert cut_value / 2.0 > 0.25

    def test_qaoa_gradient_flows(self):
        edges = [(0, 1)]
        solver = QAOASolver(edges=edges, n_qubits=2, p=1)
        solver.step()
        assert solver.params.grad is not None
