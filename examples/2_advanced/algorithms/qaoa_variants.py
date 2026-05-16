#!/usr/bin/env python
"""QAOA Variants -- XY Mixer, Warm-Start, and MA-QAOA.

Demonstrates:
  * Standard QAOA with XY mixer for constrained optimization
  * Warm-start QAOA with custom initial state
  * MA-QAOA with per-term angles

Usage:
    python qaoa_variants.py [--p LAYERS] [--n-nodes N]

References:
    Hadfield, S. et al. (2019). "From the Quantum Approximate Optimization
    Algorithm to a Quantum Alternating Operator Ansatz." arXiv:1709.03489.

    Egger, D.J. et al. (2021). "Warm-starting quantum optimization."
    arXiv:2009.10095.

    Hadir, M. et al. (2023). "Multi-Angle Quantum Approximate Optimization
    Algorithm." arXiv:2305.04881.

[doc-require: ]
"""

import argparse
import sys

import numpy as np

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from uniqc import Circuit
from uniqc.simulator import Simulator
from uniqc.algorithms.core.ansatz import qaoa_ansatz


def _build_maxcut_hamiltonian(edges):
    """Build MaxCut cost Hamiltonian for a graph.

    H_C = -1/2 sum_{(i,j) in E} (1 - Z_i Z_j)
    """
    hamiltonian = []
    for i, j in edges:
        # -1/2 * (1 - Z_i Z_j) = -1/2*I + 1/2*Z_i Z_j
        hamiltonian.append((f"Z{i}Z{j}", 0.5))
    return hamiltonian


def _print_circuit_info(circuit, label):
    """Print circuit statistics."""
    print(f"\n  {label}:")
    print(f"    Qubits used: {circuit.max_qubit + 1}")
    print(f"    Gate count: {len(circuit.opcode_list)}")


def demo_xy_mixer(p=2, n_nodes=4):
    """Demonstrate QAOA with XY mixer for constrained optimization."""
    print("=" * 60)
    print("Demo 1: XY Mixer")
    print("=" * 60)

    # Ring graph (constrained to exactly n_nodes/2 cuts in optimal solution)
    edges = [(i, (i + 1) % n_nodes) for i in range(n_nodes)]
    H = _build_maxcut_hamiltonian(edges)

    print(f"\n  Graph: Ring with {n_nodes} nodes")
    print(f"  Edges: {edges}")

    # Standard QAOA
    c_standard = qaoa_ansatz(H, p=p)
    print(f"\n  Standard QAOA (X mixer):")
    print(f"    Parameters: betas={p}, gammas={p} (total: {2*p})")
    _print_circuit_info(c_standard, "Standard circuit")

    # XY mixer QAOA
    c_xy = qaoa_ansatz(H, p=p, mixer="xy")
    print(f"\n  XY Mixer QAOA:")
    print(f"    Parameters: betas={p}, gammas={p} (total: {2*p})")
    print(f"    Note: XY mixer preserves excitation number")
    _print_circuit_info(c_xy, "XY mixer circuit")

    # Verify both produce valid statevectors
    sim = Simulator(backend_type="statevector")
    sv_std = sim.simulate_statevector(c_standard.originir)
    sv_xy = sim.simulate_statevector(c_xy.originir)
    print(f"\n  Standard norm: {np.linalg.norm(sv_std):.10f}")
    print(f"  XY mixer norm: {np.linalg.norm(sv_xy):.10f}")


def demo_warm_start(p=2, n_nodes=4):
    """Demonstrate warm-start QAOA with custom initial state."""
    print("\n" + "=" * 60)
    print("Demo 2: Warm-Start QAOA")
    print("=" * 60)

    # Simple line graph
    edges = [(i, i + 1) for i in range(n_nodes - 1)]
    H = _build_maxcut_hamiltonian(edges)

    print(f"\n  Graph: Line with {n_nodes} nodes")
    print(f"  Edges: {edges}")

    # Standard QAOA (starts from uniform superposition)
    c_standard = qaoa_ansatz(H, p=p)
    print(f"\n  Standard QAOA (uniform superposition):")
    print(f"    Initial: Hadamards on all qubits")
    _print_circuit_info(c_standard, "Standard circuit")

    # Warm-start: custom initial state
    # Example: start from a greedy solution (alternate 0/1 pattern)
    warm_state = Circuit()
    for i in range(n_nodes):
        if i % 2 == 0:
            warm_state.x(i)

    c_warm = qaoa_ansatz(H, p=p, initial_state=warm_state)
    print(f"\n  Warm-Start QAOA (greedy solution):")
    print(f"    Initial: |0101...> (alternating pattern)")
    _print_circuit_info(c_warm, "Warm-start circuit")

    # Compare circuit depths
    print(f"\n  Comparison:")
    print(f"    Standard: {len(c_standard.opcode_list)} gates")
    print(f"    Warm-start: {len(c_warm.opcode_list)} gates")

    # Verify both produce valid statevectors
    sim = Simulator(backend_type="statevector")
    sv_std = sim.simulate_statevector(c_standard.originir)
    sv_warm = sim.simulate_statevector(c_warm.originir)
    print(f"\n  Standard norm: {np.linalg.norm(sv_std):.10f}")
    print(f"  Warm-start norm: {np.linalg.norm(sv_warm):.10f}")


def demo_ma_qaoa(p=2, n_nodes=4):
    """Demonstrate MA-QAOA with per-term angles."""
    print("\n" + "=" * 60)
    print("Demo 3: MA-QAOA (Multi-Angle)")
    print("=" * 60)

    # Triangle graph
    edges = [(0, 1), (1, 2), (0, 2)]
    H = _build_maxcut_hamiltonian(edges)

    n_terms = len(edges)
    print(f"\n  Graph: Triangle")
    print(f"  Edges (Hamiltonian terms): {n_terms}")

    # Standard QAOA
    c_standard = qaoa_ansatz(H, p=p)
    std_params = 2 * p  # p betas + p gammas
    print(f"\n  Standard QAOA:")
    print(f"    Parameters: {std_params} (p betas + p gammas)")

    # MA-QAOA: each term gets its own gamma, each qubit gets its own beta
    c_ma = qaoa_ansatz(H, p=p, multi_angle=True)
    ma_betas = n_nodes * p
    ma_gammas = n_terms * p
    ma_params = ma_betas + ma_gammas
    print(f"\n  MA-QAOA:")
    print(f"    Parameters: {ma_params} ({n_terms} terms x {p} layers gammas + {n_nodes} qubits x {p} layers betas)")
    print(f"    Improvement: {ma_params - std_params} extra parameters")

    _print_circuit_info(c_standard, "Standard circuit")
    _print_circuit_info(c_ma, "MA-QAOA circuit")

    # Verify both produce valid statevectors
    sim = Simulator(backend_type="statevector")
    sv_std = sim.simulate_statevector(c_standard.originir)
    sv_ma = sim.simulate_statevector(c_ma.originir)
    print(f"\n  Standard norm: {np.linalg.norm(sv_std):.10f}")
    print(f"  MA-QAOA norm: {np.linalg.norm(sv_ma):.10f}")


def run_demo(p, n_nodes):
    """Run all QAOA variant demos."""
    print(f"\n{'=' * 60}")
    print(f"QAOA Variants Demo (p={p}, nodes={n_nodes})")
    print(f"{'=' * 60}")

    demo_xy_mixer(p, n_nodes)
    demo_warm_start(p, n_nodes)
    demo_ma_qaoa(p, n_nodes)

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="QAOA Variants Demo")
    parser.add_argument(
        "-p", "--p-layers", type=int, default=2,
        help="Number of QAOA layers (default: 2)"
    )
    parser.add_argument(
        "-n", "--n-nodes", type=int, default=4,
        help="Number of graph nodes (default: 4)"
    )
    args = parser.parse_args()

    if args.p_layers < 1:
        parser.error("-p must be at least 1")
    if args.n_nodes < 3:
        parser.error("-n must be at least 3")

    run_demo(args.p_layers, args.n_nodes)


if __name__ == "__main__":
    main()
