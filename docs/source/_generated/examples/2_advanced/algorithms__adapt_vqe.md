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
  Best operator: YI, gradient = 1.00000000
Iter 2: E = -0.50000000, n_operators = 1
  Best operator: YI, gradient = 1.00000000
Iter 3: E = -0.50000000, n_operators = 2
  Best operator: YI, gradient = 1.00000000
Iter 4: E = -0.49998990, n_operators = 3
  Best operator: YI, gradient = 0.99998990
Iter 5: E = -0.50000000, n_operators = 4
  Best operator: IY, gradient = 1.00000000
Iter 6: E = -0.50000000, n_operators = 5
  Best operator: YI, gradient = 1.00000000
Iter 7: E = -0.49960312, n_operators = 6
  Best operator: YI, gradient = 0.99960312
Iter 8: E = -0.50000000, n_operators = 7
  Best operator: YI, gradient = 1.00000000
Iter 9: E = -0.50000000, n_operators = 8
  Best operator: YI, gradient = 1.00000000
Iter 10: E = -0.50000000, n_operators = 9
  Best operator: YI, gradient = 1.00000000
------------------------------------------------------------
Final energy: -0.50000000
Selected 10 operators

============================================================
ADAPT-VQE Results:
  Energy: -0.50000000
  Iterations: 10
  Converged: False
  Selected operators: 10
    YI (coeff=1.00)
    YI (coeff=1.00)
    YI (coeff=1.00)
    YI (coeff=1.00)
    IY (coeff=1.00)
    YI (coeff=1.00)
    YI (coeff=1.00)
    YI (coeff=1.00)
    YI (coeff=1.00)
    YI (coeff=1.00)

Comparison with standard VQE (HEA):
  VQE Energy: -0.50000000
  VQE Success: True
```

