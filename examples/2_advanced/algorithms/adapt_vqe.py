#!/usr/bin/env python3
"""ADAPT-VQE Example.

This script demonstrates how to implement ADAPT-VQE (Adaptively Parametrised
Variational Quantum Eigensolver) using the existing algorithm components in uniqc.

ADAPT-VQE iteratively builds an ansatz by selecting operators from a pool
based on gradient magnitude, rather than using a fixed ansatz structure.

This is an EXAMPLE script, not a reusable algorithm module. Users can copy and
adapt this code for their specific use cases.

References:
- Grimsley et al., "Adaptively parametric ansatz" (2019)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple
import numpy as np

from uniqc.algorithms.core.ansatz._operator_pool import OperatorPool, compute_operator_gradient
from uniqc.algorithms.core.measurement.pauli_expectation import pauli_expectation
from uniqc.algorithms.core.ansatz._pauli_unitary import _apply_cost_unitary
from uniqc.circuit_builder import Circuit
from uniqc.simulator import Simulator


@dataclass
class ADAPTVQEResult:
    """Result of ADAPT-VQE optimization."""

    energy: float
    params: np.ndarray
    selected_operators: List[Tuple[str, float, float]]  # (op, coeff, gradient)
    history: List[float] = field(default_factory=list)
    n_iterations: int = 0
    converged: bool = False


def _build_adapt_circuit(
    operators: List[Tuple[str, float]],
    params: np.ndarray,
    n_qubits: int = 1,
) -> Circuit:
    """Build the ADAPT ansatz circuit from selected operators and parameters."""
    circuit = Circuit(n_qubits)

    for i, (pauli_str, coeff) in enumerate(operators):
        theta = float(params[i]) if i < len(params) else 0.0
        _apply_cost_unitary(circuit, [(pauli_str, coeff)], theta)

    return circuit


def _energy(
    circuit: Circuit,
    hamiltonian: List[Tuple[str, float]],
    shots: Optional[int] = None,
) -> float:
    """Compute expectation value of Hamiltonian."""
    total = 0.0
    for pauli, coeff in hamiltonian:
        total += float(coeff) * pauli_expectation(circuit, pauli, shots=shots)
    return total


def _optimize_circuit(
    circuit: Circuit,
    hamiltonian: List[Tuple[str, float]],
    n_params: int,
    shots: Optional[int] = None,
) -> Tuple[float, np.ndarray]:
    """Optimize parameters using COBYLA (simple derivative-free method)."""
    try:
        from scipy.optimize import minimize
    except ImportError:
        raise ImportError("scipy is required for ADAPT-VQE optimization")

    history: List[float] = []

    def objective(params: np.ndarray) -> float:
        # Rebuild circuit with current parameters
        circ = _build_adapt_circuit(
            [(f"I{''.join(['I'] * (n_params - 1))}", 0.0)],  # placeholder
            params,
        )
        # Actually rebuild with the operators from the closure
        circ = _build_adapt_circuit(operators_from_closure, params)
        e = _energy(circ, hamiltonian, shots)
        history.append(e)
        return e

    # Store operators for the closure
    global operators_from_closure
    operators_from_closure = []

    # Use simple random initialization
    init_params = np.random.uniform(-np.pi / 4, np.pi / 4, size=n_params)

    # Simple optimization
    result = minimize(objective, init_params, method="COBYLA", options={"maxiter": 50})

    return float(result.fun), np.asarray(result.x)


# Global for closure
operators_from_closure = []


def adapt_vqe(
    hamiltonian: List[Tuple[str, float]],
    operator_pool: OperatorPool,
    *,
    n_qubits: Optional[int] = None,
    max_iterations: int = 20,
    convergence_threshold: float = 1e-4,
    shots: Optional[int] = None,
    verbose: bool = True,
) -> ADAPTVQEResult:
    """Run ADAPT-VQE optimization.

    Args:
        hamiltonian: List of (pauli_string, coefficient) tuples.
        operator_pool: Pool of operators to choose from.
        n_qubits: Number of qubits. Auto-detected if not provided.
        max_iterations: Maximum ADAPT iterations.
        convergence_threshold: Stop when gradient norm falls below this.
        shots: Shots for expectation value. None = statevector.
        verbose: Print progress.

    Returns:
        ADAPTVQEResult with optimal energy and parameters.

    Example:
        >>> from uniqc.examples.algorithms.adapt_vqe import adapt_vqe, OperatorPool
        >>> H = [("ZZ", -1.0), ("ZI", 0.5), ("IZ", 0.5)]
        >>> pool = OperatorPool.minimal_pool(n_qubits=2)
        >>> result = adapt_vqe(H, pool, n_qubits=2)
        >>> print(f"Energy: {result.energy:.6f}")
    """
    global operators_from_closure

    # Auto-detect n_qubits
    if n_qubits is None:
        max_idx = 0
        for pauli, _ in hamiltonian:
            for ch in pauli:
                if ch.isdigit():
                    max_idx = max(max_idx, int(ch))
        n_qubits = max_idx + 1

    selected_operators: List[Tuple[str, float]] = []
    params: np.ndarray = np.array([])
    history: List[float] = []

    if verbose:
        print(f"ADAPT-VQE starting with {len(operator_pool)} operators in pool")
        print(f"Hamiltonian: {hamiltonian}")
        print("-" * 60)

    for iteration in range(max_iterations):
        # Build current ansatz circuit
        if selected_operators:
            current_circuit = _build_adapt_circuit(selected_operators, params, n_qubits)
            current_energy = _energy(current_circuit, hamiltonian, shots)
            history.append(current_energy)
        else:
            current_energy = 0.0
            current_circuit = Circuit(n_qubits)

        if verbose:
            print(f"Iter {iteration + 1}: E = {current_energy:.8f}, "
                  f"n_operators = {len(selected_operators)}")

        # Compute gradients for all pool operators
        gradients: List[Tuple[int, str, float, float]] = []

        for i, (pauli_str, coeff) in enumerate(operator_pool.operators()):
            try:
                gradient = compute_operator_gradient(
                    current_circuit,
                    (pauli_str, coeff),
                    hamiltonian,
                    shots,
                    n_qubits=n_qubits,
                )
                gradients.append((i, pauli_str, coeff, gradient))
            except Exception:
                # Skip operators that fail gradient computation
                continue

        if not gradients:
            if verbose:
                print("  No valid gradients, stopping.")
            break

        # Find operator with largest gradient
        gradients.sort(key=lambda x: x[3], reverse=True)
        best_idx, best_pauli, best_coeff, best_grad = gradients[0]

        if verbose:
            print(f"  Best operator: {best_pauli}, gradient = {best_grad:.8f}")

        # Check convergence
        if best_grad < convergence_threshold:
            if verbose:
                print(f"  Converged (gradient {best_grad:.2e} < {convergence_threshold:.2e})")
            break

        # Add operator to ansatz
        selected_operators.append((best_pauli, best_coeff))

        # Remove from pool (optional - for faster subsequent iterations)
        # pool.remove_operator(best_idx)

        # Re-optimize all parameters
        new_params = np.random.uniform(-np.pi / 4, np.pi / 4, size=len(selected_operators))

        # Simple optimization loop
        operators_from_closure = selected_operators

        for _ in range(30):  # Simple SGD-like optimization
            for j in range(len(selected_operators)):
                # Finite difference gradient
                eps = np.pi / 8
                test_params_plus = new_params.copy()
                test_params_plus[j] += eps
                test_params_minus = new_params.copy()
                test_params_minus[j] -= eps

                circ_plus = _build_adapt_circuit(selected_operators, test_params_plus, n_qubits)
                circ_minus = _build_adapt_circuit(selected_operators, test_params_minus, n_qubits)

                e_plus = _energy(circ_plus, hamiltonian, shots)
                e_minus = _energy(circ_minus, hamiltonian, shots)
                grad_j = (e_plus - e_minus) / (2 * eps)

                # Simple gradient descent step
                lr = 0.1
                new_params[j] -= lr * grad_j

        params = new_params

    # Final energy
    if selected_operators:
        final_circuit = _build_adapt_circuit(selected_operators, params, n_qubits)
        final_energy = _energy(final_circuit, hamiltonian, shots)
    else:
        final_energy = 0.0

    if verbose:
        print("-" * 60)
        print(f"Final energy: {final_energy:.8f}")
        print(f"Selected {len(selected_operators)} operators")

    return ADAPTVQEResult(
        energy=final_energy,
        params=params,
        selected_operators=[
            (op, coeff, 0.0) for op, coeff in selected_operators
        ],  # gradient not stored
        history=history,
        n_iterations=iteration + 1,
        converged=best_grad < convergence_threshold if gradients else False,
    )


def main():
    """Run ADAPT-VQE on a simple 2-qubit Hamiltonian."""
    print("=" * 60)
    print("ADAPT-VQE Example: 2-Qubit Hamiltonian")
    print("=" * 60)

    # Simple Hamiltonian: H = -Z0Z1 + 0.5*I
    # Ground state energy should be -1.0 (for the ZZ term)
    hamiltonian = [
        ("ZZ", -1.0),
        ("II", 0.5),
    ]

    # Use minimal operator pool
    pool = OperatorPool.minimal_pool(n_qubits=2)

    print(f"Using {len(pool)} operators from minimal pool")
    print()

    result = adapt_vqe(
        hamiltonian,
        pool,
        n_qubits=2,
        max_iterations=10,
        convergence_threshold=1e-4,
        verbose=True,
    )

    print()
    print("=" * 60)
    print("ADAPT-VQE Results:")
    print(f"  Energy: {result.energy:.8f}")
    print(f"  Iterations: {result.n_iterations}")
    print(f"  Converged: {result.converged}")
    print(f"  Selected operators: {len(result.selected_operators)}")
    for op, coeff, grad in result.selected_operators:
        print(f"    {op} (coeff={coeff:.2f})")

    # Compare with VQE using full HEA
    print()
    print("Comparison with standard VQE (HEA):")
    from uniqc.algorithms.workflows.vqe_workflow import run_vqe_workflow

    vqe_result = run_vqe_workflow(hamiltonian, n_qubits=2, depth=2)
    print(f"  VQE Energy: {vqe_result.energy:.8f}")
    print(f"  VQE Success: {vqe_result.success}")


if __name__ == "__main__":
    main()
