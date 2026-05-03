"""QAOA for MaxCut using TorchQuantum backend with native PyTorch autograd.

Demonstrates Quantum Approximate Optimization Algorithm on a triangle graph
with Adam optimizer, using TorchQuantum's differentiable simulation.
"""

try:
    import torch
    from uniqc import QAOASolver
except ImportError as e:
    print(f"Required dependencies not available: {e}")
    print("Install with: pip install unified-quantum[pytorch]")
    print('Then install TorchQuantum manually: pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"')
    raise SystemExit(1)


def main():
    print("=" * 60)
    print("QAOA for MaxCut — TorchQuantum Backend")
    print("=" * 60)

    # Triangle graph: 3 nodes, 3 edges
    edges = [(0, 1), (1, 2), (0, 2)]
    n_qubits = 3
    p = 2  # QAOA depth

    print(f"\nGraph: Triangle (3 nodes, 3 edges)")
    print(f"Edges: {edges}")
    print(f"QAOA depth p={p}")
    print(f"Max cut value (exact): 2.0\n")

    # Create solver
    solver = QAOASolver(
        edges=edges,
        n_qubits=n_qubits,
        p=p,
        lr=0.05,
    )

    # Optimize
    cut_value, optimal_params = solver.solve(n_iters=100, verbose=True)

    print(f"\nFinal cut value: {cut_value:.6f}")
    print(f"Optimal gammas: {optimal_params[:p].tolist()}")
    print(f"Optimal betas:  {optimal_params[p:].tolist()}")
    print(f"Approximation ratio: {cut_value / 2.0:.4f}")


if __name__ == "__main__":
    main()
