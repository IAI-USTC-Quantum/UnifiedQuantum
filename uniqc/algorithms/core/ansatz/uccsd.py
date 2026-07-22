"""UCCSD (Unitary Coupled-Cluster Singles and Doubles) ansatz.

Implements a simplified UCCSD ansatz for variational quantum chemistry
simulations.  Each single/double excitation is parameterised by an
independent variational angle.
"""

__all__ = ["uccsd_ansatz"]

from itertools import combinations
from typing import TYPE_CHECKING, Union

import numpy as np

from uniqc._error_hints import format_enriched_message
from uniqc.circuit_builder import Circuit

if TYPE_CHECKING:
    from uniqc.circuit_builder.parameter import Parameters


def _single_excitation(
    circuit: Circuit,
    p: int,
    q: int,
    theta: float,
) -> None:
    """Apply a single-excitation gate G^{pq}(θ).

    Maps |0_p 1_q> → cos(θ)|0_p 1_q> + sin(θ)|1_p 0_q>.
    Uses a Givens-rotation decomposition with 2 CNOTs.
    """
    # G^{pq}(θ) = CX(p,q); Ry(q, -θ); CX(p,q)
    # This maps |01> → cos(θ)|01> - sin(θ)|10> in the {p,q} subspace
    # (when p is the higher orbital and q the lower)
    circuit.cx(p, q)
    if abs(theta) > 1e-15:
        circuit.ry(q, float(-theta))
    circuit.cx(p, q)


def _double_excitation(
    circuit: Circuit,
    i: int,
    j: int,
    a: int,
    b: int,
    theta: float,
) -> None:
    """Apply a double-excitation gate.

    Uses 8 CNOTs + 1 Ry for the standard UCCSD double excitation
    decomposition.
    """
    # Standard decomposition for exp(θ (a†_b a†_a a_j a_i - h.c.))
    # Uses the 8-CNOT decomposition
    # Step 1: CNOT cascade from occupied to virtual
    circuit.cx(i, j)
    circuit.cx(j, a)
    circuit.cx(a, b)

    # Step 2: Ry on target
    if abs(theta / 2) > 1e-15:
        circuit.ry(b, float(theta / 2))

    # Step 3: Undo and redo with different control phase
    circuit.cx(a, b)
    if abs(theta / 2) > 1e-15:
        circuit.ry(b, float(-theta / 2))
    circuit.cx(j, b)
    if abs(theta / 2) > 1e-15:
        circuit.ry(b, float(theta / 2))
    circuit.cx(a, b)
    if abs(theta / 2) > 1e-15:
        circuit.ry(b, float(-theta / 2))

    # Step 4: Undo cascade
    circuit.cx(j, b)
    circuit.cx(i, b)
    circuit.cx(i, j)


def uccsd_ansatz(
    n_qubits: int,
    n_electrons: int,
    qubits: list[int] | None = None,
    params: Union["Parameters", np.ndarray] | None = None,
) -> Circuit:
    """Build a UCCSD (Unitary Coupled-Cluster Singles and Doubles) ansatz.

    Occupies the first *n_electrons* spin-orbitals and allows single
    excitations from occupied → virtual and double excitations from
    pairs of occupied → pairs of virtual.

    Args:
        n_qubits: Total number of qubits (spin-orbitals).
        n_electrons: Number of occupied spin-orbitals.
        qubits: Qubit indices.  ``None`` → ``list(range(n_qubits))``.
        params: Variational parameters.  ``None`` → zeros (no excitation).

    Returns:
        A :class:`Circuit` object.

    Raises:
        ValueError: *n_electrons* > *n_qubits*.
        ValueError: *params* length does not match the expected count.

    Example:
        >>> from uniqc.algorithms.core.ansatz import uccsd_ansatz
        >>> c = uccsd_ansatz(n_qubits=4, n_electrons=2)
    """
    if n_electrons > n_qubits:
        raise ValueError(
            format_enriched_message(
                f"n_electrons ({n_electrons}) must not exceed n_qubits ({n_qubits})", "circuit_validation"
            )
        )

    qubits = list(range(n_qubits)) if qubits is None else list(qubits)

    occupied = list(range(n_electrons))
    virtual = list(range(n_electrons, n_qubits))

    # Count singles and doubles
    n_singles = len(occupied) * len(virtual)
    n_doubles = len(list(combinations(occupied, 2))) * len(list(combinations(virtual, 2)))
    n_params = n_singles + n_doubles

    # Import Parameters for auto-generation
    from uniqc.circuit_builder.parameter import Parameters as ParamClass

    if params is None:
        # Auto-generate named Parameters (initialized to zero)
        params = ParamClass("theta_uccsd", size=n_params)
        params.bind([0.0] * n_params)
    elif isinstance(params, ParamClass):
        if len(params) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters ({n_singles} singles + {n_doubles} doubles), got {len(params)}",
                    "circuit_validation",
                )
            )
        if not params[0].is_bound:
            params.bind([0.0] * n_params)
    else:
        # Convert np.ndarray to Parameters
        params_arr = np.asarray(params)
        if len(params_arr) != n_params:
            raise ValueError(
                format_enriched_message(
                    f"Expected {n_params} parameters "
                    f"({n_singles} singles + {n_doubles} doubles), "
                    f"got {len(params_arr)}",
                    "circuit_validation",
                )
            )
        params = ParamClass("theta_uccsd", size=n_params)
        params.bind(list(params_arr.flatten()))

    circuit = Circuit()

    # Hartree-Fock initial state: occupy first n_electrons qubits
    for i in occupied:
        circuit.x(qubits[i])

    idx = 0

    # Single excitations: occupied → virtual
    for occ in occupied:
        for virt in virtual:
            val = params[idx].evaluate()
            if abs(val) > 1e-15:
                _single_excitation(circuit, qubits[occ], qubits[virt], val)
            idx += 1

    # Double excitations: pairs of occupied → pairs of virtual
    for i, j in combinations(occupied, 2):
        for a, b in combinations(virtual, 2):
            val = params[idx].evaluate()
            if abs(val) > 1e-15:
                _double_excitation(circuit, qubits[i], qubits[j], qubits[a], qubits[b], val)
            idx += 1

    # Attach parameters to circuit for traceability
    circuit._params = params

    return circuit
