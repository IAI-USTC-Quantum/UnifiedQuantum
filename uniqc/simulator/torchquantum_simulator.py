"""TorchQuantum-based simulator with native PyTorch autograd.

This module provides a quantum circuit simulator backed by TorchQuantum,
enabling differentiable statevector simulation where gradients flow through
PyTorch autograd natively (no parameter-shift rule needed).

Unlike BaseSimulator subclasses that consume OriginIR/QASM strings,
this simulator reads Circuit.opcode_list directly.

Note: TorchQuantum uses qubit-0-as-MSB convention (the first dimension in the
state tensor is qubit 0). UnifiedQuantum uses qubit-0-as-LSB convention
(standard in most quantum computing frameworks). This simulator handles the
endianness conversion automatically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    TORCH_AVAILABLE = False

try:
    if TORCH_AVAILABLE:
        import torchquantum as tq
        import torchquantum.functional as tqf
        from torchquantum.measurement import expval_joint_analytical

        TORCHQUANTUM_AVAILABLE = True
    else:
        TORCHQUANTUM_AVAILABLE = False
except ImportError:
    tq = None  # type: ignore
    tqf = None  # type: ignore
    expval_joint_analytical = None  # type: ignore
    TORCHQUANTUM_AVAILABLE = False

if TYPE_CHECKING:
    from uniqc.circuit_builder.qcircuit import OpCode

__all__ = ["TORCHQUANTUM_AVAILABLE", "TorchQuantumSimulator"]

if TORCHQUANTUM_AVAILABLE:
    # Gate mapping: Uniqc opcode name → (tqf function, is_parametric)
    _GATE_MAP: dict[str, tuple] = {
        "H": (tqf.hadamard, False),
        "X": (tqf.paulix, False),
        "Y": (tqf.pauliy, False),
        "Z": (tqf.pauliz, False),
        "S": (tqf.s, False),
        "SX": (tqf.sx, False),
        "T": (tqf.t, False),
        "I": (tqf.i, False),
        "RX": (tqf.rx, True),
        "RY": (tqf.ry, True),
        "RZ": (tqf.rz, True),
        "U1": (tqf.u1, True),
        "U2": (tqf.u2, True),
        "U3": (tqf.u3, True),
        "CNOT": (tqf.cnot, False),
        "CZ": (tqf.cz, False),
        "SWAP": (tqf.swap, False),
        "ISWAP": (tqf.iswap, False),
        "XX": (tqf.rxx, True),
        "YY": (tqf.ryy, True),
        "ZZ": (tqf.rzz, True),
        "TOFFOLI": (tqf.toffoli, False),
        "CSWAP": (tqf.cswap, False),
    }

    # Dagger-specific overrides
    _DAGGER_MAP: dict[str, tuple] = {
        "S": (tqf.sdg, False),
        "SX": (tqf.sxdg, False),
        "T": (tqf.tdg, False),
    }
else:
    _GATE_MAP = {}
    _DAGGER_MAP = {}


def _require_torchquantum() -> None:
    """Raise a consistent install hint when TorchQuantum backend is unavailable."""
    if TORCHQUANTUM_AVAILABLE:
        return
    raise ImportError(
        "TorchQuantum backend requires the PyTorch extra. "
        "Install with: pip install unified-quantum[pytorch]"
    )


def _extract_n_qubits(opcode_list: list[OpCode]) -> int:
    """Determine number of qubits from opcodes."""
    max_q = 0
    for _op_name, qubits, _cbits, _params, _dagger, controls in opcode_list:
        max_q = max(max_q, max(qubits) + 1) if isinstance(qubits, list) else max(max_q, qubits + 1)
        if controls:
            ctrl_list = list(controls) if not isinstance(controls, list) else controls
            max_q = max(max_q, max(ctrl_list) + 1)
    return max_q


def _reverse_bits(statevector: torch.Tensor, n_qubits: int) -> torch.Tensor:
    """Reverse bit order in statevector to convert between endianness conventions.

    TorchQuantum: qubit 0 = MSB (first tensor dimension)
    Standard:     qubit 0 = LSB (last bit in binary index)
    """
    dim = 2**n_qubits
    sv = statevector[:dim]
    indices = torch.arange(dim, device=sv.device)
    # Reverse the bits of each index
    reversed_indices = torch.zeros_like(indices)
    for b in range(n_qubits):
        bit = (indices >> b) & 1
        reversed_indices |= bit << (n_qubits - 1 - b)
    return sv[reversed_indices]


def _reverse_pauli_string(pauli_str: str) -> str:
    """Reverse Pauli string to match TorchQuantum's qubit ordering."""
    return pauli_str[::-1]


class TorchQuantumSimulator:
    """TorchQuantum-based simulator with native PyTorch autograd.

    Operates on Circuit.opcode_list directly (no string serialization).
    All operations are differentiable through PyTorch autograd.

    The n_wires parameter is optional — if not set, it is auto-detected
    from the opcodes.
    """

    def __init__(self, n_wires: int = 0, device: str = "cpu"):
        _require_torchquantum()
        self.n_wires = n_wires
        self.device = device

    def _resolve_n_wires(self, opcode_list: list[OpCode]) -> int:
        if self.n_wires > 0:
            return self.n_wires
        return _extract_n_qubits(opcode_list) or 1

    def _create_qdev(self, n_wires: int, bsz: int = 1) -> tq.QuantumDevice:
        return tq.QuantumDevice(n_wires=n_wires, bsz=bsz, device=self.device)

    def execute_opcodes(
        self,
        opcode_list: list[OpCode],
        param_overrides: dict[int, torch.Tensor] | None = None,
        n_qubits: int | None = None,
        bsz: int = 1,
    ) -> tq.QuantumDevice:
        """Execute opcodes on a fresh QuantumDevice.

        Args:
            opcode_list: Circuit.opcode_list.
            param_overrides: Map opcode index → torch.Tensor to inject
                differentiable parameters.
            n_qubits: Override number of qubits (auto-detected if None).
            bsz: Batch size for the QuantumDevice.

        Returns:
            The QuantumDevice after executing all gates.
        """
        if n_qubits is None:
            n_qubits = self._resolve_n_wires(opcode_list)
        qdev = self._create_qdev(n_qubits, bsz)
        param_overrides = param_overrides or {}

        for idx, opcode in enumerate(opcode_list):
            op_name, qubits, _cbits, params, dagger, controls = opcode

            # Resolve gate function
            if dagger and op_name in _DAGGER_MAP:
                gate_fn, is_parametric = _DAGGER_MAP[op_name]
            elif op_name in _GATE_MAP:
                gate_fn, is_parametric = _GATE_MAP[op_name]
            else:
                raise NotImplementedError(f"Gate '{op_name}' is not supported by TorchQuantum backend.")

            # Resolve wires
            wires = qubits if isinstance(qubits, list) else [qubits]
            if controls:
                wires = list(controls) + wires

            # Resolve parameters
            if idx in param_overrides:
                gate_params = param_overrides[idx]
            elif is_parametric and params is not None:
                if isinstance(params, (list, tuple)):
                    raw = [-p for p in params] if dagger else list(params)
                else:
                    raw = [-params] if dagger else [params]
                gate_params = torch.tensor(raw, dtype=torch.float32, device=self.device)
            else:
                gate_params = None

            # Apply gate
            kwargs: dict = {"wires": wires, "inverse": False}
            if gate_params is not None:
                if gate_params.dim() == 0:
                    gate_params = gate_params.unsqueeze(0).unsqueeze(0)
                elif gate_params.dim() == 1:
                    gate_params = gate_params.unsqueeze(0)
                if gate_params.shape[0] != bsz:
                    gate_params = gate_params.expand(bsz, -1)
                kwargs["params"] = gate_params

            gate_fn(qdev, **kwargs)

        return qdev

    def simulate_statevector(
        self,
        opcode_list: list[OpCode],
        param_overrides: dict[int, torch.Tensor] | None = None,
        n_qubits: int | None = None,
    ) -> torch.Tensor:
        """Execute circuit and return statevector (LSB convention).

        Returns:
            Complex tensor of shape (2^n_qubits,) with the final statevector.
        """
        if n_qubits is None:
            n_qubits = self._resolve_n_wires(opcode_list)
        qdev = self.execute_opcodes(opcode_list, param_overrides, n_qubits, bsz=1)
        sv_tq = qdev.get_states_1d().squeeze(0)
        return _reverse_bits(sv_tq, n_qubits)

    def expectation(
        self,
        opcode_list: list[OpCode],
        hamiltonian: list[tuple[str, float]],
        param_overrides: dict[int, torch.Tensor] | None = None,
        n_qubits: int | None = None,
    ) -> torch.Tensor:
        """Compute <psi|H|psi> for a Pauli Hamiltonian.

        Args:
            opcode_list: Circuit.opcode_list.
            hamiltonian: List of (pauli_string, coefficient).
            param_overrides: Differentiable parameter injection.
            n_qubits: Override number of qubits.

        Returns:
            Scalar tensor with the expectation value (differentiable).
        """
        if n_qubits is None:
            n_qubits = self._resolve_n_wires(opcode_list)
        total = torch.tensor(0.0, dtype=torch.float32, device=self.device)

        for pauli_str, coeff in hamiltonian:
            if abs(coeff) < 1e-15:
                continue
            if all(c == "I" for c in pauli_str):
                total = total + coeff
                continue

            qdev = self.execute_opcodes(opcode_list, param_overrides, n_qubits, bsz=1)
            # Reverse Pauli string to match TorchQuantum's qubit ordering
            tq_pauli = _reverse_pauli_string(pauli_str)
            expval = expval_joint_analytical(qdev, tq_pauli)
            total = total + coeff * expval.squeeze()

        return total
