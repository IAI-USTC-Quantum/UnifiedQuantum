### Variational Quantum Eigensolver (VQE) — complete example.

*Source*: ``examples/2_advanced/algorithms/vqe.py``  
*Status*: **not-executed**

Demonstrates:
  * Building a UCCSD ansatz for molecular Hamiltonians
  * Computing energy expectation values via Pauli decomposition
  * Classical optimisation loop (COBYLA) to find ground-state energy
  * Using uniqc ansatz + measurement modules

Usage:
    python vqe.py [--molecule NAME] [--maxiter N]

References:
    Peruzzo et al. (2014). "A variational eigenvalue solver on a photonic
    quantum processor." Nature Communications 5, 4213.
    https://arxiv.org/abs/1304.3061

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/vqe.py
:language: python
```

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

