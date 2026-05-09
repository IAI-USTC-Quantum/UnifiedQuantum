### Quantum Approximate Optimization Algorithm (QAOA) — complete example.

*Source*: ``examples/2_advanced/algorithms/qaoa.py``  
*Status*: **not-executed**

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

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

