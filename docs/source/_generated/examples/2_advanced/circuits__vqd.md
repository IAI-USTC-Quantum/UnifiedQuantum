### Variational Quantum Deflation (VQD) — complete example.

*Source*: ``examples/2_advanced/circuits/vqd.py``  
*Status*: **pass**

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

**Stdout**

```text
=== VQD Example: H = Z₀ + ... + Z_{n-1} on 2 qubits ===
n_layers=2, penalty=10.0, n_params=4

Exact eigenvalues: [-2.  0.  0.  2.]

--- Step 1: VQE (ground state) ---
VQE ground state energy: -2.000000  (exact: -2.000000)

--- Step 2: VQD (first excited state) ---
VQD first excited state energy: 0.000000  (exact: 0.000000)
Overlap with ground state: 0.000000

✓ Run complete.
```

