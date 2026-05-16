#!/usr/bin/env python
"""Hardware-Efficient Ansatz (HEA) -- Configuration Options.

Demonstrates:
  * Configurable rotation gates (RX, RY, RZ)
  * Configurable entangling gates (CNOT, CZ, CRX, XX)
  * Entanglement topologies (LINEAR, RING, FULL, BRICKWORK)
  * Parameter counting with hea_param_count()

Usage:
    python hea_options.py [--n-qubits N] [--depth L]

References:
    Kandala, A. et al. (2017). "Hardware-efficient variational quantum
    eigensolver for small molecules and quantum magnets."
    Nature 549, 242-246. https://doi.org/10.1038/nature23879

[doc-require: ]
"""

import argparse
import sys

import numpy as np

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from uniqc import Circuit
from uniqc.simulator import Simulator
from uniqc.algorithms.core.ansatz import (
    hea,
    hea_param_count,
    RotationGate,
    EntanglingGate,
    EntanglementTopology,
)


def _print_circuit_info(circuit, label):
    """Print circuit statistics."""
    print(f"\n  {label}:")
    print(f"    Qubits used: {circuit.max_qubit + 1}")
    print(f"    Gate count: {len(circuit.opcode_list)}")


def demo_rotation_gates(n_qubits=4, depth=2):
    """Demonstrate different rotation gate configurations."""
    print("=" * 60)
    print("Demo 1: Rotation Gate Configurations")
    print("=" * 60)

    # Default: RZ + RY (backward compatible)
    n_default = hea_param_count(n_qubits, depth, rotation_gates=["rz", "ry"])
    c_default = hea(n_qubits, depth, rotation_gates=["rz", "ry"])
    print(f"\n  Default (RZ + RY):")
    print(f"    Parameters: {n_default}")
    _print_circuit_info(c_default, "RZ+RY circuit")

    # RX only
    n_rx = hea_param_count(n_qubits, depth, rotation_gates=["rx"])
    c_rx = hea(n_qubits, depth, rotation_gates=["rx"])
    print(f"\n  RX only:")
    print(f"    Parameters: {n_rx}")
    _print_circuit_info(c_rx, "RX circuit")

    # RX + RY + RZ (full rotation)
    n_full = hea_param_count(n_qubits, depth, rotation_gates=["rx", "ry", "rz"])
    c_full = hea(n_qubits, depth, rotation_gates=["rx", "ry", "rz"])
    print(f"\n  RX + RY + RZ (full):")
    print(f"    Parameters: {n_full}")
    _print_circuit_info(c_full, "Full rotation circuit")

    # Verify all circuits produce valid statevectors
    sim = Simulator(backend_type="statevector")
    for label, c in [("RZ+RY", c_default), ("RX", c_rx), ("RX+RY+RZ", c_full)]:
        sv = sim.simulate_statevector(c.originir)
        norm = np.linalg.norm(sv)
        print(f"\n  {label} statevector norm: {norm:.10f}")


def demo_entangling_gates(n_qubits=4, depth=1):
    """Demonstrate different entangling gate configurations."""
    print("\n" + "=" * 60)
    print("Demo 2: Entangling Gate Configurations")
    print("=" * 60)

    # Non-parametric gates (0 extra params per edge)
    print("\n  Non-parametric gates:")
    for gate in ["cnot", "cz", "iswap"]:
        n = hea_param_count(n_qubits, depth, entangling_gate=gate, topology="ring")
        c = hea(n_qubits, depth, entangling_gate=gate, topology="ring")
        print(f"    {gate.upper():8s}: {n:3d} params")
        _print_circuit_info(c, f"{gate.upper()} circuit")

    # Parametric gates (extra params per edge)
    print("\n  Parametric gates (extra params per edge):")
    for gate in ["crx", "xx", "yy", "zz"]:
        n = hea_param_count(n_qubits, depth, entangling_gate=gate, topology="ring")
        c = hea(n_qubits, depth, entangling_gate=gate, topology="ring")
        print(f"    {gate.upper():8s}: {n:3d} params")
        _print_circuit_info(c, f"{gate.upper()} circuit")

    # Verify all circuits produce valid statevectors
    sim = Simulator(backend_type="statevector")
    for gate in ["cnot", "cz", "crx", "xx"]:
        c = hea(n_qubits, depth, entangling_gate=gate, topology="ring")
        sv = sim.simulate_statevector(c.originir)
        print(f"\n  {gate.upper()} statevector norm: {np.linalg.norm(sv):.10f}")


def demo_topologies(n_qubits=4, depth=1):
    """Demonstrate different entanglement topologies."""
    print("\n" + "=" * 60)
    print("Demo 3: Entanglement Topologies")
    print("=" * 60)

    for topo in ["linear", "ring", "full", "star", "brickwork"]:
        n = hea_param_count(n_qubits, depth, topology=topo)
        c = hea(n_qubits, depth, topology=topo)
        print(f"\n  {topo.upper():10s}:")
        print(f"    Parameters: {n}")
        _print_circuit_info(c, f"{topo.upper()} circuit")

    # Custom topology
    print("\n  CUSTOM (user-defined edges):")
    custom_edges = [(0, 1), (0, 2), (0, 3)]  # Star from qubit 0
    n = hea_param_count(n_qubits, depth, topology="custom", custom_edges=custom_edges)
    c = hea(n_qubits, depth, topology="custom", custom_edges=custom_edges)
    print(f"    Edges: {custom_edges}")
    print(f"    Parameters: {n}")
    _print_circuit_info(c, "Custom circuit")


def run_demo(n_qubits, depth):
    """Run all HEA configuration demos."""
    print(f"\n{'=' * 60}")
    print(f"HEA Configuration Demo (n_qubits={n_qubits}, depth={depth})")
    print(f"{'=' * 60}")

    demo_rotation_gates(n_qubits, depth)
    demo_entangling_gates(n_qubits, depth)
    demo_topologies(n_qubits, depth)

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="HEA Configuration Options Demo")
    parser.add_argument(
        "--n-qubits", type=int, default=4,
        help="Number of qubits (default: 4)"
    )
    parser.add_argument(
        "--depth", type=int, default=2,
        help="Ansatz depth/layers (default: 2)"
    )
    args = parser.parse_args()

    if args.n_qubits < 2:
        parser.error("--n-qubits must be at least 2")
    if args.depth < 0:
        parser.error("--depth must be non-negative")

    run_demo(args.n_qubits, args.depth)


if __name__ == "__main__":
    main()
