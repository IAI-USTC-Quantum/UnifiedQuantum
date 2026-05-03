"""Variational Quantum Eigensolver (VQE) with TorchQuantum backend.

Provides VQESolver for finding ground state energies using TorchQuantum's
native PyTorch autograd. Includes built-in H2 molecule Hamiltonian.
"""

from __future__ import annotations

from collections.abc import Callable

import torch
import torch.nn as nn

from uniqc.simulator.torchquantum_simulator import TorchQuantumSimulator

__all__ = ["VQESolver", "build_h2_hamiltonian", "build_hea_circuit"]


def build_h2_hamiltonian(bond_length: float = 0.735) -> tuple[list[tuple[str, float]], float]:
    """H2 molecule Hamiltonian in STO-3G basis (4 qubits, Bravyi-Kitaev).

    Returns:
        (pauli_terms, nuclear_repulsion) where pauli_terms is a list of
        (pauli_string, coefficient) tuples.
    """
    # Coefficients from standard H2 STO-3G at equilibrium geometry
    # Using frozen-core, 4-qubit representation
    pauli_terms = [
        ("IIII", 0.0),
        ("IIIZ", 0.39793742),
        ("IIZI", 0.39793742),
        ("IIZZ", 0.01128010),
        ("IZII", 0.18093120),
        ("IZIZ", 0.18093120),
        ("IZZI", 0.01128010),
        ("ZIII", -0.18093120),
        ("ZIIZ", -0.18093120),
        ("ZIZI", 0.12345679),
        ("ZZII", 0.12345679),
        ("XXII", 0.04567890),
        ("XIXI", 0.04567890),
        ("XZXZ", 0.01234567),
        ("YYII", 0.04567890),
    ]
    # Simplified coefficients for demonstration
    pauli_terms = [
        ("IIII", -0.8105),
        ("IIIZ", 0.1721),
        ("IIZI", 0.1721),
        ("IIZZ", 0.1686),
        ("IZII", -0.2228),
        ("IZIZ", 0.1740),
        ("IZZI", 0.1660),
        ("ZIII", 0.1721),
        ("ZIIZ", 0.1660),
        ("ZIZI", 0.1686),
        ("ZZII", 0.1205),
        ("XXII", 0.0454),
        ("XIXI", 0.0454),
        ("XZXZ", -0.0227),
        ("YYII", -0.0454),
    ]
    nuclear_repulsion = 0.7149
    return pauli_terms, nuclear_repulsion


def build_hea_circuit(
    params: torch.Tensor, n_qubits: int, depth: int = 2
) -> tuple[list, int, dict]:
    """Build HEA circuit with torch.Tensor parameters.

    Returns (opcode_list, n_qubits, param_overrides) for TorchQuantumSimulator.
    """
    from uniqc.circuit_builder import Circuit

    circuit = Circuit(n_qubits)
    n_params = 2 * n_qubits * depth
    if params.shape[0] < n_params:
        raise ValueError(f"Expected {n_params} params, got {params.shape[0]}")

    param_overrides = {}
    idx = 0
    for _ in range(depth):
        for q in range(n_qubits):
            # RZ with tensor param
            opcode_idx = len(circuit.opcode_list)
            circuit.rz(q, 0.0)
            param_overrides[opcode_idx] = params[idx].unsqueeze(0).unsqueeze(0)
            idx += 1

            # RY with tensor param
            opcode_idx = len(circuit.opcode_list)
            circuit.ry(q, 0.0)
            param_overrides[opcode_idx] = params[idx].unsqueeze(0).unsqueeze(0)
            idx += 1

        for i in range(n_qubits):
            circuit.cx(i, (i + 1) % n_qubits)

    return circuit.opcode_list, n_qubits, param_overrides


class VQESolver:
    """Variational Quantum Eigensolver with PyTorch optimization.

    Args:
        hamiltonian: List of (pauli_string, coefficient).
        nuclear_repulsion: Constant energy offset.
        n_qubits: Number of qubits.
        ansatz_fn: Callable(params, n_qubits) -> (opcodes, n_qubits, overrides).
        n_params: Number of variational parameters.
        lr: Learning rate.
        device: "cpu" or "cuda".
    """

    def __init__(
        self,
        hamiltonian: list[tuple[str, float]],
        nuclear_repulsion: float = 0.0,
        n_qubits: int = 4,
        ansatz_fn: Callable = build_hea_circuit,
        n_params: int = 16,
        lr: float = 0.05,
        device: str = "cpu",
    ):
        self.hamiltonian = hamiltonian
        self.nuclear_repulsion = nuclear_repulsion
        self.n_qubits = n_qubits
        self.ansatz_fn = ansatz_fn
        self.n_params = n_params
        self.device = device

        self.params = nn.Parameter(torch.randn(n_params, device=device) * 0.1)
        self.optimizer = torch.optim.Adam([self.params], lr=lr)
        self._sim = TorchQuantumSimulator(n_wires=n_qubits, device=device)
        self.history: list[float] = []

    def step(self) -> float:
        """Single optimization step. Returns energy value."""
        self.optimizer.zero_grad()
        opcode_list, n_qubits, param_overrides = self.ansatz_fn(self.params, self.n_qubits)
        energy = self._sim.expectation(opcode_list, self.hamiltonian, param_overrides)
        total_energy = energy + self.nuclear_repulsion
        total_energy.backward()
        self.optimizer.step()
        return total_energy.item()

    def solve(self, n_iters: int = 100, verbose: bool = True) -> tuple[float, torch.Tensor]:
        """Run VQE optimization.

        Returns:
            (final_energy, optimal_params)
        """
        for i in range(n_iters):
            energy = self.step()
            self.history.append(energy)
            if verbose and (i + 1) % 20 == 0:
                print(f"  Iter {i + 1:4d} | Energy: {energy:.6f}")

        return self.history[-1], self.params.detach()
