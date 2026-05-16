### QAOA Variants -- XY Mixer, Warm-Start, and MA-QAOA.

*Source*: ``examples/2_advanced/algorithms/qaoa_variants.py``  
*Status*: **pass**

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

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qaoa_variants.py
:language: python
```

**Stdout**

```text

============================================================
QAOA Variants Demo (p=2, nodes=4)
============================================================
============================================================
Demo 1: XY Mixer
============================================================

  Graph: Ring with 4 nodes
  Edges: [(0, 1), (1, 2), (2, 3), (3, 0)]

  Standard QAOA (X mixer):
    Parameters: betas=2, gammas=2 (total: 4)

  Standard circuit:
    Qubits used: 4
    Gate count: 52

  XY Mixer QAOA:
    Parameters: betas=2, gammas=2 (total: 4)
    Note: XY mixer preserves excitation number

  XY mixer circuit:
    Qubits used: 4
    Gate count: 40

  Standard norm: 1.0000000000
  XY mixer norm: 1.0000000000

============================================================
Demo 2: Warm-Start QAOA
============================================================

  Graph: Line with 4 nodes
  Edges: [(0, 1), (1, 2), (2, 3)]

  Standard QAOA (uniform superposition):
    Initial: Hadamards on all qubits

  Standard circuit:
    Qubits used: 4
    Gate count: 46

  Warm-Start QAOA (greedy solution):
    Initial: |0101...> (alternating pattern)

  Warm-start circuit:
    Qubits used: 4
    Gate count: 44

  Comparison:
    Standard: 46 gates
    Warm-start: 44 gates

  Standard norm: 1.0000000000
  Warm-start norm: 1.0000000000

============================================================
Demo 3: MA-QAOA (Multi-Angle)
============================================================

  Graph: Triangle
  Edges (Hamiltonian terms): 3

  Standard QAOA:
    Parameters: 4 (p betas + p gammas)

  MA-QAOA:
    Parameters: 14 (3 terms x 2 layers gammas + 4 qubits x 2 layers betas)
    Improvement: 10 extra parameters

  Standard circuit:
    Qubits used: 3
    Gate count: 39

  MA-QAOA circuit:
    Qubits used: 3
    Gate count: 39

  Standard norm: 1.0000000000
  MA-QAOA norm: 1.0000000000

============================================================
Demo Complete
============================================================
```

