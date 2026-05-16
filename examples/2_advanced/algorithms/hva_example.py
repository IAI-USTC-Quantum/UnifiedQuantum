#!/usr/bin/env python
"""Hamiltonian Variational Ansatz (HVA) -- complete example.

Demonstrates:
  * Building HVA with commuting Hamiltonian groups
  * Hartree-Fock initial state preparation
  * Energy evaluation and optimization

Usage:
    python hva_example.py [--p-layers L] [--n-iterations N]

References:
    Wecker, D. et al. (2015). "Hackett, and A. Aspuru-Guzik,
    Progress toward practical quantum variational algorithms."
    Phys. Rev. A 92, 060303.

    Kivlichan, I.D. et al. (2018). "Quantum Simulation of Electronic
    Structure with Linear Depth and Connectivity."
    Phys. Rev. Lett. 120, 110501.

[doc-require: ]
"""

import argparse
import sys

import numpy as np

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from uniqc import Circuit
from uniqc.simulator import Simulator
from uniqc.algorithms.core.ansatz import hva
from uniqc.algorithms.core.measurement import pauli_expectation


def _print_circuit_info(circuit, label):
    """Print circuit statistics."""
    print(f"\n  {label}:")
    print(f"    Qubits used: {circuit.max_qubit + 1}")
    print(f"    Gate count: {len(circuit.opcode_list)}")


def demo_hva_basic(p=2):
    """Demonstrate basic HVA construction."""
    print("=" * 60)
    print("Demo 1: Basic HVA Construction")
    print("=" * 60)

    # Define commuting Hamiltonian groups (simplified Hubbard model)
    # Group 1: Hopping terms (X and Y on same pairs)
    hopping = [
        ("X0X1", 1.0),
        ("Y0Y1", 1.0),
    ]
    # Group 2: Interaction term (Z on same pair)
    interaction = [
        ("Z0Z1", 0.5),
    ]
    groups = [hopping, interaction]

    print(f"\n  Hamiltonian groups:")
    print(f"    Group 1 (hopping): {hopping}")
    print(f"    Group 2 (interaction): {interaction}")

    n_params = len(groups) * p
    print(f"\n  HVA configuration:")
    print(f"    Layers (p): {p}")
    print(f"    Groups: {len(groups)}")
    print(f"    Parameters: {n_params} ({len(groups)} groups x {p} layers)")

    # Build the HVA circuit
    c = hva(groups, p=p)
    _print_circuit_info(c, "HVA circuit")

    # Verify statevector validity
    sim = Simulator(backend_type="statevector")
    sv = sim.simulate_statevector(c.originir)
    print(f"\n  Statevector norm: {np.linalg.norm(sv):.10f}")


def demo_hva_hf_state(p=2):
    """Demonstrate HVA with Hartree-Fock initial state."""
    print("\n" + "=" * 60)
    print("Demo 2: HVA with Hartree-Fock Initial State")
    print("=" * 60)

    # Define groups for a 4-qubit system
    groups = [
        [("X0X1", 1.0), ("X1X2", 1.0)],
        [("Y0Y1", 1.0), ("Y1Y2", 1.0)],
        [("Z0Z1", 0.5), ("Z1Z2", 0.5)],
    ]

    print(f"\n  Hamiltonian groups: 3 groups")
    print(f"    Group 1: X hopping")
    print(f"    Group 2: Y hopping")
    print(f"    Group 3: ZZ interactions")

    # Without Hartree-Fock (all qubits start in |0>)
    c_no_hf = hva(groups, p=p)
    print(f"\n  Without Hartree-Fock:")
    print(f"    Initial state: |0000>")
    _print_circuit_info(c_no_hf, "Circuit")

    # With Hartree-Fock (first 2 qubits in |1>)
    c_hf = hva(groups, p=p, hf_state=[0, 1])
    print(f"\n  With Hartree-Fock:")
    print(f"    Initial state: |1100>")
    _print_circuit_info(c_hf, "Circuit")

    # Verify both produce valid statevectors
    sim = Simulator(backend_type="statevector")
    sv_no_hf = sim.simulate_statevector(c_no_hf.originir)
    sv_hf = sim.simulate_statevector(c_hf.originir)
    print(f"\n  Without HF norm: {np.linalg.norm(sv_no_hf):.10f}")
    print(f"  With HF norm: {np.linalg.norm(sv_hf):.10f}")


def demo_hva_energy(p=3, max_iter=20):
    """Demonstrate HVA energy optimization."""
    print("\n" + "=" * 60)
    print("Demo 3: HVA Energy Optimization")
    print("=" * 60)

    # Simple 2-qubit Hamiltonian: H = -Z0Z1 + 0.5*I
    # Ground state: |00> or |11> with E = -1.0 + 0.5 = -0.5
    H = [
        ("Z0Z1", -1.0),
        ("II", 0.5),
    ]
    groups = [[("Z0Z1", -1.0)]]  # Single group containing ZZ

    print(f"\n  Hamiltonian: H = -Z0Z1 + 0.5*I")
    print(f"  Expected ground state: |00> or |11>")
    print(f"  Expected energy: -0.5")

    def energy(params):
        """Compute expectation value of H."""
        c = hva(groups, p=p, params=params)
        e = 0.0
        for pauli, coeff in H:
            e += coeff * pauli_expectation(c, pauli)
        return e

    # Random initial parameters
    n_params = len(groups) * p
    params = np.random.uniform(-np.pi/4, np.pi/4, size=n_params)

    print(f"\n  Optimization (coordinate descent):")
    best_energy = float("inf")
    best_params = params.copy()
    step = 0.1

    for iteration in range(max_iter):
        improved = False
        for i in range(n_params):
            # Try positive step
            params[i] += step
            e_plus = energy(params)
            # Try negative step
            params[i] -= 2 * step
            e_minus = energy(params)
            # Reset
            params[i] += step
            e_curr = energy(params)

            if e_plus < e_curr and e_plus < e_minus:
                params[i] += step
                improved = True
            elif e_minus < e_curr:
                params[i] -= step
                improved = True

        e = energy(params)
        if e < best_energy:
            best_energy = e
            best_params = params.copy()

        if iteration % 5 == 0:
            print(f"    Iter {iteration:2d}: E = {e:.6f}")

        if not improved:
            step *= 0.5
            if step < 1e-6:
                break

    print(f"\n  Final energy: {best_energy:.6f}")
    print(f"  Expected:     -0.500000")
    print(f"  Accuracy:     {abs(best_energy - (-0.5)):.6f}")


def run_demo(p, max_iter):
    """Run all HVA demos."""
    print(f"\n{'=' * 60}")
    print(f"HVA Example (p={p}, iterations={max_iter})")
    print(f"{'=' * 60}")

    demo_hva_basic(p)
    demo_hva_hf_state(p)
    demo_hva_energy(p, max_iter)

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="HVA Example")
    parser.add_argument(
        "-p", "--p-layers", type=int, default=2,
        help="Number of HVA layers (default: 2)"
    )
    parser.add_argument(
        "-n", "--n-iterations", type=int, default=20,
        help="Max optimization iterations (default: 20)"
    )
    args = parser.parse_args()

    if args.p_layers < 1:
        parser.error("-p must be at least 1")
    if args.n_iterations < 1:
        parser.error("-n must be at least 1")

    run_demo(args.p_layers, args.n_iterations)


if __name__ == "__main__":
    main()
