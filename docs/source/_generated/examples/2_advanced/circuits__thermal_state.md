### Thermal state preparation circuit — example.

*Source*: ``examples/2_advanced/circuits/thermal_state.py``  
*Status*: **pass**

Demonstrates the thermal_state_circuit building block for preparing
thermal (Gibbs) states of H = Σ Z_i at various inverse temperatures β.

Usage:
    python thermal_state.py [--n-qubits N] [--beta BETA] [--shots N]

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/thermal_state.py
:language: python
```

**Stdout**

```text
Thermal State Preparation — 3 qubits, β = 1.0
Single-qubit probabilities: p₀ = 0.880797, p₁ = 0.119203

Measured probability distribution (shots=8192):
  State          Measured     Theory
  ------------ ---------- ----------
  |000⟩    0.685059   0.683325
  |001⟩    0.089355   0.092478
  |010⟩    0.090698   0.092478
  |011⟩    0.013184   0.012516
  |100⟩    0.093628   0.092478
  |101⟩    0.013428   0.012516
  |110⟩    0.012939   0.012516
  |111⟩    0.001709   0.001694
```

