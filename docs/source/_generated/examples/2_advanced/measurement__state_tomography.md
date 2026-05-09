### Full quantum state tomography — measurement example.

*Source*: ``examples/2_advanced/measurement/state_tomography.py``  
*Status*: **pass**

Demonstrates:
  * Reconstructing the density matrix via state tomography
  * Computing fidelity with the target state
  * Comparing tomography result with exact statevector

Usage:
    python state_tomography.py [--n-shots N]

References:
    James et al. (2001). "Measurement of qubits." Physical Review A 64, 052312.

**Source code**

```{literalinclude} ../../../examples/2_advanced/measurement/state_tomography.py
:language: python
```

**Stdout**

```text
Full State Tomography Demo
==================================================
  Shots per basis: 2000

Circuit: (|00⟩ + i|11⟩)/√2

Running tomography (3^2 = 9 measurement bases for 2 qubits)...
==================================================
State Tomography Summary  (label=ρ_tomo, n_qubits=2)
==================================================

Eigenvalues (largest first):
  λ_0 =  1.866025
  λ_1 =  0.133975
  λ_2 = -0.500000
  λ_3 = -0.500000

Purity  Tr(ρ²) = 4.000000  (mixed)
Trace   Tr(ρ)   = 1.000000

Fidelity F(ρ, σ) = 1.000000
==================================================


Tomography complete.
  Density matrix shape: (4, 4)
  Fidelity ⟨ψ|ρ|ψ⟩: 1.000000
  Trace of reconstructed ρ: 1.000000

  Populations:
    |00⟩: exact=0.5000, tomography=1.0000
    |01⟩: exact=0.0000, tomography=0.0000
    |10⟩: exact=0.0000, tomography=0.0000
    |11⟩: exact=0.5000, tomography=0.0000
```

