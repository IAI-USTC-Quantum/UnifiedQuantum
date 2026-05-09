### Grover's search algorithm — complete example.

*Source*: ``examples/2_advanced/algorithms/grover.py``  
*Status*: **not-executed**

Demonstrates:
  * Oracle construction for an n-qubit Grover search
  * Diffusion operator (amplitude amplification)
  * Running the algorithm with UnifiedQuantum simulators
  * Using the measurement module for result analysis

Usage:
    python grover.py [--n-qubits N] [--marked-state STATE] [--shots N]

References:
    Grover, L. K. (1996). "A fast quantum mechanical algorithm
    for database search." STOC '96.
    https://arxiv.org/abs/quant-ph/9605043

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/grover.py
:language: python
```

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

