"""Operator pool utilities for ADAPT-VQE and similar algorithms.

Provides reusable building blocks for operator pool construction and
gradient computation using the parameter-shift rule.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from itertools import combinations
import numpy as np

from uniqc.circuit_builder import Circuit
from uniqc.algorithms.core.measurement.pauli_expectation import pauli_expectation
from uniqc.algorithms.core.ansatz._pauli_unitary import _parse_pauli_string, _apply_cost_unitary

__all__ = ["OperatorPool", "compute_operator_gradient"]


class OperatorPool:
    """Pool of excitation operators for ADAPT-VQE.

    Generates operators (Pauli strings with coefficients) that can be used
    to iteratively build an ansatz.
    """

    def __init__(
        self,
        operators: Optional[List[Tuple[str, float]]] = None,
    ) -> None:
        """Initialize with explicit operator list.

        Args:
            operators: List of (pauli_string, coefficient) tuples.
        """
        self._operators = operators or []

    @classmethod
    def uccsd_pool(cls, n_qubits: int, n_electrons: int) -> "OperatorPool":
        """Generate UCCSD singles + doubles operator pool.

        Args:
            n_qubits: Total number of spin-orbitals (qubits).
            n_electrons: Number of occupied spin-orbitals.

        Returns:
            OperatorPool containing all single and double excitation operators.
        """
        if n_electrons > n_qubits:
            raise ValueError(
                f"n_electrons ({n_electrons}) must not exceed n_qubits ({n_qubits})"
            )

        occupied = list(range(n_electrons))
        virtual = list(range(n_electrons, n_qubits))
        operators: List[Tuple[str, float]] = []

        # Single excitations: occupied -> virtual
        for i in occupied:
            for a in virtual:
                pauli_str = _generate_excitation_pauli(n_qubits, i, a, is_double=False)
                operators.append((pauli_str, 1.0))

        # Double excitations: pairs of occupied -> pairs of virtual
        for i, j in combinations(occupied, 2):
            for a, b in combinations(virtual, 2):
                pauli_str = _generate_excitation_pauli(n_qubits, i, j, a, b)
                operators.append((pauli_str, 1.0))

        return cls(operators)

    @classmethod
    def minimal_pool(cls, n_qubits: int) -> "OperatorPool":
        """Generate a minimal pool with single and two-qubit Pauli excitations.

        For n qubits, includes all single-qubit Pauli operators and
        all two-qubit ZZ interactions.

        Args:
            n_qubits: Number of qubits.

        Returns:
            OperatorPool with minimal operator set.
        """
        operators: List[Tuple[str, float]] = []

        # Single-qubit excitations (X, Y on each qubit)
        for q in range(n_qubits):
            pauli = "I" * q + "X" + "I" * (n_qubits - q - 1)
            operators.append((pauli, 1.0))
            pauli = "I" * q + "Y" + "I" * (n_qubits - q - 1)
            operators.append((pauli, 1.0))

        # Two-qubit ZZ interactions
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                pauli = "I" * i + "Z" + "I" * (j - i - 1) + "Z" + "I" * (n_qubits - j - 1)
                operators.append((pauli, 1.0))

        return cls(operators)

    def operators(self) -> List[Tuple[str, float]]:
        """Return the list of (pauli_string, coefficient) operators."""
        return self._operators

    def __len__(self) -> int:
        return len(self._operators)

    def __iter__(self):
        return iter(self._operators)


def _generate_excitation_pauli(
    n_qubits: int,
    i: int,
    a: int,
    is_double: bool = False,
    j: Optional[int] = None,
    b: Optional[int] = None,
) -> str:
    """Generate Pauli string for an excitation operator.

    Single excitation: creates Y_i X_a - X_i Y_a pattern
    Double excitation: creates Y_i Y_j X_a X_b - X_i X_j Y_a Y_b pattern
    """
    if is_double and (j is None or b is None):
        raise ValueError("Double excitation requires j and b parameters")

    if is_double:
        # Double excitation: Y_i Y_j X_a X_b - X_i X_j Y_a Y_b
        pauli = ["I"] * n_qubits
        pauli[i] = "Y"
        pauli[j] = "Y"
        pauli[a] = "X"
        pauli[b] = "X"
        return "".join(pauli)
    else:
        # Single excitation: Y_i X_a - X_i Y_a
        pauli = ["I"] * n_qubits
        pauli[i] = "Y"
        pauli[a] = "X"
        return "".join(pauli)


def compute_operator_gradient(
    circuit: Circuit,
    operator: Tuple[str, float],
    hamiltonian: List[Tuple[str, float]],
    shots: Optional[int] = None,
) -> float:
    """Compute the gradient of energy with respect to an operator's parameter.

    Uses the parameter-shift rule:
    gradient = (E(θ + π/4) - E(θ - π/4)) / 2

    Args:
        circuit: Base circuit with current parameters applied.
        operator: The (pauli_string, coefficient) operator to compute gradient for.
        hamiltonian: Full Hamiltonian as list of (pauli_string, coefficient).
        shots: Number of shots for measurement. ``None`` uses statevector.

    Returns:
        Absolute value of the gradient magnitude.

    Note:
        This computes the gradient of ⟨H⟩ with respect to the angle parameter
        of the given operator in the ansatz circuit.
    """
    from uniqc.simulator import Simulator

    pauli_str, coeff = operator
    shift = np.pi / 4

    # Create two copies of the circuit with shifted parameters
    sim = Simulator(backend_type="statevector", least_qubit_remapping=False)

    # Build circuit with +shift
    circ_plus = Circuit()
    circ_plus.add_circuit(circuit)
    _apply_cost_unitary(circ_plus, [(pauli_str, coeff)], shift)
    circ_plus.measure_all()

    # Build circuit with -shift
    circ_minus = Circuit()
    circ_minus.add_circuit(circuit)
    _apply_cost_unitary(circ_minus, [(pauli_str, coeff)], -shift)
    circ_minus.measure_all()

    # Compute energies
    def energy(c: Circuit) -> float:
        total = 0.0
        for pauli, c_coeff in hamiltonian:
            total += c_coeff * pauli_expectation(c, pauli, shots=shots)
        return total

    e_plus = energy(circ_plus)
    e_minus = energy(circ_minus)

    # Parameter-shift gradient
    gradient = (e_plus - e_minus) / 2
    return abs(gradient)
