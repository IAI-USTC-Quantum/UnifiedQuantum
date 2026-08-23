"""Deutsch-Jozsa algorithm circuit and oracle builder.

The oracular convention here (per the design notes in the project README) is:

- :func:`deutsch_jozsa_oracle` returns a fresh ``Circuit`` (the oracle).
- :func:`deutsch_jozsa_circuit` accepts a *quantum-circuit* oracle as its
  argument and returns a fresh full-DJ ``Circuit`` (fragment style).
"""

__all__ = ["deutsch_jozsa_circuit", "deutsch_jozsa_oracle", "deutsch_jozsa_example"]

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit


def deutsch_jozsa_oracle(
    qubits: list[int],
    balanced: bool = True,
    target_bits: list[int] | None = None,
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
        raise TypeError(format_enriched_message("qubits must be a list of qubit indices", "circuit_validation"))
    if len(qubits) < 1:
        raise ValueError(format_enriched_message("qubits must contain at least 1 data qubit", "circuit_validation"))

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
                format_enriched_message(
                    f"target_bit {idx} out of range for {n_qubits} data qubits", "circuit_validation"
                )
            )
        oracle.cnot(qubits[idx], ancilla)

    return oracle


def _build_dj_fragment(
    *,
    oracle: Circuit,
    qubits: list[int],
    ancilla: int | None = None,
) -> Circuit:
    if not isinstance(qubits, list):
        raise TypeError(format_enriched_message("qubits must be a list of qubit indices", "circuit_validation"))
    if len(qubits) < 1:
        raise ValueError(format_enriched_message("qubits must contain at least 1 data qubit", "circuit_validation"))

    n_data = len(qubits)
    if ancilla is None:
        ancilla = max(qubits) + 1
    if oracle.qubit_num > 0 and oracle.qubit_num != n_data + 1:
        raise ValueError(
            format_enriched_message(
                f"Oracle acts on {oracle.qubit_num} qubits, expected {n_data + 1} (data + ancilla)",
                "circuit_validation",
            )
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
    oracle: Circuit | None = None,
    *,
    qubits: list[int] | None = None,
    ancilla: int | None = None,
) -> Circuit:
    r"""Build the Deutsch-Jozsa algorithm circuit fragment.

    .. code-block:: python

        ora = deutsch_jozsa_oracle(qubits=[0, 1, 2], balanced=True)
        circuit = deutsch_jozsa_circuit(ora, qubits=[0, 1, 2])      # returns Circuit

    Args:
        oracle: The oracle ``Circuit`` (positional or keyword).
        qubits: Data-qubit indices.
        ancilla: Ancilla qubit index. ``None`` means ``max(qubits) + 1``.

    Returns:
        A fresh :class:`Circuit` containing the full DJ circuit.
    """
    if oracle is None:
        raise TypeError(
            format_enriched_message("deutsch_jozsa_circuit requires an oracle Circuit argument", "circuit_validation")
        )
    return _build_dj_fragment(oracle=oracle, qubits=qubits, ancilla=ancilla)


def deutsch_jozsa_example() -> Circuit:
    """Return a 3-qubit balanced-DJ algorithm circuit for tests/docs."""
    ora = deutsch_jozsa_oracle(qubits=[0, 1, 2], balanced=True)
    return deutsch_jozsa_circuit(ora, qubits=[0, 1, 2])
