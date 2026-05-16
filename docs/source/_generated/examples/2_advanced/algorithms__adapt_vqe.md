### ADAPT-VQE Example.

*Source*: ``examples/2_advanced/algorithms/adapt_vqe.py``  
*Status*: **pass**

This script demonstrates how to implement ADAPT-VQE (Adaptively Parametrised
Variational Quantum Eigensolver) using the existing algorithm components in uniqc.

ADAPT-VQE iteratively builds an ansatz by selecting operators from a pool
based on gradient magnitude, rather than using a fixed ansatz structure.

This is an EXAMPLE script, not a reusable algorithm module. Users can copy and
adapt this code for their specific use cases.

References:
- Grimsley et al., "Adaptively parametric ansatz" (2019)

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/adapt_vqe.py
:language: python
```

**Stdout**

```text
============================================================
ADAPT-VQE Example: 2-Qubit Hamiltonian
============================================================
Using 5 operators from minimal pool

ADAPT-VQE starting with 5 operators in pool
Hamiltonian: [('ZZ', -1.0), ('II', 0.5)]
------------------------------------------------------------
Iter 1: E = 0.00000000, n_operators = 0
  No valid gradients, stopping.
------------------------------------------------------------
Final energy: 0.00000000
Selected 0 operators

============================================================
ADAPT-VQE Results:
  Energy: 0.00000000
  Iterations: 1
  Converged: False
  Selected operators: 0

Comparison with standard VQE (HEA):
  VQE Energy: -0.50000000
  VQE Success: True
```

