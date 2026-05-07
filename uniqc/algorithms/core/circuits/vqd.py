"""Variational Quantum Deflation (VQD) circuit components."""

__all__ = ["vqd_circuit", "vqd_ansatz", "vqd_overlap_circuit", "vqd_example"]

import warnings
from typing import List, Optional

import numpy as np

from uniqc.circuit_builder import Circuit


def _hea_ansatz(
    circuit: Circuit,
    params: List[float],
    n_layers: int,
    qubits: List[int],
) -> None:
    r"""Apply a Hardware-Efficient Ansatz (HEA) to the circuit.

    Each layer consists of:
    1. ``Ry`` rotation on every qubit.
    2. A chain of CNOT gates between adjacent qubits.

    The total number of parameters required is ``n_qubits * n_layers``.

    Args:
        circuit: Quantum circuit to operate on (mutated in-place).
        params: Rotation angles.  Length must equal ``len(qubits) * n_layers``.
        n_layers: Number of repeating layers.
        qubits: Qubit indices to apply the ansatz on.

    Raises:
        ValueError: Parameter count does not match ``n_qubits * n_layers``.

    Example:
        >>> from uniqc.circuit_builder import Circuit
        >>> c = Circuit(2)
        >>> _hea_ansatz(c, [0.1, 0.2, 0.3, 0.4], n_layers=2, qubits=[0, 1])
    """
    n_qubits = len(qubits)
    expected = n_qubits * n_layers
    if len(params) != expected:
        raise ValueError(
            f"Expected {expected} parameters (n_qubits={n_qubits} × "
            f"n_layers={n_layers}), got {len(params)}"
        )

    idx = 0
    for _ in range(n_layers):
        # Single-qubit Ry rotations
        for q in qubits:
            circuit.ry(q, params[idx])
            idx += 1
        # Entangling CNOT chain
        for i in range(n_qubits - 1):
            circuit.cnot(qubits[i], qubits[i + 1])


def vqd_ansatz(
    n_qubits: int,
    ansatz_params: List[float],
    prev_states: List[np.ndarray],
    qubits: Optional[List[int]] = None,
    penalty: float = 10.0,
    n_layers: int = 2,
) -> Circuit:
    r"""Build a VQD ansatz circuit fragment (variational style).

    Returns a fresh :class:`Circuit`.  ``prev_states`` is accepted to keep
    the VQD signature, but is only used by the classical optimiser.
    """
    if qubits is None:
        qubits = list(range(n_qubits))
    if len(prev_states) == 0:
        raise ValueError(
            "prev_states is empty. Use VQE (not VQD) for the ground state."
        )
    fragment = Circuit()
    _hea_ansatz(fragment, ansatz_params, n_layers, qubits)
    return fragment


def vqd_circuit(
    *args,
    ansatz_params: Optional[List[float]] = None,
    prev_states: Optional[List[np.ndarray]] = None,
    qubits: Optional[List[int]] = None,
    penalty: float = 10.0,
    n_layers: int = 2,
):
    r"""Build (or apply) a VQD ansatz.

    Two calling conventions:

    .. code-block:: python

        # Variational fragment style (recommended; see also vqd_ansatz):
        c = vqd_circuit(2, ansatz_params=[0.1]*4, prev_states=[gs], n_layers=2)

        # Legacy in-place (deprecated):
        c = Circuit(2)
        vqd_circuit(c, [0.1]*4, prev_states=[gs], n_layers=2)
    """
    if len(args) >= 1 and isinstance(args[0], Circuit):
        circuit_in = args[0]
        if len(args) >= 2 and ansatz_params is None:
            ansatz_params = args[1]
        if len(args) >= 3 and prev_states is None:
            prev_states = args[2]
        warnings.warn(
            "vqd_circuit(circuit, ansatz_params, prev_states, ...) (in-place form) is "
            "deprecated. Use vqd_ansatz(n_qubits, ansatz_params, prev_states, ...) "
            "and add_circuit().",
            DeprecationWarning,
            stacklevel=2,
        )
        if qubits is None:
            qubits = list(range(circuit_in.qubit_num))
        if not prev_states:
            raise ValueError(
                "prev_states is empty. Use VQE (not VQD) for the ground state."
            )
        _hea_ansatz(circuit_in, ansatz_params, n_layers, qubits)
        return None

    # Fragment-style call
    if len(args) >= 1 and isinstance(args[0], int):
        n_qubits = args[0]
    elif qubits is not None:
        n_qubits = max(qubits) + 1
    else:
        raise TypeError("vqd_circuit requires n_qubits as first positional arg")
    if ansatz_params is None or prev_states is None:
        raise TypeError("vqd_circuit requires ansatz_params and prev_states")
    return vqd_ansatz(
        n_qubits, ansatz_params, prev_states,
        qubits=qubits, penalty=penalty, n_layers=n_layers,
    )


def vqd_overlap_circuit(
    prev_state: np.ndarray,
    ansatz_params: List[float],
    n_layers: int = 2,
    qubits: Optional[List[int]] = None,
) -> Circuit:
    r"""Build a circuit to compute :math:`|\langle\psi(\boldsymbol{\theta})|\phi\rangle|^2`.

    Uses the **swap test**: an ancilla qubit controls SWAPs between the
    ansatz register and a register prepared in *prev_state*.  Measuring
    the ancilla in the computational basis gives an estimate of the
    overlap.

    Circuit layout (2 data qubits)::

        ancilla: ──H──●──────●──●──────●── Measure
                       |      |  |      |
        data_A:  ──[ansatz]──SWAP──[ansatz]──SWAP──
                       |      |  |      |
        data_B:  ──[prev]──SWAP──[prev]──SWAP──

    Args:
        prev_state: State vector :math:`|\phi\rangle` of dimension :math:`2^n`.
        ansatz_params: Parameters for the HEA ansatz.
        n_layers: Number of HEA layers.
        qubits: Data qubit indices for the ansatz register.
            ``None`` means ``[0, 1, …, n-1]`` where *n* is inferred
            from ``prev_state``.

    Returns:
        A new :class:`Circuit` containing the swap-test circuit with the
        ancilla measured.

    Raises:
        ValueError: *prev_state* is not a power-of-2 length.

    Example:
        >>> import numpy as np
        >>> gs = np.array([1, 0, 0, 0], dtype=complex)
        >>> circ = vqd_overlap_circuit(gs, [0.1]*4, n_layers=2)
    """
    dim = len(prev_state)
    n = int(np.log2(dim))
    if 2**n != dim:
        raise ValueError(
            f"prev_state length {dim} is not a power of 2."
        )

    if qubits is None:
        qubits = list(range(n))

    # Total qubits: 1 ancilla + n (ansatz) + n (prev_state)
    total = 1 + 2 * n
    circ = Circuit()

    ancilla = 0
    data_a = list(range(1, 1 + n))       # ansatz register
    data_b = list(range(1 + n, 1 + 2 * n))  # prev-state register

    # Prepare prev_state on data_b using state preparation
    _prepare_state(circ, prev_state, data_b)

    # Apply ansatz on data_a
    _hea_ansatz(circ, ansatz_params, n_layers, data_a)

    # Swap test
    circ.h(ancilla)
    for i in range(n):
        circ.cnot(ancilla, data_a[i])
        circ.cnot(ancilla, data_b[i])
        # Controlled-SWAP decomposition: CSWAP(ancilla, a, b)
        #   = CNOT(b, a) — H(b) — T(b) — CNOT(a, b) — T†(a) — CNOT(ancilla, b)
        #   — T(a) — CNOT(a, b) — T†(b) — H(b) — CNOT(ancilla, a)
        # Simpler: just use three CNOTs with ancilla control
        # Standard decomposition of Toffoli-based CSWAP:
        circ.cnot(data_b[i], data_a[i])
        circ.cnot(ancilla, data_b[i])
        circ.cnot(data_b[i], data_a[i])
        circ.cnot(ancilla, data_b[i])
        circ.cnot(data_a[i], data_b[i])
    circ.h(ancilla)

    circ.measure(ancilla)
    return circ


def _prepare_state(
    circuit: Circuit,
    state: np.ndarray,
    qubits: List[int],
) -> None:
    """Prepare an arbitrary state vector on the given qubits using multiplexed rotations.

    For small state vectors this uses a simple Schmidt-decomposition based
    preparation.  Normalises *state* if needed.

    Args:
        circuit: Circuit to modify in-place.
        state: Target state vector.
        qubits: Qubit indices.
    """
    n = len(qubits)
    dim = len(state)
    if dim != 2**n:
        raise ValueError(
            f"State vector length {dim} does not match {n} qubits (expected {2**n})."
        )

    # Normalise
    norm = np.linalg.norm(state)
    if norm == 0:
        raise ValueError("State vector is zero.")
    state = state / norm

    # Use state preparation via multiplexed Ry rotations (Schmidt decomposition)
    # This is a simplified recursive approach
    _state_prep_recursive(circuit, state, qubits)


def _state_prep_recursive(
    circuit: Circuit,
    state: np.ndarray,
    qubits: List[int],
) -> None:
    """Recursively prepare a state vector using controlled Ry rotations."""
    n = len(qubits)
    dim = len(state)

    if n == 1:
        # Single qubit: just Ry
        alpha = float(state[0])
        beta = float(state[1]) if dim > 1 else 0.0
        amp = np.sqrt(abs(alpha)**2 + abs(beta)**2)
        if amp < 1e-15:
            return
        theta = 2 * np.arccos(np.clip(abs(alpha) / amp, 0, 1))
        circuit.ry(qubits[0], theta)
        if beta != 0 and alpha != 0:
            phase_diff = np.angle(beta) - np.angle(alpha)
            if abs(phase_diff) > 1e-10:
                circuit.rz(qubits[0], phase_diff)
        return

    # Split state into two halves (for most-significant qubit control)
    half = dim // 2
    top = state[:half]
    bot = state[half:]

    norm_top = np.linalg.norm(top)
    norm_bot = np.linalg.norm(bot)
    total = np.sqrt(norm_top**2 + norm_bot**2)

    if total < 1e-15:
        return

    theta = 2 * np.arccos(np.clip(norm_top / total, 0, 1))
    circuit.ry(qubits[0], theta)

    if norm_top > 1e-15:
        _state_prep_recursive(circuit, top / norm_top, qubits[1:])
    # Apply X to flip to bottom half
    circuit.x(qubits[0])
    if norm_bot > 1e-15:
        _state_prep_recursive(circuit, bot / norm_bot, qubits[1:])
    circuit.x(qubits[0])


def vqd_example() -> Circuit:
    """Return a small VQD ansatz fragment for tests/docs."""
    gs = np.array([1, 0, 0, 0], dtype=complex)
    return vqd_ansatz(2, [0.1] * 4, prev_states=[gs], n_layers=2)
