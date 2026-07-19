### Classical Shadow tomography — measurement example.

*Source*: ``examples/2_advanced/measurement/shadow_tomography.py``  
*Status*: **pass**

Demonstrates:
  * Using classical_shadow for efficient state characterisation
  * Computing shadow expectation values
  * Comparing shadow estimates with exact statevector

Usage:
    python shadow_tomography.py [--n-shots N] [--n-shadow N]

References:
    Huang, Kueng, Preskill (2020). "Predicting many properties of a quantum
    system from very few measurements." Nature Physics 16, 1050–1057.

**Source code**

```{literalinclude} ../../../examples/2_advanced/measurement/shadow_tomography.py
:language: python
```

**Stdout**

```text
Classical Shadow Tomography Demo
==================================================
  Shots per basis: 1000
  Shadow snapshots: 100

Circuit: Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2

Performing 100 shadow measurements...
  Collected 100 shadow snapshots

  ⟨Z₀⟩ estimate: 1.0200 (exact: 0.0)
  ⟨Z₀Z₁⟩ estimate: 1.0800 (exact: 1.0)
  ⟨X₀⟩ estimate: 0.9900 (exact: 1/√2 ≈ 0.707)

  Exact ⟨Z₀⟩ = 0.0000
  Exact ⟨Z₀Z₁⟩ = 1.0000

✓ Shadow estimation complete with 100 snapshots
```

