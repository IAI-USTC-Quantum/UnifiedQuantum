"""Variational Quantum Deflation (VQD) circuit components."""

__all__ = ["vqd_circuit", "vqd_ansatz", "vqd_overlap_circuit", "vqd_example"]

import numpy as np

from uniqc._error_hints import format_enriched_message
from uniqc.algorithms.core.state_preparation import rotation_prepare
from uniqc.circuit_builder import Circuit


def _hea_ansatz(
    circuit: Circuit,
    params: list[float],
    n_layers: int,
    qubits: list[int],
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
            format_enriched_message(
                f"Expected {expected} parameters (n_qubits={n_qubits} × n_layers={n_layers}), got {len(params)}",
                "circuit_validation",
            )
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
    ansatz_params: list[float],
    prev_states: list[np.ndarray],
    qubits: list[int] | None = None,
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
            format_enriched_message(
                "prev_states is empty. Use VQE (not VQD) for the ground state.", "circuit_validation"
            )
        )
    fragment = Circuit()
    _hea_ansatz(fragment, ansatz_params, n_layers, qubits)
    return fragment


def vqd_circuit(
    *args,
    ansatz_params: list[float] | None = None,
    prev_states: list[np.ndarray] | None = None,
    qubits: list[int] | None = None,
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
        from uniqc._deprecation import warn_removed_in_0_1_0

        warn_removed_in_0_1_0(
            "vqd_circuit(circuit, ansatz_params, prev_states, ...) (in-place form)",
            replacement="vqd_ansatz(n_qubits, ansatz_params, prev_states, ...) with add_circuit()",
            stacklevel=2,
        )
        if qubits is None:
            qubits = list(range(circuit_in.qubit_num))
        if not prev_states:
            raise ValueError(
                format_enriched_message(
                    "prev_states is empty. Use VQE (not VQD) for the ground state.", "circuit_validation"
                )
            )
        _hea_ansatz(circuit_in, ansatz_params, n_layers, qubits)
        return None

    # Fragment-style call
    if len(args) >= 1 and isinstance(args[0], int):
        n_qubits = args[0]
    elif qubits is not None:
        n_qubits = max(qubits) + 1
    else:
        raise TypeError(
            format_enriched_message("vqd_circuit requires n_qubits as first positional arg", "circuit_validation")
        )
    if ansatz_params is None or prev_states is None:
        raise TypeError(
            format_enriched_message("vqd_circuit requires ansatz_params and prev_states", "circuit_validation")
        )
    return vqd_ansatz(
        n_qubits,
        ansatz_params,
        prev_states,
        qubits=qubits,
        penalty=penalty,
        n_layers=n_layers,
    )


def vqd_overlap_circuit(
    prev_state: np.ndarray,
    ansatz_params: list[float],
    n_layers: int = 2,
    qubits: list[int] | None = None,
) -> Circuit:
    r"""Build a circuit to compute :math:`|\langle\psi(\boldsymbol{\theta})|\phi\rangle|^2`.

    Uses the **swap test**: an ancilla qubit controls SWAPs between the
    ansatz register and a register prepared in *prev_state*.  Measuring
    the ancilla in the computational basis gives an estimate of the
    overlap.

    ``qubits`` names the ansatz register exactly. The ancilla and previous-state
    register are allocated from the lowest unused non-negative indices.

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
        raise ValueError(format_enriched_message(f"prev_state length {dim} is not a power of 2.", "circuit_validation"))

    data_a = list(range(n)) if qubits is None else [int(qubit) for qubit in qubits]
    if len(data_a) != n:
        raise ValueError(
            format_enriched_message(
                f"Expected {n} ansatz qubits, got {len(data_a)}",
                "circuit_validation",
            )
        )
    if len(set(data_a)) != len(data_a) or any(qubit < 0 for qubit in data_a):
        raise ValueError(
            format_enriched_message(
                "qubits must contain distinct non-negative indices",
                "circuit_validation",
            )
        )

    used = set(data_a)
    available = (qubit for qubit in range(max(data_a, default=-1) + 2 * n + 2) if qubit not in used)
    ancilla = next(available)
    data_b = [next(available) for _ in range(n)]
    circ = Circuit(max([ancilla, *data_a, *data_b], default=-1) + 1)

    # Prepare prev_state on data_b using state preparation
    rotation_prepare(circ, prev_state, data_b)

    # Apply ansatz on data_a
    _hea_ansatz(circ, ansatz_params, n_layers, data_a)

    # Swap test
    circ.h(ancilla)
    for ansatz_qubit, previous_qubit in zip(data_a, data_b, strict=True):
        circ.cswap(ancilla, ansatz_qubit, previous_qubit)
    circ.h(ancilla)

    circ.measure(ancilla)
    return circ


def vqd_example() -> Circuit:
    """Return a small VQD ansatz fragment for tests/docs."""
    gs = np.array([1, 0, 0, 0], dtype=complex)
    return vqd_ansatz(2, [0.1] * 4, prev_states=[gs], n_layers=2)
