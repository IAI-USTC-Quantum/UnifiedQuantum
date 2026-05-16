#!/usr/bin/env python
"""Symbolic Parameters for Variational Circuits.

Demonstrates:
  * Auto-generation of Parameters when params=None
  * Manual binding workflow with Parameters objects
  * Pre-computing parameter counts with hea_param_count()
  * Symbolic arithmetic with Parameter objects

Usage:
    python parameters_demo.py

[doc-require: ]
"""

import sys

import numpy as np

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from uniqc import Circuit
from uniqc.simulator import Simulator
from uniqc.algorithms.core.ansatz import hea, hea_param_count, qaoa_ansatz, hva
from uniqc.circuit_builder.parameter import Parameter, Parameters


def demo_auto_generation():
    """Demonstrate auto-generation of Parameters when params=None."""
    print("=" * 60)
    print("Demo 1: Auto-Generated Parameters")
    print("=" * 60)

    # HEA without params - auto-generates Parameters
    c = hea(n_qubits=4, depth=2)

    print(f"\n  Calling hea(n_qubits=4, depth=2) without params:")
    print(f"\n  Circuit._params type: {type(c._params).__name__}")
    print(f"  Parameters name: {c._params.name}")
    print(f"  Parameters count: {len(c._params)}")
    print(f"  Parameter names: {c._params.names}")

    # Show first few values
    values = [c._params[i].evaluate() for i in range(min(4, len(c._params)))]
    print(f"  First 4 values: {[f'{v:.4f}' for v in values]}")

    # QAOA auto-generates separate betas and gammas
    H = [("Z0Z1", 1.0), ("Z1Z2", 0.5)]
    c_qaoa = qaoa_ansatz(H, p=2)

    print(f"\n  QAOA auto-generated parameters:")
    print(f"    betas: {c_qaoa._params['betas'].name}, len={len(c_qaoa._params['betas'])}")
    print(f"    gammas: {c_qaoa._params['gammas'].name}, len={len(c_qaoa._params['gammas'])}")


def demo_hea_param_count():
    """Demonstrate pre-computing parameter counts."""
    print("\n" + "=" * 60)
    print("Demo 2: Pre-computing Parameter Counts")
    print("=" * 60)

    n_qubits = 4
    depth = 2

    print(f"\n  For n_qubits={n_qubits}, depth={depth}:")
    print(f"\n  {'Configuration':<30} {'Parameters':<12}")
    print(f"  {'-'*42}")

    configs = [
        ("RZ+RY (default)", dict(rotation_gates=["rz", "ry"])),
        ("RX only", dict(rotation_gates=["rx"])),
        ("RX+RY+RZ", dict(rotation_gates=["rx", "ry", "rz"])),
        ("CNOT (default)", dict(entangling_gate="cnot")),
        ("CZ", dict(entangling_gate="cz")),
        ("XX (parametric)", dict(entangling_gate="xx", topology="ring")),
        ("Linear topology", dict(topology="linear")),
        ("Full topology", dict(topology="full")),
    ]

    for label, kwargs in configs:
        count = hea_param_count(n_qubits, depth, **kwargs)
        print(f"  {label:<30} {count:<12}")

    print(f"\n  Use hea_param_count() to determine array size before building:")
    print(f"\n  n_params = hea_param_count(4, 2, rotation_gates=['rx', 'ry'])")
    n_params = hea_param_count(4, 2, rotation_gates=["rx", "ry"])
    print(f"  # n_params = {n_params}")
    print(f"  params = np.zeros(n_params)")


def demo_manual_binding():
    """Demonstrate manual Parameters binding workflow."""
    print("\n" + "=" * 60)
    print("Demo 3: Manual Parameters Binding")
    print("=" * 60)

    # Step 1: Determine parameter count
    n_qubits = 4
    depth = 2
    n_params = hea_param_count(n_qubits, depth)
    print(f"\n  Step 1: Determine parameter count")
    print(f"    n_params = hea_param_count({n_qubits}, {depth}) = {n_params}")

    # Step 2: Create Parameters object
    print(f"\n  Step 2: Create Parameters object")
    params = Parameters("my_ansatz_params", size=n_params)
    print(f"    params = Parameters('my_ansatz_params', size={n_params})")
    print(f"    names: {params.names}")

    # Step 3: Bind values
    print(f"\n  Step 3: Bind values")
    values = [0.1 * (i + 1) for i in range(n_params)]
    params.bind(values)
    print(f"    params.bind([0.1, 0.2, ..., {values[-1]:.1f}])  # {n_params} values")
    print(f"    Bound: {params[0].is_bound}")

    # Step 4: Use in circuit
    print(f"\n  Step 4: Build circuit")
    c = hea(n_qubits, depth, params=params)
    print(f"    circuit = hea({n_qubits}, {depth}, params=params)")
    print(f"    circuit._params is params: {c._params is params}")

    # Step 5: Verify statevector
    sim = Simulator(backend_type="statevector")
    sv = sim.simulate_statevector(c.originir)
    print(f"\n  Step 5: Verify circuit")
    print(f"    Statevector norm: {np.linalg.norm(sv):.10f}")

    # Step 6: Rebind for new optimization run
    print(f"\n  Step 6: Rebind for new optimization")
    new_values = [0.5] * n_params
    params.bind(new_values)
    c2 = hea(n_qubits, depth, params=params)
    print(f"    params.bind([0.5, 0.5, ..., 0.5])  # {n_params} values")
    print(f"    Rebuilt circuit successfully")


def demo_symbolic_arithmetic():
    """Demonstrate symbolic arithmetic with Parameter objects."""
    print("\n" + "=" * 60)
    print("Demo 4: Symbolic Arithmetic")
    print("=" * 60)

    # Create parameters
    theta = Parameter("theta")
    phi = Parameter("phi")

    print(f"\n  Creating parameters:")
    print(f"    theta = Parameter('theta')")
    print(f"    phi = Parameter('phi')")

    # Arithmetic operations create sympy expressions
    expr1 = theta + phi / 2
    expr2 = theta * 2 - phi
    expr3 = -theta

    print(f"\n  Arithmetic expressions (sympy):")
    print(f"    theta + phi/2 = {expr1}")
    print(f"    theta*2 - phi = {expr2}")
    print(f"    -theta = {expr3}")

    # Evaluate with specific values using substitution
    theta.bind(1.0)
    phi.bind(2.0)

    print(f"\n  After binding theta=1.0, phi=2.0:")
    # Use subs to substitute the symbol values
    subs_dict = {theta.symbol: 1.0, phi.symbol: 2.0}
    print(f"    theta + phi/2 = {float(expr1.subs(subs_dict).evalf())}")
    print(f"    theta*2 - phi = {float(expr2.subs(subs_dict).evalf())}")

    # Show that Parameters array works similarly
    print(f"\n  Parameters array:")
    params = Parameters("alpha", size=3)
    params.bind([0.5, 1.0, 1.5])
    for i in range(3):
        print(f"    params[{i}].name = '{params[i].name}', value = {params[i].evaluate()}")


def run_demo():
    """Run all parameter demos."""
    print("\n" + "=" * 60)
    print("Symbolic Parameters Demo")
    print("=" * 60)

    demo_auto_generation()
    demo_hea_param_count()
    demo_manual_binding()
    demo_symbolic_arithmetic()

    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


def main():
    run_demo()


if __name__ == "__main__":
    main()
