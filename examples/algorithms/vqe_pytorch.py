"""VQE for H2 molecule using TorchQuantum backend with native PyTorch autograd.

Demonstrates variational quantum eigensolver with Adam optimizer,
using TorchQuantum's differentiable simulation (no parameter-shift rule).
"""

try:
    import torch
    from uniqc import VQESolver, build_h2_hamiltonian
except ImportError as e:
    print(f"Required dependencies not available: {e}")
    print("Install with: pip install unified-quantum[pytorch]")
    print('Then install TorchQuantum manually: pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"')
    raise SystemExit(1)


def main():
    print("=" * 60)
    print("VQE for H2 Molecule — TorchQuantum Backend")
    print("=" * 60)

    # Build H2 Hamiltonian
    pauli_terms, nuclear_repulsion = build_h2_hamiltonian()
    n_qubits = 4
    depth = 2
    n_params = 2 * n_qubits * depth  # 16 params

    print(f"\nMolecule: H2 (STO-3G, 4 qubits)")
    print(f"Nuclear repulsion: {nuclear_repulsion:.4f}")
    print(f"Pauli terms: {len(pauli_terms)}")
    print(f"Ansatz: HEA depth={depth}, params={n_params}")
    print(f"Exact FCI energy: -1.137274 Ha\n")

    # Create solver
    solver = VQESolver(
        hamiltonian=pauli_terms,
        nuclear_repulsion=nuclear_repulsion,
        n_qubits=n_qubits,
        n_params=n_params,
        lr=0.05,
    )

    # Optimize
    final_energy, optimal_params = solver.solve(n_iters=100, verbose=True)

    print(f"\nFinal energy: {final_energy:.6f} Ha")
    print(f"Optimal params: {optimal_params[:4].tolist()} ...")
    print(f"\nExpected: ~-1.10 Ha (simplified Hamiltonian)")


if __name__ == "__main__":
    main()
