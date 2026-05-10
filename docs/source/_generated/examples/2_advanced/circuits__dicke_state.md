### Dicke state preparation circuit — example.

*Source*: ``examples/2_advanced/circuits/dicke_state.py``  
*Status*: **pass**

Demonstrates the dicke_state_circuit building block for preparing
Dicke states |D(n,k)⟩ — equal superpositions of all n-bit strings
with exactly k ones.

Usage:
    python dicke_state.py [--n-qubits N] [--k K] [--shots N]

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/dicke_state.py
:language: python
```

**Stdout**

```text
Dicke State |D(4,2)⟩ Preparation
Expected: 6 basis states, each with probability 0.166667

Measured probability distribution (shots=8192):
  State          Measured   Weight     Theory
  ------------ ---------- -------- ----------
  |0011⟩    0.163940      2✓    0.166667
  |0101⟩    0.172852      2✓    0.166667
  |0110⟩    0.165283      2✓    0.166667
  |1001⟩    0.163330      2✓    0.166667
  |1010⟩    0.170044      2✓    0.166667
  |1100⟩    0.164551      2✓    0.166667

Total weight on Hamming-weight-2 subspace: 1.000000 (expected: 1.0)
```

