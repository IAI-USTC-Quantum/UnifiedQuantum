"""Hybrid Classical-Quantum model with TorchQuantum backend.

Combines classical neural network layers with a quantum circuit layer
for hybrid quantum-classical machine learning.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from uniqc.simulator.torchquantum_simulator import TorchQuantumSimulator

__all__ = ["HybridQCLModel"]


def _build_hybrid_qlayer_circuit(
    params: torch.Tensor,
    n_qubits: int,
    depth: int = 2,
    x_encoded: torch.Tensor | None = None,
) -> tuple[list, int, dict]:
    """Build quantum circuit for hybrid model.

    Encodes classical features via angle encoding, then applies HEA.
    """
    from uniqc.circuit_builder import Circuit

    circuit = Circuit(n_qubits)
    param_overrides = {}

    # Data encoding from classical encoder output
    if x_encoded is not None:
        for q in range(min(x_encoded.shape[0], n_qubits)):
            opcode_idx = len(circuit.opcode_list)
            circuit.ry(q, 0.0)
            param_overrides[opcode_idx] = x_encoded[q].unsqueeze(0).unsqueeze(0)

    # Variational HEA
    idx = 0
    n_variational = len(params)
    for _ in range(depth):
        for q in range(n_qubits):
            if idx >= n_variational:
                break
            opcode_idx = len(circuit.opcode_list)
            circuit.rz(q, 0.0)
            param_overrides[opcode_idx] = params[idx].unsqueeze(0).unsqueeze(0)
            idx += 1

            if idx >= n_variational:
                break
            opcode_idx = len(circuit.opcode_list)
            circuit.ry(q, 0.0)
            param_overrides[opcode_idx] = params[idx].unsqueeze(0).unsqueeze(0)
            idx += 1

        if idx >= n_variational:
            break
        for i in range(n_qubits):
            circuit.cx(i, (i + 1) % n_qubits)

    return circuit.opcode_list, n_qubits, param_overrides


class HybridQCLModel(nn.Module):
    """Hybrid Classical-Quantum model.

    Architecture: ClassicalEncoder → QuantumLayer → ClassicalDecoder

    Args:
        n_features: Input feature dimension.
        n_qubits: Number of quantum circuit qubits.
        quantum_depth: HEA depth for quantum layer.
        classical_hidden: Hidden layer size for classical nets.
    """

    def __init__(
        self,
        n_features: int = 2,
        n_qubits: int = 4,
        quantum_depth: int = 2,
        classical_hidden: int = 32,
    ):
        super().__init__()
        self.n_qubits = n_qubits
        self.quantum_depth = quantum_depth

        # Classical encoder: maps input features to quantum-compatible angles
        self.encoder = nn.Sequential(
            nn.Linear(n_features, classical_hidden),
            nn.ReLU(),
            nn.Linear(classical_hidden, n_qubits),
            nn.Tanh(),  # output in [-1, 1], scaled to angle range later
        )

        # Quantum parameters
        n_quantum_params = 2 * n_qubits * quantum_depth
        self.quantum_params = nn.Parameter(torch.randn(n_quantum_params) * 0.1)

        # Measurement
        self.hamiltonian = [("Z" + "I" * (n_qubits - 1), 1.0)]

        # Classical decoder
        self.decoder = nn.Sequential(
            nn.Linear(1, classical_hidden),
            nn.ReLU(),
            nn.Linear(classical_hidden, 1),
            nn.Sigmoid(),
        )

        self._sim = TorchQuantumSimulator(n_wires=n_qubits)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through hybrid model.

        Args:
            x: Input tensor of shape (batch_size, n_features).

        Returns:
            Output tensor of shape (batch_size, 1).
        """
        batch_size = x.shape[0]
        outputs = []

        for i in range(batch_size):
            # Classical encoding
            encoded = self.encoder(x[i]) * torch.pi  # scale to angle range

            # Quantum circuit
            opcode_list, n_qubits, param_overrides = _build_hybrid_qlayer_circuit(
                self.quantum_params, self.n_qubits, self.quantum_depth, encoded
            )
            expval = self._sim.expectation(opcode_list, self.hamiltonian, param_overrides)
            q_output = expval.unsqueeze(0).unsqueeze(0)  # shape (1, 1)

            # Classical decoding
            output = self.decoder(q_output)
            outputs.append(output)

        return torch.cat(outputs, dim=0)
