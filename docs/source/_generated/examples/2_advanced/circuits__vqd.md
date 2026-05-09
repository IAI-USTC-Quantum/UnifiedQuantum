### Variational Quantum Deflation (VQD) — complete example.

*Source*: ``examples/2_advanced/circuits/vqd.py``  
*Status*: **not-executed**

Demonstrates:
  * Finding the ground state of H = Z₀ + Z₁ using VQE (layer 0)
  * Finding the first excited state using VQD with overlap penalty
  * Using scipy.optimize.minimize as the classical optimiser

Usage:
    python vqd.py [--n-qubits N] [--n-layers L] [--penalty B]

References:
    Higgott, O., Wang, D. & Brierley, S. (2019).
    "Variational Quantum Computation of Excited States."
    Quantum 3, 156.

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/vqd.py
:language: python
```

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

