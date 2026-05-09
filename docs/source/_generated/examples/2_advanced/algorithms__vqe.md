### Variational Quantum Eigensolver (VQE) — complete example.

*Source*: ``examples/2_advanced/algorithms/vqe.py``  
*Status*: **pass**

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

**Stdout**

```text
VQE for H2
  Qubits: 4, Electrons: 2
  UCCSD parameters: 5 (4 singles + 1 doubles)
  Hamiltonian terms: 13
  Nuclear repulsion: 0.7200 Ha

  Iter   0: E = -0.584500 Ha
  Iter  10: E = -0.584500 Ha

  Final energy: -0.584500 Ha
  Parameters: [ 0.   0.   0.   0.  -0.1]
  Exact FCI:   -1.137274 Ha
```

