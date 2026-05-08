"""Matrix utilities for :mod:`uniqc.circuit_builder` circuits."""

from __future__ import annotations

__all__ = ["NotMatrixableError", "get_matrix"]

import math
from collections.abc import Sequence

import numpy as np

from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.exceptions import NotMatrixableError  # noqa: F401 — re-export


_I = np.eye(2, dtype=np.complex128)
_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_H = np.array([[1, 1], [1, -1]], dtype=np.complex128) / math.sqrt(2)
_S = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
_T = np.array([[1, 0], [0, np.exp(1j * math.pi / 4)]], dtype=np.complex128)
_SX = np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=np.complex128) / 2


def _as_qubit_list(qubits: int | Sequence[int] | None) -> list[int]:
    if qubits is None:
        return []
    if isinstance(qubits, int):
        return [qubits]
    return [int(q) for q in qubits]


def _as_param_list(params: float | Sequence[float] | None) -> list[float]:
    if params is None:
        return []
    if isinstance(params, (list, tuple)):
        return [float(p) for p in params]
    return [float(params)]


def _single_param(params: float | Sequence[float] | None, default: float = 0.0) -> float:
    values = _as_param_list(params)
    return values[0] if values else default


def _rx(theta: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=np.complex128)


def _ry(theta: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=np.complex128)


def _rz(theta: float) -> np.ndarray:
    return np.array(
        [[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]],
        dtype=np.complex128,
    )


def _u1(lam: float) -> np.ndarray:
    return np.array([[1, 0], [0, np.exp(1j * lam)]], dtype=np.complex128)


def _u2(phi: float, lam: float) -> np.ndarray:
    return _u3(math.pi / 2, phi, lam)


def _u3(theta: float, phi: float, lam: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array(
        [
            [c, -np.exp(1j * lam) * s],
            [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c],
        ],
        dtype=np.complex128,
    )


def _rphi(theta: float, phi: float) -> np.ndarray:
    return _rz(phi) @ _rx(theta) @ _rz(-phi)


def _swap_matrix() -> np.ndarray:
    matrix = np.zeros((4, 4), dtype=np.complex128)
    for col in range(4):
        b0 = col & 1
        b1 = (col >> 1) & 1
        row = b1 | (b0 << 1)
        matrix[row, col] = 1
    return matrix


def _controlled_matrix(base: np.ndarray, n_controls: int) -> np.ndarray:
    n_targets = int(round(math.log2(base.shape[0])))
    dim = 2 ** (n_controls + n_targets)
    target_mask = (1 << n_targets) - 1
    control_mask = (1 << n_controls) - 1
    matrix = np.eye(dim, dtype=np.complex128)

    for col in range(dim):
        if (col & control_mask) != control_mask:
            continue
        matrix[col, col] = 0
        target_col = (col >> n_controls) & target_mask
        controls = col & control_mask
        for target_row in range(2**n_targets):
            row = controls | (target_row << n_controls)
            matrix[row, col] = base[target_row, target_col]

    return matrix


def _xx(theta: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return c * np.eye(4, dtype=np.complex128) - 1j * s * np.kron(_X, _X)


def _yy(theta: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return c * np.eye(4, dtype=np.complex128) - 1j * s * np.kron(_Y, _Y)


def _zz(theta: float) -> np.ndarray:
    return np.diag(
        [
            np.exp(-1j * theta / 2),
            np.exp(1j * theta / 2),
            np.exp(1j * theta / 2),
            np.exp(-1j * theta / 2),
        ]
    ).astype(np.complex128)


def _phase2q(theta1: float, theta2: float, thetazz: float) -> np.ndarray:
    return np.diag(
        [
            1,
            np.exp(1j * theta1),
            np.exp(1j * theta2),
            np.exp(1j * (theta1 + theta2 + thetazz)),
        ]
    ).astype(np.complex128)


def _xy(theta: float) -> np.ndarray:
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array(
        [[1, 0, 0, 0], [0, c, 1j * s, 0], [0, 1j * s, c, 0], [0, 0, 0, 1]],
        dtype=np.complex128,
    )


def _iswap() -> np.ndarray:
    return np.array(
        [[1, 0, 0, 0], [0, 0, 1j, 0], [0, 1j, 0, 0], [0, 0, 0, 1]],
        dtype=np.complex128,
    )


def _ecr() -> np.ndarray:
    return np.array(
        [[0, 0, 1, 1j], [0, 0, 1j, 1], [1, -1j, 0, 0], [-1j, 1, 0, 0]],
        dtype=np.complex128,
    ) / math.sqrt(2)


def _base_gate_matrix(
    name: str,
    qubits: int | list[int],
    params: float | list[float] | tuple[float, ...] | None,
) -> np.ndarray:
    values = _as_param_list(params)

    if isinstance(qubits, int):
        if name == "I":
            return _I.copy()
        if name == "X":
            return _X.copy()
        if name == "Y":
            return _Y.copy()
        if name == "Z":
            return _Z.copy()
        if name == "H":
            return _H.copy()
        if name == "S":
            return _S.copy()
        if name == "T":
            return _T.copy()
        if name == "SX":
            return _SX.copy()
        if name == "RX":
            return _rx(_single_param(params))
        if name == "RY":
            return _ry(_single_param(params))
        if name == "RZ":
            return _rz(_single_param(params))
        if name == "U1":
            return _u1(_single_param(params))
        if name == "U2":
            return _u2(values[0], values[1])
        if name == "U3":
            return _u3(values[0], values[1], values[2])
        if name == "RPhi90":
            return _rphi(math.pi / 2, _single_param(params))
        if name == "RPhi180":
            return _rphi(math.pi, _single_param(params))
        if name == "RPhi":
            return _rphi(values[0], values[1])
        raise NotImplementedError(f"Unsupported 1-qubit gate: {name!r}")

    if len(qubits) == 2:
        if name == "CNOT":
            return _controlled_matrix(_X, 1)
        if name == "CZ":
            return _controlled_matrix(_Z, 1)
        if name == "SWAP":
            return _swap_matrix()
        if name == "ISWAP":
            return _iswap()
        if name == "ECR":
            return _ecr()
        if name == "XX":
            return _xx(_single_param(params))
        if name == "YY":
            return _yy(_single_param(params))
        if name == "ZZ":
            return _zz(_single_param(params))
        if name == "XY":
            return _xy(_single_param(params))
        if name == "PHASE2Q":
            return _phase2q(values[0], values[1], values[2])
        raise NotImplementedError(f"Unsupported 2-qubit gate: {name!r}")

    if len(qubits) == 3:
        if name == "TOFFOLI":
            return _controlled_matrix(_X, 2)
        if name == "CSWAP":
            return _controlled_matrix(_swap_matrix(), 1)
        raise NotImplementedError(f"Unsupported 3-qubit gate: {name!r}")

    raise NotImplementedError(f"Unsupported gate width for {name!r}: {len(qubits)}")


def _opcode_matrix(
    name: str,
    qubits: int | list[int],
    params: float | list[float] | tuple[float, ...] | None,
    dagger: bool,
    controls: int | list[int] | None,
) -> tuple[np.ndarray, list[int]]:
    target_qubits = _as_qubit_list(qubits)
    control_qubits = _as_qubit_list(controls)
    if set(target_qubits) & set(control_qubits):
        raise ValueError(f"Gate {name!r} has overlapping target and control qubits")

    base = _base_gate_matrix(name, qubits, params)
    if dagger:
        base = base.conj().T
    if control_qubits:
        base = _controlled_matrix(base, len(control_qubits))
    return base, control_qubits + target_qubits


def _embed_gate(gate: np.ndarray, qubits: list[int], n_total: int) -> np.ndarray:
    """Embed a local gate into the full LSQ-first Hilbert space.

    The local gate index order follows ``qubits``: bit 0 of the local basis
    index corresponds to ``qubits[0]``.  ``np.einsum`` performs the actual
    tensor contraction after the local matrix axes are permuted into the full
    circuit tensor layout.
    """
    if len(set(qubits)) != len(qubits):
        raise ValueError(f"Duplicate qubits in gate application: {qubits}")

    n_gate = len(qubits)
    dim = 2**n_total
    gate_tensor = gate.reshape((2,) * (2 * n_gate), order="F")
    identity_tensor = np.eye(dim, dtype=np.complex128).reshape((2,) * n_total + (dim,), order="F")
    output_labels = list(range(n_total))
    input_labels = list(range(n_total, n_total + n_gate))
    column_label = n_total + n_gate
    gate_output_labels = [output_labels[q] for q in qubits]
    identity_labels = output_labels.copy()

    for local_index, q in enumerate(qubits):
        identity_labels[q] = input_labels[local_index]

    embedded_tensor = np.einsum(
        gate_tensor,
        gate_output_labels + input_labels,
        identity_tensor,
        identity_labels + [column_label],
        output_labels + [column_label],
    )
    return embedded_tensor.reshape((dim, dim), order="F")


def _matrix_qubit_count(circuit: Circuit) -> int:
    max_qubit = circuit.qubit_num - 1
    for name, qubits, _cbits, _params, _dagger, controls in circuit.opcode_list:
        if name in {"QINIT", "CREG"}:
            continue
        all_qubits = _as_qubit_list(qubits) + _as_qubit_list(controls)
        if all_qubits:
            max_qubit = max(max_qubit, max(all_qubits))
    return max_qubit + 1


def get_matrix(circuit: Circuit) -> np.ndarray:
    """Return the full unitary matrix for ``circuit``.

    Qubit 0 is treated as the least-significant bit of the statevector index.
    The returned matrix uses the standard convention ``state_out = U @
    state_in`` and gates are applied in the same order as ``opcode_list``.
    """
    if circuit.measure_list:
        raise NotMatrixableError("Measured circuits have no unitary matrix")

    n_qubits = _matrix_qubit_count(circuit)
    dim = 2**n_qubits
    unitary = np.eye(dim, dtype=np.complex128)

    for opcode in circuit.opcode_list:
        name, qubits, _cbits, params, dagger, controls = opcode
        if name in {"BARRIER"}:
            continue
        if name in {"MEASURE", "QINIT", "CREG", "CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER"}:
            raise NotMatrixableError(f"Opcode {name!r} has no unitary matrix")

        gate, gate_qubits = _opcode_matrix(name, qubits, params, bool(dagger), controls)
        embedded = _embed_gate(gate, gate_qubits, n_qubits)
        unitary = embedded @ unitary

    return unitary
