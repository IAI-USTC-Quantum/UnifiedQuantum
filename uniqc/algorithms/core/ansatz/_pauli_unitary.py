"""Shared Pauli string parsing and cost unitary application.

Extracted from qaoa_ansatz.py for reuse in HVA and other algorithms.
"""

from __future__ import annotations

import numpy as np

from uniqc.circuit_builder import Circuit

__all__ = ["_parse_pauli_string", "_apply_cost_unitary"]


def _parse_pauli_string(pauli_string: str) -> list[tuple[str, int]]:
    """Parse a Pauli string into [(op, qubit), ...].

    Supports two formats:

    * **Indexed** (``'Z0Z1'``, ``'X0Y1Z2'``) — operator-digit pairs; qubits
      not listed are identity.
    * **Compact** (``'IX'``, ``'ZZ'``, ``'XYZ'``) — one character per qubit
      in left-to-right order; ``position`` == ``qubit index``.
    """
    # Indexed format: contains digits (e.g. "Z0Z1", "X0Y2")
    if any(ch.isdigit() for ch in pauli_string):
        terms: list[tuple[str, int]] = []
        current_op: str | None = None
        current_idx = ""
        for ch in pauli_string:
            if ch in "XYZI":
                if current_op is not None:
                    terms.append((current_op, int(current_idx)))
                current_op = ch
                current_idx = ""
            elif ch.isdigit():
                current_idx += ch
        if current_op is not None:
            terms.append((current_op, int(current_idx)))
        return terms

    # Compact format: one letter per qubit (e.g. "IX", "ZZ", "XYZ")
    upper = pauli_string.upper()
    return [(ch, i) for i, ch in enumerate(upper) if ch in "XYZ"]


def _apply_cost_unitary(
    circuit: Circuit,
    hamiltonian_terms: list[tuple[str, float]],
    gamma: float,
) -> None:
    """Apply the cost-function unitary exp(-i γ H_C).

    For each Pauli string with coefficient h, applies exp(-i γ h P).
    """
    for pauli_str, coeff in hamiltonian_terms:
        angle = 2 * gamma * coeff
        terms = _parse_pauli_string(pauli_str)

        # Filter out identity terms
        non_id = [(op, q) for op, q in terms if op != "I"]
        if not non_id:
            continue

        # Step 1: Rotate non-Z qubits to Z basis
        for op, q in non_id:
            if op == "X":
                circuit.h(q)
            elif op == "Y":
                _angle = -np.pi / 2
                circuit.rz(q, float(_angle))
                circuit.h(q)

        # Step 2: CNOT cascade
        for i in range(len(non_id) - 1):
            circuit.cx(non_id[i][1], non_id[i + 1][1])

        # Step 3: Rz on last qubit
        if abs(angle) > 1e-15:
            circuit.rz(non_id[-1][1], float(angle))

        # Step 4: Undo CNOT cascade
        for i in range(len(non_id) - 2, -1, -1):
            circuit.cx(non_id[i][1], non_id[i + 1][1])

        # Step 5: Undo basis rotations
        # Forward Y rotation was Rz(-π/2) then H (matrix H · Rz(-π/2));
        # the inverse is Rz(+π/2) · H, which in circuit order means
        # apply H first and then Rz(+π/2).
        for op, q in non_id:
            if op == "X":
                circuit.h(q)
            elif op == "Y":
                circuit.h(q)
                circuit.rz(q, float(np.pi / 2))
