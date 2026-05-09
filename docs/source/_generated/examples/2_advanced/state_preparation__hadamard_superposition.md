### Hadamard superposition — state preparation example.

*Source*: ``examples/2_advanced/state_preparation/hadamard_superposition.py``  
*Status*: **pass**

Demonstrates:
  * Creating uniform superposition states with hadamard_superposition
  * Verifying state correctness via statevector simulation
  * Visualising the probability distribution

Usage:
    python hadamard_superposition.py [--n-qubits N]

References:
    Nielsen & Chuang (2010). "Quantum Computation and Quantum Information."
    Chapter 1.

**Source code**

```{literalinclude} ../../../examples/2_advanced/state_preparation/hadamard_superposition.py
:language: python
```

**Stdout**

```text
Hadamard Superposition Demo (3 qubits)
==================================================

State vector (8 amplitudes):
  |000⟩: +0.3536 (expected: +0.3536)
  |001⟩: +0.3536 (expected: +0.3536)
  |010⟩: +0.3536 (expected: +0.3536)
  |011⟩: +0.3536 (expected: +0.3536)
  |100⟩: +0.3536 (expected: +0.3536)
  |101⟩: +0.3536 (expected: +0.3536)
  |110⟩: +0.3536 (expected: +0.3536)
  |111⟩: +0.3536 (expected: +0.3536)

Probabilities:
  |000⟩: 0.1250 ████
  |001⟩: 0.1250 ████
  |010⟩: 0.1250 ████
  |011⟩: 0.1250 ████
  |100⟩: 0.1250 ████
  |101⟩: 0.1250 ████
  |110⟩: 0.1250 ████
  |111⟩: 0.1250 ████

All amplitudes equal? True
Total probability: 1.000000

--- Subset: qubits [0, 2] only ---
  |000⟩: 0.2500
  |001⟩: 0.2500
  |100⟩: 0.2500
  |101⟩: 0.2500
```

