"""Deutsch-Jozsa algorithm circuit and oracle builder.

The oracular convention here (per :doc:`/guide/algorithm_design`) is:

- :func:`deutsch_jozsa_oracle` returns a fresh ``Circuit`` (the oracle).
- :func:`deutsch_jozsa_circuit` accepts a *quantum-circuit* oracle as its
  argument and returns a fresh full-DJ ``Circuit`` (fragment style).

A legacy in-place form ``deutsch_jozsa_circuit(circuit, oracle, qubits)`` is
preserved as a deprecated dispatch and emits :class:`DeprecationWarning`.
"""

__all__ = ["deutsch_jozsa_circuit", "deutsch_jozsa_oracle", "deutsch_jozsa_example"]

import warnings
from typing import List, Optional

from uniqc.circuit_builder import Circuit


def deutsch_jozsa_oracle(
    qubits: List[int],
    balanced: bool = True,
    target_bits: Optional[List[int]] = None,
) -> Circuit:
    r"""Build a Deutsch-Jozsa oracle circuit.

    See module docstring; behaviour is unchanged from previous releases —
    this is already a fragment-style API (returns a fresh ``Circuit``).

    Args:
        qubits: Data-qubit indices (explicit list, no default).
        balanced: If ``True``, build a balanced oracle; otherwise constant.
        target_bits: Data-qubit indices (positions within *qubits*) that
            control the ancilla flip.  Only used when *balanced* is ``True``.
            ``None`` means all data qubits.

    Returns:
        A new :class:`Circuit` containing the oracle gates.
    """
    if not isinstance(qubits, list):
        raise TypeError("qubits must be a list of qubit indices")
    if len(qubits) < 1:
        raise ValueError("qubits must contain at least 1 data qubit")

    n_qubits = len(qubits)
    ancilla = max(qubits) + 1

    oracle = Circuit()

    if not balanced:
        return oracle

    if target_bits is None:
        target_bits = list(range(n_qubits))

    for idx in target_bits:
        if idx < 0 or idx >= n_qubits:
            raise ValueError(
                f"target_bit {idx} out of range for {n_qubits} data qubits"
            )
        oracle.cnot(qubits[idx], ancilla)

    return oracle


def _build_dj_fragment(
    *,
    oracle: Circuit,
    qubits: List[int],
    ancilla: Optional[int] = None,
) -> Circuit:
    if not isinstance(qubits, list):
        raise TypeError("qubits must be a list of qubit indices")
    if len(qubits) < 1:
        raise ValueError("qubits must contain at least 1 data qubit")

    n_data = len(qubits)
    if ancilla is None:
        ancilla = max(qubits) + 1
    if oracle.qubit_num > 0 and oracle.qubit_num != n_data + 1:
        raise ValueError(
            f"Oracle acts on {oracle.qubit_num} qubits, "
            f"expected {n_data + 1} (data + ancilla)"
        )

    fragment = Circuit()
    for q in qubits:
        fragment.h(q)
    fragment.x(ancilla)
    fragment.h(ancilla)
    fragment.add_circuit(oracle)
    for q in qubits:
        fragment.h(q)
    fragment.measure(*qubits)
    return fragment


def deutsch_jozsa_circuit(
    *args,
    qubits: Optional[List[int]] = None,
    ancilla: Optional[int] = None,
    oracle: Optional[Circuit] = None,
):
    r"""Build (or apply) the Deutsch-Jozsa algorithm circuit.

    Two calling conventions are supported:

    .. code-block:: python

        # Fragment style (recommended):
        ora = deutsch_jozsa_oracle(qubits=[0, 1, 2], balanced=True)
        circuit = deutsch_jozsa_circuit(ora, qubits=[0, 1, 2])      # returns Circuit

        # Legacy in-place style (deprecated):
        c = Circuit()
        deutsch_jozsa_circuit(c, ora, qubits=[0, 1, 2], ancilla=3)  # mutates c

    Args:
        *args: Either ``(oracle: Circuit, ...)`` (fragment) or
            ``(circuit: Circuit, oracle: Circuit, ...)`` (deprecated in-place).
        qubits: Data-qubit indices.
        ancilla: Ancilla qubit index. ``None`` means ``max(qubits) + 1``.
        oracle: The oracle ``Circuit`` (positional or keyword).

    Returns:
        A fresh :class:`Circuit` in fragment mode; ``None`` in legacy mode.
    """
    # Resolve dispatch
    if len(args) == 0:
        if oracle is None:
            raise TypeError("deutsch_jozsa_circuit requires an oracle Circuit argument")
        return _build_dj_fragment(oracle=oracle, qubits=qubits, ancilla=ancilla)

    if len(args) == 1:
        first = args[0]
        # Fragment style: first arg IS the oracle
        if oracle is None:
            return _build_dj_fragment(oracle=first, qubits=qubits, ancilla=ancilla)
        # Legacy: first arg is the in-place circuit
        warnings.warn(
            "deutsch_jozsa_circuit(circuit, oracle=...) (in-place form) is deprecated. "
            "Use deutsch_jozsa_circuit(oracle, qubits=...) and add_circuit().",
            DeprecationWarning,
            stacklevel=2,
        )
        fragment = _build_dj_fragment(oracle=oracle, qubits=qubits, ancilla=ancilla)
        first.add_circuit(fragment)
        return None

    if len(args) >= 2:
        # Legacy positional: (circuit, oracle, qubits=..., ancilla=...)
        circuit_in, ora = args[0], args[1]
        warnings.warn(
            "deutsch_jozsa_circuit(circuit, oracle, ...) (in-place form) is deprecated. "
            "Use deutsch_jozsa_circuit(oracle, qubits=...) and add_circuit().",
            DeprecationWarning,
            stacklevel=2,
        )
        fragment = _build_dj_fragment(oracle=ora, qubits=qubits, ancilla=ancilla)
        circuit_in.add_circuit(fragment)
        return None


def deutsch_jozsa_example() -> Circuit:
    """Return a 3-qubit balanced-DJ algorithm circuit for tests/docs."""
    ora = deutsch_jozsa_oracle(qubits=[0, 1, 2], balanced=True)
    return deutsch_jozsa_circuit(ora, qubits=[0, 1, 2])
