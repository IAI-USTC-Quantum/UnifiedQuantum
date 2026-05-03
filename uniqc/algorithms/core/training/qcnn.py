"""Quantum Convolutional Neural Network (QCNN) with TorchQuantum backend.

Implements convolutional and pooling layers on qubits for quantum state
classification, using TorchQuantum's native PyTorch autograd.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from uniqc.simulator.torchquantum_simulator import TorchQuantumSimulator

__all__ = ["QCNNClassifier"]


def _build_qcnn_circuit(
    params: torch.Tensor,
    n_qubits: int,
) -> tuple[list, int, dict]:
    """Build QCNN circuit with conv and pooling layers.

    Architecture:
    1. Conv layers: parameterized 2-qubit gates on neighboring pairs
    2. Pool layers: CNOT-based reduction (halve active qubits)
    3. Final measurement on remaining qubits

    Returns (opcode_list, n_qubits, param_overrides).
    """
    from uniqc.circuit_builder import Circuit

    circuit = Circuit(n_qubits)
    param_overrides = {}
    param_idx = 0
    active_qubits = list(range(n_qubits))

    while len(active_qubits) > 1:
        # Convolution layer: parameterized 2-qubit gates on pairs
        for i in range(0, len(active_qubits) - 1, 2):
            q1, q2 = active_qubits[i], active_qubits[i + 1]

            # RZ on q1
            opcode_idx = len(circuit.opcode_list)
            circuit.rz(q1, 0.0)
            param_overrides[opcode_idx] = params[param_idx].unsqueeze(0).unsqueeze(0)
            param_idx += 1

            # RY on q2
            opcode_idx = len(circuit.opcode_list)
            circuit.ry(q2, 0.0)
            param_overrides[opcode_idx] = params[param_idx].unsqueeze(0).unsqueeze(0)
            param_idx += 1

            # CNOT entangle
            circuit.cx(q1, q2)

            # RZ on q2
            opcode_idx = len(circuit.opcode_list)
            circuit.rz(q2, 0.0)
            param_overrides[opcode_idx] = params[param_idx].unsqueeze(0).unsqueeze(0)
            param_idx += 1

        # Pooling layer: CNOT to halve active qubits
        new_active = []
        for i in range(0, len(active_qubits) - 1, 2):
            q1, q2 = active_qubits[i], active_qubits[i + 1]
            circuit.cx(q2, q1)
            new_active.append(q1)  # keep q1, discard q2

        if len(active_qubits) % 2 == 1:
            new_active.append(active_qubits[-1])

        active_qubits = new_active

    return circuit.opcode_list, n_qubits, param_overrides


class QCNNClassifier(nn.Module):
    """Quantum Convolutional Neural Network for classification.

    Applies convolutional and pooling layers that progressively reduce
    the number of active qubits, then measures the final qubit.

    Args:
        n_qubits: Number of qubits (preferably power of 2).
        n_classes: Number of output classes.
    """

    def __init__(self, n_qubits: int = 8, n_classes: int = 2):
        super().__init__()
        self.n_qubits = n_qubits
        self.n_classes = n_classes

        # Calculate number of parameters
        # Each conv layer uses 3 params per pair, pooling uses 0
        # Number of pairs halves each round
        n_params = 0
        active = n_qubits
        while active > 1:
            n_pairs = active // 2
            n_params += n_pairs * 3
            active = (active + 1) // 2

        self.n_params = n_params
        self.params = nn.Parameter(torch.randn(n_params) * 0.1)

        # Measurement: <Z_0> for binary, or multi-qubit for multi-class
        if n_classes == 2:
            self.hamiltonian = [("Z" + "I" * (n_qubits - 1), 1.0)]
        else:
            self.hamiltonian = [("I" * n_qubits, 1.0)]  # placeholder

        self._sim = TorchQuantumSimulator(n_wires=n_qubits)

    def forward(self, x: torch.Tensor | None = None) -> torch.Tensor:
        """Classify quantum state.

        Returns:
            Probability-like output in [0, 1].
        """
        opcode_list, n_qubits, param_overrides = _build_qcnn_circuit(
            self.params, self.n_qubits
        )
        expval = self._sim.expectation(opcode_list, self.hamiltonian, param_overrides)
        return (expval + 1.0) / 2.0
