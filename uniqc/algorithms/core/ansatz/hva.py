"""Hamiltonian Variational Ansatz (HVA).

Constructs an ansatz that alternates between groups of commuting Hamiltonian
terms, suitable for quantum chemistry simulations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit

from ._pauli_unitary import _apply_cost_unitary

__all__ = ["hva"]

if TYPE_CHECKING:
    from uniqc.circuit_builder.parameter import Parameters


def hva(
    hamiltonian_groups: list[list[tuple[str, float]]],
    p: int = 1,
    qubits: list[int] | None = None,
    params: Parameters | np.ndarray | None = None,
    hf_state: list[int] | None = None,
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
        hf_state: Qubit indices to initialize in ``|1>`` (Hartree-Fock state).
            ``None`` → all qubits start in ``|0>``.

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

    qubits = list(range(n_qubits)) if qubits is None else list(qubits)

    n_groups = len(hamiltonian_groups)
    n_params = n_groups * p

    # Import Parameters for auto-generation
    from uniqc.circuit_builder.parameter import Parameters as ParamClass

    if params is None:
        # Auto-generate named Parameters
        params = ParamClass("theta_hva", size=n_params)
        rng = np.random.default_rng(0)
        params.bind(list(rng.uniform(0, np.pi, size=n_params)))
    elif isinstance(params, ParamClass):
        if len(params) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters (n_groups={n_groups} × p={p}), got {len(params)}",
                    "circuit_validation",
                )
            )
        if not params[0].is_bound:
            rng = np.random.default_rng(0)
            params.bind(list(rng.uniform(0, np.pi, size=n_params)))
    else:
        # Convert np.ndarray to Parameters
        params_arr = np.asarray(params)
        if len(params_arr) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters (n_groups={n_groups} × p={p}), got {len(params_arr)}",
                    "circuit_validation",
                )
            )
        params = ParamClass("theta_hva", size=n_params)
        params.bind(list(params_arr.flatten()))

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
            theta = params[layer * n_groups + g].evaluate()
            _apply_cost_unitary(circuit, group, theta)

    # Attach parameters to circuit for traceability
    circuit._params = params

    return circuit
