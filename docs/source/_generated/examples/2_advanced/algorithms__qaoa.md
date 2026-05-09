### Quantum Approximate Optimization Algorithm (QAOA) — complete example.

*Source*: ``examples/2_advanced/algorithms/qaoa.py``  
*Status*: **pass**

Demonstrates:
  * Building a QAOA ansatz for MaxCut
  * Evaluating the cost function via Pauli measurements
  * Classical optimisation to find approximate solutions
  * Using uniqc ansatz + measurement modules

Usage:
    python qaoa.py [--p LAYERS] [--maxiter N] [--graph FILE]

References:
    Farhi, E. et al. (2014). "A Quantum Approximate Optimization Algorithm."
    arXiv:1411.4028.

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qaoa.py
:language: python
```

**Stdout**

```text
QAOA for MaxCut
  Graph: 3 edges, 3 nodes
  Layers (p): 2
  Max possible cut: 3

  Iter   0: cut ≈ 1.608
  Iter  20: cut ≈ 2.000

  Best cut value: 2.000 / 3
  Approximation ratio: 0.667
```

