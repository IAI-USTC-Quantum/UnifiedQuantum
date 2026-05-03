"""Quantum Approximate Optimization Algorithm (QAOA) with TorchQuantum backend.

Provides QAOASolver for combinatorial optimization using TorchQuantum's
native PyTorch autograd. Includes built-in MaxCut Hamiltonian.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from uniqc.simulator.torchquantum_simulator import TorchQuantumSimulator

__all__ = ["QAOASolver", "build_maxcut_hamiltonian", "build_qaoa_circuit"]


def build_maxcut_hamiltonian(edges: list[tuple[int, int]], n_qubits: int) -> list[tuple[str, float]]:
    """Build MaxCut cost Hamiltonian from graph edges.

    H_C = 0.5 * sum_{(i,j)} (I - Z_i Z_j)

    Returns list of (pauli_string, coefficient).
    """
    pauli_terms: list[tuple[str, float]] = []

    for i, j in edges:
        # I term: 0.5 per edge
        pauli_terms.append(("I" * n_qubits, 0.5))
        # -Z_i Z_j term: -0.5 per edge
        chars = ["I"] * n_qubits
        chars[i] = "Z"
        chars[j] = "Z"
        pauli_terms.append(("".join(chars), -0.5))

    return pauli_terms


def build_qaoa_circuit(
    params: torch.Tensor,
    n_qubits: int,
    edges: list[tuple[int, int]],
    p: int = 1,
) -> tuple[list, int, dict]:
    """Build QAOA circuit with torch.Tensor parameters.

    params layout: [gamma_0, ..., gamma_{p-1}, beta_0, ..., beta_{p-1}]

    Returns (opcode_list, n_qubits, param_overrides).
    """
    from uniqc.circuit_builder import Circuit

    circuit = Circuit(n_qubits)
    param_overrides = {}

    # Initial Hadamard on all qubits
    for q in range(n_qubits):
        circuit.h(q)

    gammas = params[:p]
    betas = params[p : 2 * p]

    for layer in range(p):
        # Cost unitary: exp(-i * gamma * H_C)
        for i, j in edges:
            # ZZ interaction
            opcode_idx = len(circuit.opcode_list)
            circuit.zz(i, j, 0.0)
            param_overrides[opcode_idx] = (2.0 * gammas[layer]).unsqueeze(0).unsqueeze(0)

        # Mixer unitary: exp(-i * beta * sum X_i)
        for q in range(n_qubits):
            opcode_idx = len(circuit.opcode_list)
            circuit.rx(q, 0.0)
            param_overrides[opcode_idx] = (2.0 * betas[layer]).unsqueeze(0).unsqueeze(0)

    return circuit.opcode_list, n_qubits, param_overrides


class QAOASolver:
    """QAOA with PyTorch optimization.

    Args:
        edges: Graph edges for MaxCut.
        n_qubits: Number of qubits (= graph vertices).
        p: Number of QAOA layers.
        lr: Learning rate.
        device: "cpu" or "cuda".
    """

    def __init__(
        self,
        edges: list[tuple[int, int]],
        n_qubits: int,
        p: int = 1,
        lr: float = 0.05,
        device: str = "cpu",
    ):
        self.edges = edges
        self.n_qubits = n_qubits
        self.p = p
        self.device = device

        self.hamiltonian = build_maxcut_hamiltonian(edges, n_qubits)
        self.n_params = 2 * p

        self.params = nn.Parameter(torch.randn(self.n_params, device=device) * 0.5)
        self.optimizer = torch.optim.Adam([self.params], lr=lr)
        self._sim = TorchQuantumSimulator(n_wires=n_qubits, device=device)
        self.history: list[float] = []

    def step(self) -> float:
        """Single optimization step. Returns cost value."""
        self.optimizer.zero_grad()

        gammas = self.params[: self.p]
        betas = self.params[self.p :]
        params = torch.cat([gammas, betas])

        opcode_list, n_qubits, param_overrides = build_qaoa_circuit(
            params, self.n_qubits, self.edges, self.p
        )
        cost = self._sim.expectation(opcode_list, self.hamiltonian, param_overrides)
        # Minimize negative cut value = maximize cut
        (-cost).backward()
        self.optimizer.step()
        return cost.item()

    def solve(self, n_iters: int = 100, verbose: bool = True) -> tuple[float, torch.Tensor]:
        """Run QAOA optimization.

        Returns:
            (best_cut_value, optimal_params)
        """
        for i in range(n_iters):
            cost = self.step()
            self.history.append(cost)
            if verbose and (i + 1) % 20 == 0:
                print(f"  Iter {i + 1:4d} | Cut value: {cost:.6f}")

        return self.history[-1], self.params.detach()
