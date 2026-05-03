"""TorchQuantumLayer: nn.Module with native PyTorch autograd via TorchQuantum.

Unlike QuantumLayer (parameter-shift rule), this layer gets gradients
for free through TorchQuantum's differentiable statevector simulation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

try:
    import torch
    import torch.nn as nn

    from uniqc.simulator.torchquantum_simulator import TORCHQUANTUM_AVAILABLE, TorchQuantumSimulator

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    TORCHQUANTUM_AVAILABLE = False

    class nn:  # type: ignore
        class Module:
            pass

    torch = None  # type: ignore

if TYPE_CHECKING:
    pass

__all__ = ["TorchQuantumLayer"]

if TORCH_AVAILABLE and TORCHQUANTUM_AVAILABLE:

    class TorchQuantumLayer(nn.Module):
        """PyTorch layer using TorchQuantum for native autograd.

        Takes a circuit builder callable that constructs opcodes from a
        parameter tensor. Gradients propagate through PyTorch autograd
        natively — no parameter-shift rule needed.

        Args:
            circuit_builder: Callable(params_tensor) -> (opcode_list, n_qubits,
                param_overrides). Constructs the circuit with tensor parameters.
            n_qubits: Number of qubits.
            n_params: Number of trainable parameters.
            hamiltonian: List of (pauli_string, coefficient) for expectation.
            init_params: Initial parameter values (optional).
            device: "cpu" or "cuda".
        """

        def __init__(
            self,
            circuit_builder: Callable[[torch.Tensor], tuple],
            n_qubits: int,
            n_params: int,
            hamiltonian: list[tuple[str, float]],
            init_params: torch.Tensor | None = None,
            device: str = "cpu",
        ):
            super().__init__()
            self.circuit_builder = circuit_builder
            self.n_qubits = n_qubits
            self.hamiltonian = hamiltonian
            self._device = device
            self._sim = TorchQuantumSimulator(n_wires=n_qubits, device=device)

            if init_params is not None:
                self.params = nn.Parameter(init_params.clone().to(device))
            else:
                self.params = nn.Parameter(torch.randn(n_params, device=device) * 0.1)

        def forward(self, x: torch.Tensor | None = None) -> torch.Tensor:
            """Execute circuit and return expectation value.

            Args:
                x: Optional input tensor (for data encoding circuits).

            Returns:
                Differentiable scalar tensor with expectation value.
            """
            params = self.params
            if x is not None:
                # Concatenate quantum params with encoded data
                params = torch.cat([self.params, x.flatten()])

            opcode_list, n_qubits, param_overrides = self.circuit_builder(params)
            return self._sim.expectation(opcode_list, self.hamiltonian, param_overrides)

        def extra_repr(self) -> str:
            return f"n_qubits={self.n_qubits}, n_params={len(self.params)}"

else:

    class TorchQuantumLayer:  # type: ignore
        """Placeholder when PyTorch/TorchQuantum is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "PyTorch and TorchQuantum are required. "
                "Install with: pip install unified-quantum[pytorch] && "
                'pip install "torchquantum @ '
                'git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"'
            )
