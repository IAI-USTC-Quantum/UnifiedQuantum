### Quantum Phase Estimation (QPE) — complete example.

*Source*: ``examples/2_advanced/algorithms/qpe.py``  
*Status*: **not-executed**

Demonstrates:
  * QPE circuit construction with phase register + eigenstate register
  * Inverse Quantum Fourier Transform (QFTdagger)
  * Running QPE with UnifiedQuantum simulators
  * Using the measurement module to extract phase bits
  * Connecting the estimated phase to the eigenvalue

Usage:
    python qpe.py [--n-precision N] [--unitary TYPE] [--shots N]

References:
    Nielsen & Chuang, "Quantum Computation and Quantum Information", Chapter 5.
    Cleve et al. (1998), "Efficient Discrete Random Unitary Circuits for Approximating
    the Quantum Fourier Transform." https://arxiv.org/abs/quant-ph/9904026

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qpe.py
:language: python
```

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

