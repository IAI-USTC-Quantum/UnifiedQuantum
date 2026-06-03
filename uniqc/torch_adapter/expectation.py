"""Backend-agnostic differentiable expectation values for quantum circuits.

Public API::

    expectation(circuit, hamiltonian, param_map=None, backend="virtual") -> Tensor

The ``backend`` parameter selects the execution engine:

* ``"virtual"`` (default) — native PyTorch statevector simulation, fully
  differentiable, no external dependencies beyond torch.
* ``"torchquantum"`` — delegates to the TorchQuantum-based simulator (optional).

Additional backends (density matrix, MPS, real hardware) can be registered
in future versions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from uniqc.circuit_builder.qcircuit import Circuit

__all__ = ["expectation"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def expectation(
    circuit: Circuit,
    hamiltonian: list[tuple[str, float]],
    param_map: dict | None = None,
    backend: str = "virtual",
) -> "torch.Tensor":
    """Compute the differentiable expectation value ⟨ψ|H|ψ⟩.

    Args:
        circuit: A :class:`Circuit` whose ``opcode_list`` defines the unitary.
        hamiltonian: List of ``(pauli_string, coefficient)`` tuples.
            Each *pauli_string* is a sequence of ``I``, ``X``, ``Y``, ``Z``
            characters (e.g. ``"ZII"``, ``"XX"``).  The length must match
            the number of qubits acted on by the circuit.
        param_map: Optional ``{opcode_index: torch.Tensor}`` mapping that
            overrides the float values stored in the opcode ``params`` field.
            If *None*, falls back to ``circuit.param_map``.
        backend: Execution backend.  ``"virtual"`` (default) uses a native
            PyTorch statevector simulation.  ``"torchquantum"`` delegates to
            the TorchQuantum-based simulator.

    Returns:
        A scalar ``torch.Tensor`` (with ``requires_grad`` when any tensor
        in *param_map* requires gradients).
    """
    if not TORCH_AVAILABLE:
        raise ImportError(
            "PyTorch is required for expectation(). "
            "Install with: pip install unified-quantum[pytorch]"
        )

    backend_key = backend.strip().replace("-", "_").lower()
    pm = param_map if param_map is not None else getattr(circuit, "param_map", None) or {}

    if backend_key == "virtual":
        return _expectation_virtual(circuit.opcode_list, hamiltonian, pm, circuit.qubit_num)
    if backend_key == "torchquantum":
        return _expectation_torchquantum(circuit.opcode_list, hamiltonian, pm, circuit.qubit_num)

    raise ValueError(
        f"Unknown expectation backend: {backend!r}.  "
        f"Supported: 'virtual', 'torchquantum'."
    )


# ---------------------------------------------------------------------------
# Backend: virtual  (native PyTorch statevector, no external deps)
# ---------------------------------------------------------------------------

def _expectation_virtual(
    opcode_list: list,
    hamiltonian: list[tuple[str, float]],
    param_map: dict,
    n_qubits: int,
) -> "torch.Tensor":
    state = _execute_opcodes(opcode_list, param_map, n_qubits)
    total = torch.tensor(0.0, dtype=torch.float32)
    for pauli_str, coeff in hamiltonian:
        if abs(coeff) < 1e-15:
            continue
        if all(c == "I" for c in pauli_str):
            total = total + coeff
            continue
        expval = _pauli_expval(state, pauli_str)
        total = total + coeff * expval
    return total


# ---------------------------------------------------------------------------
# Backend: torchquantum  (optional, delegates to TorchQuantumSimulator)
# ---------------------------------------------------------------------------

def _expectation_torchquantum(
    opcode_list: list,
    hamiltonian: list[tuple[str, float]],
    param_map: dict,
    n_qubits: int,
) -> "torch.Tensor":
    from uniqc.simulator.torchquantum_simulator import TorchQuantumSimulator

    sim = TorchQuantumSimulator(n_wires=n_qubits)
    return sim.expectation(opcode_list, hamiltonian, param_map, n_qubits)


# ===========================================================================
#  Native differentiable statevector engine (private)
# ===========================================================================

# ---- linear-algebra helpers ------------------------------------------------

def _eye(n: int) -> "torch.Tensor":
    return torch.eye(n, dtype=torch.complex64)


def _kron(a: "torch.Tensor", b: "torch.Tensor") -> "torch.Tensor":
    return torch.kron(a, b)


# ---- static gate matrices --------------------------------------------------

_SQRT2_INV = 0.5**0.5

_H = torch.tensor([[_SQRT2_INV, _SQRT2_INV], [_SQRT2_INV, -_SQRT2_INV]], dtype=torch.complex64)
_X = torch.tensor([[0, 1], [1, 0]], dtype=torch.complex64)
_Y = torch.tensor([[0, -1j], [1j, 0]], dtype=torch.complex64)
_Z = torch.tensor([[1, 0], [0, -1]], dtype=torch.complex64)
_S = torch.tensor([[1, 0], [0, 1j]], dtype=torch.complex64)
_SDG = torch.tensor([[1, 0], [0, -1j]], dtype=torch.complex64)
_T = torch.tensor([[1, 0], [0, (1 + 1j) * _SQRT2_INV]], dtype=torch.complex64)
_TDG = torch.tensor([[1, 0], [0, (1 - 1j) * _SQRT2_INV]], dtype=torch.complex64)
_I2 = _eye(2)

# SX = (I + iX) / sqrt(2)  =  [[1+i, 1-i], [1-i, 1+i]] / 2
_SX = torch.tensor([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=torch.complex64) / 2
_SXDG = _SX.conj().T

_SWAP = torch.tensor([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=torch.complex64)
_ISWAP = torch.tensor([[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]], dtype=torch.complex64)


# ---- parametric gate matrices (differentiable) ----------------------------

def _rx_matrix(theta: "torch.Tensor") -> "torch.Tensor":
    c = torch.cos(theta / 2).to(torch.complex64)
    s = torch.sin(theta / 2).to(torch.complex64)
    return torch.stack([torch.stack([c, -1j * s]), torch.stack([-1j * s, c])])


def _ry_matrix(theta: "torch.Tensor") -> "torch.Tensor":
    c = torch.cos(theta / 2).to(torch.complex64)
    s = torch.sin(theta / 2).to(torch.complex64)
    return torch.stack([torch.stack([c, -s]), torch.stack([s, c])])


def _rz_matrix(theta: "torch.Tensor") -> "torch.Tensor":
    p = torch.exp(-1j * theta / 2).to(torch.complex64)
    m = torch.exp(1j * theta / 2).to(torch.complex64)
    return torch.stack([torch.stack([p, torch.zeros_like(p)]), torch.stack([torch.zeros_like(m), m])])


def _u1_matrix(lam: "torch.Tensor") -> "torch.Tensor":
    p = torch.exp(1j * lam).to(torch.complex64)
    return torch.stack([torch.stack([torch.ones_like(p), torch.zeros_like(p)]),
                        torch.stack([torch.zeros_like(p), p])])


def _u3_matrix(theta: "torch.Tensor", phi: "torch.Tensor", lam: "torch.Tensor") -> "torch.Tensor":
    ct = torch.cos(theta / 2).to(torch.complex64)
    st = torch.sin(theta / 2).to(torch.complex64)
    ep = torch.exp(1j * phi).to(torch.complex64)
    el = torch.exp(1j * lam).to(torch.complex64)
    epl = torch.exp(1j * (phi + lam)).to(torch.complex64)
    return torch.stack([
        torch.stack([ct, -el * st]),
        torch.stack([ep * st, epl * ct]),
    ])


def _rxx_matrix(theta: "torch.Tensor") -> "torch.Tensor":
    c = torch.cos(theta / 2).to(torch.complex64)
    s = torch.sin(theta / 2).to(torch.complex64)
    z = torch.zeros_like(c)
    o = torch.ones_like(c)
    return torch.stack([
        torch.stack([c, z, z, -1j * s]),
        torch.stack([z, c, -1j * s, z]),
        torch.stack([z, -1j * s, c, z]),
        torch.stack([-1j * s, z, z, c]),
    ])


def _ryy_matrix(theta: "torch.Tensor") -> "torch.Tensor":
    c = torch.cos(theta / 2).to(torch.complex64)
    s = torch.sin(theta / 2).to(torch.complex64)
    z = torch.zeros_like(c)
    return torch.stack([
        torch.stack([c, z, z, 1j * s]),
        torch.stack([z, c, -1j * s, z]),
        torch.stack([z, -1j * s, c, z]),
        torch.stack([1j * s, z, z, c]),
    ])


def _rzz_matrix(theta: "torch.Tensor") -> "torch.Tensor":
    p = torch.exp(-1j * theta / 2).to(torch.complex64)
    m = torch.exp(1j * theta / 2).to(torch.complex64)
    z = torch.zeros_like(p)
    return torch.stack([
        torch.stack([p, z, z, z]),
        torch.stack([z, m, z, z]),
        torch.stack([z, z, m, z]),
        torch.stack([z, z, z, p]),
    ])


def _build_cnot_matrix(n_qubits: int, control_wire: int, target_wire: int) -> "torch.Tensor":
    dim = 2**n_qubits
    mat = torch.zeros(dim, dim, dtype=torch.complex64)
    for i in range(dim):
        if (i >> control_wire) & 1:
            j = i ^ (1 << target_wire)
            mat[j, i] = 1.0
        else:
            mat[i, i] = 1.0
    return mat


def _build_cz_matrix(n_qubits: int, w1: int, w2: int) -> "torch.Tensor":
    dim = 2**n_qubits
    mat = torch.eye(dim, dtype=torch.complex64)
    for i in range(dim):
        if ((i >> w1) & 1) and ((i >> w2) & 1):
            mat[i, i] = -1.0
    return mat


def _build_toffoli_matrix(n_qubits: int, c1: int, c2: int, target: int) -> "torch.Tensor":
    dim = 2**n_qubits
    mat = torch.eye(dim, dtype=torch.complex64)
    for i in range(dim):
        if ((i >> c1) & 1) and ((i >> c2) & 1):
            j = i ^ (1 << target)
            mat[i, i] = 0.0
            mat[j, i] = 1.0
    return mat


def _build_cswap_matrix(n_qubits: int, ctrl: int, a: int, b: int) -> "torch.Tensor":
    dim = 2**n_qubits
    mat = torch.eye(dim, dtype=torch.complex64)
    for i in range(dim):
        if (i >> ctrl) & 1:
            bit_a = (i >> a) & 1
            bit_b = (i >> b) & 1
            if bit_a != bit_b:
                j = i ^ (1 << a) ^ (1 << b)
                mat[i, i] = 0.0
                mat[j, i] = 1.0
    return mat


# ---- gate application on multi-dim state -----------------------------------

def _apply_1q_gate(state: "torch.Tensor", mat: "torch.Tensor", wire: int) -> "torch.Tensor":
    """Apply a 2x2 unitary to *wire* (LSB-indexed) of the state tensor."""
    n = state.dim() - 1
    d = n - 1 - wire  # MSB dim index (1-indexed, after batch)
    s = state.movedim(d + 1, -1)
    s = torch.einsum("ij,...j->...i", mat, s)
    return s.movedim(-1, d + 1)


def _apply_2q_gate(state: "torch.Tensor", mat: "torch.Tensor", w0: int, w1: int) -> "torch.Tensor":
    """Apply a 4x4 unitary to wires (*w0*, *w1*) of the state tensor."""
    return _apply_multiq_gate(state, mat, [w0, w1])


def _apply_multiq_gate(state: "torch.Tensor", mat: "torch.Tensor", wires: list[int]) -> "torch.Tensor":
    """Apply a 2^k x 2^k unitary to *wires* (LSB-indexed, control first).

    Moves target qubit dims to the end of the tensor, applies the gate via
    matrix multiplication, then moves them back.
    """
    n = state.dim() - 1
    k = len(wires)
    batch_shape = state.shape[:1]
    # MSB dim indices for each wire (1-indexed, after batch dim)
    target_dims = [n - w for w in wires]  # e.g. wires=[0,1] for n=3 → [3,2]
    # Destination: last k positions
    dest_dims = list(range(n - k + 1, n + 1))  # e.g. [2, 3] for n=3, k=2
    # Move target dims to the end
    s = state
    for src, dst in zip(target_dims, dest_dims):
        s = s.movedim(src, dst)
    # Reshape to (batch, rest, 2^k)
    s = s.reshape(*batch_shape, -1, 2**k)
    # Apply gate: (2^k, 2^k) @ (batch, rest, 2^k, 1) → (batch, rest, 2^k)
    s = (mat @ s.unsqueeze(-1)).squeeze(-1)
    # Reshape back to (batch, ..., 2, 2, ..., 2)
    inner = [2] * n
    s = s.reshape(*batch_shape, *inner)
    # Move dims back to original positions (reverse the moves)
    for src, dst in zip(reversed(target_dims), reversed(dest_dims)):
        s = s.movedim(dst, src)
    return s


# ---- opcode execution (differentiable) -------------------------------------

def _resolve_params(idx: int, raw_params, param_map: dict, is_parametric: bool, dagger: bool):
    if idx in param_map:
        return param_map[idx]
    if not is_parametric or raw_params is None:
        return None
    if isinstance(raw_params, (list, tuple)):
        vals = [-v for v in raw_params] if dagger else list(raw_params)
    else:
        vals = [-raw_params] if dagger else [raw_params]
    return torch.tensor(vals, dtype=torch.float32)


def _execute_opcodes(
    opcode_list: list,
    param_map: dict,
    n_qubits: int,
) -> "torch.Tensor":
    state = torch.zeros([1] + [2] * n_qubits, dtype=torch.complex64)
    state[(0,) + (0,) * n_qubits] = 1.0 + 0j

    for idx, opcode in enumerate(opcode_list):
        op_name = opcode[0]
        raw_wires = opcode[1]
        raw_params = opcode[3]
        dagger = opcode[4]
        controls = opcode[5]

        wires = raw_wires if isinstance(raw_wires, list) else [raw_wires]
        all_wires = (list(controls) if controls else []) + wires
        n_w = len(all_wires)

        if op_name == "BARRIER":
            continue

        # --- non-parametric gates ---
        if op_name == "I":
            continue

        if n_w == 1:
            w = all_wires[0]
            MAT = {
                "H": _H, "X": _X, "Y": _Y, "Z": _Z,
                "S": _SDG if dagger else _S,
                "SX": _SXDG if dagger else _SX,
                "T": _TDG if dagger else _T,
            }
            if op_name in MAT:
                state = _apply_1q_gate(state, MAT[op_name], w)
                continue

        if n_w == 2:
            w0, w1 = all_wires
            if op_name == "CNOT":
                mat = _build_cnot_matrix(n_qubits, w0, w1)
                state = _apply_multiq_gate(state, mat, [w0, w1])
                continue
            if op_name == "CZ":
                mat = _build_cz_matrix(n_qubits, w0, w1)
                state = _apply_multiq_gate(state, mat, [w0, w1])
                continue
            if op_name == "SWAP":
                state = _apply_2q_gate(state, _SWAP, w0, w1)
                continue
            if op_name == "ISWAP":
                state = _apply_2q_gate(state, _ISWAP, w0, w1)
                continue

        if n_w == 3:
            if op_name == "TOFFOLI":
                mat = _build_toffoli_matrix(n_qubits, all_wires[0], all_wires[1], all_wires[2])
                state = _apply_multiq_gate(state, mat, all_wires)
                continue
            if op_name == "CSWAP":
                mat = _build_cswap_matrix(n_qubits, all_wires[0], all_wires[1], all_wires[2])
                state = _apply_multiq_gate(state, mat, all_wires)
                continue

        # --- parametric gates ---
        p = _resolve_params(idx, raw_params, param_map, True, dagger)
        if p is None:
            continue
        if p.dim() == 0:
            p = p.unsqueeze(0)

        if n_w == 1:
            w = all_wires[0]
            gate_fn = {"RX": _rx_matrix, "RY": _ry_matrix, "RZ": _rz_matrix, "U1": _u1_matrix}
            if op_name in gate_fn:
                state = _apply_1q_gate(state, gate_fn[op_name](p[0]), w)
                continue
            if op_name == "U2":
                state = _apply_1q_gate(state, _u3_matrix(torch.tensor(3.14159265 / 2), p[0], p[1]), w)
                continue
            if op_name == "U3":
                state = _apply_1q_gate(state, _u3_matrix(p[0], p[1], p[2]), w)
                continue

        if n_w == 2:
            w0, w1 = all_wires
            if op_name == "XX":
                state = _apply_2q_gate(state, _rxx_matrix(p[0]), w0, w1)
                continue
            if op_name == "YY":
                state = _apply_2q_gate(state, _ryy_matrix(p[0]), w0, w1)
                continue
            if op_name == "ZZ":
                state = _apply_2q_gate(state, _rzz_matrix(p[0]), w0, w1)
                continue

        raise NotImplementedError(
            f"Gate {op_name!r} with {n_w} qubit(s) is not supported in the virtual backend."
        )

    return state


# ---- expectation value from statevector ------------------------------------

# Pauli matrices for expectation (complex128 for einsum precision)
_I2d = torch.eye(2, dtype=torch.complex64)
_Xd = torch.tensor([[0, 1], [1, 0]], dtype=torch.complex64)
_Yd = torch.tensor([[0, -1j], [1j, 0]], dtype=torch.complex64)
_Zd = torch.tensor([[1, 0], [0, -1]], dtype=torch.complex64)

_PAULI_MAP = {"I": _I2d, "X": _Xd, "Y": _Yd, "Z": _Zd}


def _pauli_expval(state: "torch.Tensor", pauli_str: str) -> "torch.Tensor":
    """Compute ⟨ψ|P|ψ⟩ for a Pauli string from the state tensor.

    The *pauli_str* uses the physics convention: leftmost character = highest
    qubit index (MSB).  The state tensor also uses MSB layout, but uniqc
    opcodes use LSB (qubit 0 = rightmost).  We therefore reverse the string
    so that ``pauli_str[0]`` acts on the *rightmost* dimension (qubit 0).
    """
    psi = state.reshape(-1)  # (2^n,)
    rev = pauli_str[::-1]
    H = _PAULI_MAP[rev[0]]
    for ch in rev[1:]:
        H = torch.kron(H, _PAULI_MAP[ch])
    return (psi.conj() * (H @ psi)).sum().real
