"""Hamiltonian Variational Ansatz (HVA).

Constructs an ansatz that alternates between groups of commuting Hamiltonian
terms, suitable for quantum chemistry simulations.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np
from uniqc.circuit_builder import Circuit
from uniqc._error_hints import format_enriched_message

from ._pauli_unitary import _apply_cost_unitary

__all__ = ["hva"]


def hva(
    hamiltonian_groups: List[List[Tuple[str, float]]],
    p: int = 1,
    qubits: Optional[List[int]] = None,
    params: Optional[np.ndarray] = None,
    hf_state: Optional[List[int]] = None,
) -> Circuit:
    """Build a Hamiltonian Variational Ansatz (HVA) circuit.

    The HVA alternates between applying exponentials of commuting Hamiltonian
    groups. Each group is applied with an independent variational parameter.

    Args:
        hamiltonian_groups: List of commuting Hamiltonian groups.
            Each group is a list of ``(pauli_string, coefficient)`` tuples.
            Groups should contain mutually commuting operators.
        p: Number of ansatz layers (repetitions of the full group cycle).
        qubits: Qubit indices.  ``None`` → auto-detect from hamiltonian.
        params: Variational parameters.  Length must equal ``len(hamiltonian_groups) * p``.
            ``None`` → random initialization.
        hf_state: Qubit indices to initialize in |1> (Hartree-Fock state).
            ``None`` → all qubits start in |0>.

    Returns:
        A :class:`Circuit` object.

    Raises:
        ValueError: Parameter count mismatch or empty groups.

    Example:
        >>> # Hubbard model example with two groups: hopping and interaction
        >>> hopping = [("X0X1", 1.0), ("Y0Y1", 1.0)]
        >>> interaction = [("Z0Z1", 0.5)]
        >>> groups = [hopping, interaction]
        >>> c = hva(groups, p=2)
    """
    if not hamiltonian_groups:
        raise ValueError(
            format_enriched_message(
                "hamiltonian_groups must contain at least one group",
                "circuit_validation",
            )
        )

    # Determine qubit set from all groups
    from ._pauli_unitary import _parse_pauli_string

    all_qubits = set()
    for group in hamiltonian_groups:
        for pauli_str, _ in group:
            for _, q in _parse_pauli_string(pauli_str):
                all_qubits.add(q)
    n_qubits = max(all_qubits) + 1 if all_qubits else 0

    if qubits is None:
        qubits = list(range(n_qubits))
    else:
        qubits = list(qubits)

    n_groups = len(hamiltonian_groups)
    n_params = n_groups * p

    if params is None:
        params = np.random.uniform(0, np.pi, size=n_params)
    else:
        params = np.asarray(params)
        if len(params) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters (n_groups={n_groups} × p={p}), "
                    f"got {len(params)}",
                    "circuit_validation",
                )
            )

    circuit = Circuit()

    # Apply Hartree-Fock initial state if specified
    if hf_state is not None:
        for q in hf_state:
            circuit.x(q)

    # HVA layers
    for layer in range(p):
        for g, group in enumerate(hamiltonian_groups):
            if not group:
                continue
            theta = float(params[layer * n_groups + g])
            _apply_cost_unitary(circuit, group, theta)

    return circuit
