"""Quantum Neural Network (QNN) classifier with TorchQuantum backend.

Provides QNNClassifier — an nn.Module for binary classification using
Hardware-Efficient Ansatz and TorchQuantum's native autograd.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from uniqc.simulator.torchquantum_simulator import TorchQuantumSimulator

__all__ = ["QNNClassifier"]


def _build_qnn_circuit(
    params: torch.Tensor,
    n_qubits: int,
    n_features: int,
    depth: int,
    x: torch.Tensor | None = None,
) -> tuple[list, int, dict]:
    """Build QNN circuit: data encoding + variational HEA.

    params[:n_features]: unused when x is provided (data encoding angles)
    params[n_features:]: variational parameters
    """
    from uniqc.circuit_builder import Circuit

    circuit = Circuit(n_qubits)
    param_overrides = {}

    # Data encoding: angle encoding via RY
    if x is not None:
        for q in range(min(n_features, n_qubits)):
            opcode_idx = len(circuit.opcode_list)
            circuit.ry(q, 0.0)
            param_overrides[opcode_idx] = x[q].unsqueeze(0).unsqueeze(0)

    # Variational layers (HEA)
    idx = 0
    for _ in range(depth):
        for q in range(n_qubits):
            opcode_idx = len(circuit.opcode_list)
            circuit.rz(q, 0.0)
            param_overrides[opcode_idx] = params[idx].unsqueeze(0).unsqueeze(0)
            idx += 1

            opcode_idx = len(circuit.opcode_list)
            circuit.ry(q, 0.0)
            param_overrides[opcode_idx] = params[idx].unsqueeze(0).unsqueeze(0)
            idx += 1

        for i in range(n_qubits):
            circuit.cx(i, (i + 1) % n_qubits)

    return circuit.opcode_list, n_qubits, param_overrides


class QNNClassifier(nn.Module):
    """Quantum Neural Network for binary classification.

    Uses angle encoding for input features and HEA for variational layer.
    Output is σ(<Z₀>) for binary classification.

    Args:
        n_qubits: Number of qubits.
        n_features: Input feature dimension.
        depth: HEA depth.
    """

    def __init__(self, n_qubits: int = 4, n_features: int = 2, depth: int = 2):
        super().__init__()
        self.n_qubits = n_qubits
        self.n_features = n_features
        self.depth = depth
        self.n_variational = 2 * n_qubits * depth

        # Variational parameters
        self.params = nn.Parameter(torch.randn(self.n_variational) * 0.1)

        # Measurement: <Z_0> for classification
        self.hamiltonian = [("Z" + "I" * (n_qubits - 1), 1.0)]

        self._sim = TorchQuantumSimulator(n_wires=n_qubits)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Classify input batch.

        Args:
            x: Input tensor of shape (batch_size, n_features).

        Returns:
            Probability tensor of shape (batch_size,).
        """
        batch_size = x.shape[0]
        outputs = []

        for i in range(batch_size):
            # Scale input to [0, π]
            x_scaled = x[i] * torch.pi

            circuit_params = self.params
            opcode_list, n_qubits, param_overrides = _build_qnn_circuit(
                circuit_params, self.n_qubits, self.n_features, self.depth, x_scaled
            )
            expval = self._sim.expectation(opcode_list, self.hamiltonian, param_overrides)
            # Map [-1, 1] to [0, 1] via sigmoid-like transform
            prob = (expval + 1.0) / 2.0
            outputs.append(prob)

        return torch.stack(outputs)
