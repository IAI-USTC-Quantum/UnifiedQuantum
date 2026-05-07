"""Grover oracle and diffusion operator construction.

Provides reusable building blocks for Grover's quantum search algorithm:

* :func:`grover_oracle` — phase-flip oracle for a marked computational basis state.
* :func:`grover_diffusion` — Grover diffusion (amplitude amplification) operator.

Both functions operate on a :class:`~uniqc.circuit_builder.Circuit` object
passed in by the caller, following the standard circuit-building convention of
``uniqc.algorithms.core.circuits``.

References:
    Grover, L. K. (1996). "A fast quantum mechanical algorithm for database
    search." STOC '96.  https://arxiv.org/abs/quant-ph/9605043
"""

__all__ = ["grover_oracle", "grover_diffusion", "grover_oracle_example"]

import warnings
from typing import List, Optional

from uniqc.circuit_builder import Circuit


def _apply_mcz(
    circuit: Circuit,
    controls: List[int],
    target: int,
) -> None:
    """Apply a multi-controlled Z gate.

    Flips the phase of the computational basis state where every control
    qubit and the target qubit are all in :math:`|1\\rangle`.

    Args:
        circuit: Circuit to append gates to (mutated in-place).
        controls: List of control qubit indices.
        target: Target qubit index.
    """
    n = len(controls)
    if n == 0:
        circuit.z(target)
        return
    if n == 1:
        circuit.cz(controls[0], target)
        return

    # For n>=2, realize MCZ as H·MCX·H on the target.
    circuit.h(target)
    _apply_mcx(circuit, controls, target)
    circuit.h(target)


def _apply_mcx(
    circuit: Circuit,
    controls: List[int],
    target: int,
) -> None:
    """Apply a multi-controlled X gate for any number of controls.

    For n ≤ 3 uses native circuit gates (x / cnot / toffoli / c3x).
    For n ≥ 4 uses a clean-ancilla Toffoli ladder: ``n - 2`` workspace qubits
    are allocated automatically above the highest qubit index currently in the
    circuit.  They are initialised to |0⟩ (circuit convention) and restored to
    |0⟩ after the gate.

    Args:
        circuit: Circuit to append gates to (mutated in-place).
        controls: Ordered list of control qubit indices.
        target: Target qubit index.
    """
    n = len(controls)
    if n == 0:
        circuit.x(target)
        return
    if n == 1:
        circuit.cnot(controls[0], target)
        return
    if n == 2:
        circuit.toffoli(controls[0], controls[1], target)
        return
    if n == 3:
        circuit.add_gate("X", target, control_qubits=list(controls))
        return

    # n >= 4: clean-ancilla Toffoli ladder.
    # Workspace qubits are placed just above the highest index in use so they
    # are always freshly |0⟩ and do not collide with data / ancilla qubits.
    n_workspace = n - 2
    workspace_start = max(list(controls) + [target]) + 1
    workspace = list(range(workspace_start, workspace_start + n_workspace))

    # Declare workspace qubits in the circuit (idempotent if already registered).
    for q in workspace:
        circuit.record_qubit(q)

    # Forward ladder: compute AND(controls[0..n-3]) into workspace.
    circuit.toffoli(controls[0], controls[1], workspace[0])
    for i in range(1, n_workspace):
        circuit.toffoli(controls[i + 1], workspace[i - 1], workspace[i])
    # Apply MCX to target.
    circuit.toffoli(controls[-1], workspace[-1], target)
    # Uncompute workspace.
    for i in range(n_workspace - 1, 0, -1):
        circuit.toffoli(controls[i + 1], workspace[i - 1], workspace[i])
    circuit.toffoli(controls[0], controls[1], workspace[0])


def _build_grover_oracle_fragment(
    marked_state: int,
    n_qubits: Optional[int] = None,
    qubits: Optional[List[int]] = None,
    ancilla: Optional[int] = None,
) -> Circuit:
    """Internal builder: returns a fresh Grover oracle Circuit."""
    if marked_state < 0:
        raise ValueError(f"marked_state must be non-negative, got {marked_state}")

    n_bits = max(1, marked_state.bit_length())
    if qubits is None:
        n = n_qubits if n_qubits is not None else n_bits
        qubits = list(range(n))
    n = len(qubits)

    if marked_state >= (1 << n):
        raise ValueError(
            f"marked_state {marked_state} requires {marked_state.bit_length()} "
            f"bits but only {n} qubits were provided"
        )

    if ancilla is None:
        ancilla = max(qubits) + 1

    fragment = Circuit()
    fragment.x(ancilla)
    fragment.h(ancilla)

    marked_bits = [(marked_state >> i) & 1 for i in range(n)]
    for i, bit in enumerate(marked_bits):
        if bit == 0:
            fragment.x(qubits[i])

    _apply_mcx(fragment, qubits, ancilla)

    for i, bit in enumerate(marked_bits):
        if bit == 0:
            fragment.x(qubits[i])

    fragment.h(ancilla)
    fragment.x(ancilla)
    return fragment


def grover_oracle(
    *args,
    marked_state: Optional[int] = None,
    qubits: Optional[List[int]] = None,
    ancilla: Optional[int] = None,
    n_qubits: Optional[int] = None,
):
    r"""Construct a phase-flip oracle for a marked basis state.

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        oracle = grover_oracle(marked_state=5, qubits=[0, 1, 2])  # -> Circuit

        # Legacy in-place (deprecated):
        c = Circuit()
        anc = grover_oracle(c, marked_state=5, qubits=[0, 1, 2])  # mutates, returns ancilla idx

    See module docstring for the algorithm.
    """
    # Fragment-style entry: positional int marked_state OR no positional + kw
    if len(args) == 0 or (len(args) >= 1 and isinstance(args[0], int)):
        if len(args) >= 1:
            marked_state = args[0]
        if marked_state is None:
            raise TypeError("grover_oracle requires marked_state")
        return _build_grover_oracle_fragment(
            marked_state, n_qubits=n_qubits, qubits=qubits, ancilla=ancilla
        )

    # Legacy in-place: first arg is a Circuit
    circuit_in = args[0]
    if not isinstance(circuit_in, Circuit):
        raise TypeError(
            "grover_oracle: first positional arg must be int (marked_state) "
            "or Circuit (deprecated in-place form)"
        )
    if len(args) >= 2 and marked_state is None:
        marked_state = args[1]
    if marked_state is None:
        raise TypeError("grover_oracle requires marked_state")
    warnings.warn(
        "grover_oracle(circuit, marked_state, ...) (in-place form) is deprecated. "
        "Use grover_oracle(marked_state, qubits=...) and add_circuit().",
        DeprecationWarning,
        stacklevel=2,
    )
    fragment = _build_grover_oracle_fragment(
        marked_state, n_qubits=n_qubits, qubits=qubits, ancilla=ancilla
    )
    circuit_in.add_circuit(fragment)
    # Return ancilla index for backward-compat
    if qubits is None:
        n_bits = max(1, marked_state.bit_length())
        qubits = list(range(n_bits))
    if ancilla is None:
        ancilla = max(qubits) + 1
    return ancilla


def _build_grover_diffusion_fragment(
    qubits: Optional[List[int]] = None,
    n_qubits: Optional[int] = None,
) -> Circuit:
    if qubits is None:
        qubits = list(range(n_qubits if n_qubits is not None else 2))
    n = len(qubits)
    if n < 1:
        raise ValueError("At least 1 qubit is required")

    fragment = Circuit()
    for q in qubits:
        fragment.h(q)
    for q in qubits:
        fragment.x(q)
    if n == 1:
        fragment.z(qubits[0])
    else:
        _apply_mcz(fragment, qubits[:-1], qubits[-1])
    for q in qubits:
        fragment.x(q)
    for q in qubits:
        fragment.h(q)
    return fragment


def grover_diffusion(
    *args,
    qubits: Optional[List[int]] = None,
    ancilla: Optional[int] = None,
    n_qubits: Optional[int] = None,
):
    r"""Grover diffusion (amplitude amplification) operator.

    Two calling conventions:

    .. code-block:: python

        # Fragment style (recommended):
        diff = grover_diffusion(qubits=[0, 1, 2])     # -> Circuit
        diff = grover_diffusion(3)                    # n_qubits positional

        # Legacy in-place (deprecated):
        c = Circuit()
        grover_diffusion(c, qubits=[0, 1, 2])
    """
    if ancilla is not None:
        warnings.warn(
            "The 'ancilla' argument of grover_diffusion() is unused and will be "
            "removed in a future release.  Remove it from your call site.",
            DeprecationWarning,
            stacklevel=2,
        )
    if len(args) == 0:
        return _build_grover_diffusion_fragment(qubits=qubits, n_qubits=n_qubits)
    first = args[0]
    if isinstance(first, int):
        return _build_grover_diffusion_fragment(qubits=qubits, n_qubits=first)
    if isinstance(first, Circuit):
        warnings.warn(
            "grover_diffusion(circuit, ...) (in-place form) is deprecated. "
            "Use grover_diffusion(qubits=...) and add_circuit().",
            DeprecationWarning,
            stacklevel=2,
        )
        fragment = _build_grover_diffusion_fragment(qubits=qubits, n_qubits=n_qubits)
        first.add_circuit(fragment)
        return None
    raise TypeError(
        "grover_diffusion: first positional arg must be int (n_qubits) "
        "or Circuit (deprecated in-place form)"
    )


def grover_oracle_example() -> Circuit:
    """Return a 3-qubit Grover oracle marking state |5⟩ for tests/docs."""
    return grover_oracle(marked_state=5, qubits=[0, 1, 2])
