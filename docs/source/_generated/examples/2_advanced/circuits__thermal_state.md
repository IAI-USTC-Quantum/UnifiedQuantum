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
  |000⟩    0.684082   0.683325
  |001⟩    0.093994   0.092478
  |010⟩    0.092407   0.092478
  |011⟩    0.010254   0.012516
  |100⟩    0.090942   0.092478
  |101⟩    0.012939   0.012516
  |110⟩    0.013062   0.012516
  |111⟩    0.002319   0.001694
```

