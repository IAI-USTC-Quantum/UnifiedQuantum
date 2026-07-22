### Grover's search using the public uniqc API.

*Source*: ``examples/2_advanced/circuits/grover_oracle.py``  
*Status*: **pass**

Demonstrates the full Grover search pipeline using root-level imports.

Usage:
    python examples/circuits/grover_oracle.py [--n-qubits N] [--marked-state STATE] [--shots N]

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/grover_oracle.py
:language: python
```

**Stdout**

```text
  Grover's Search — 3 data qubits
  Marked state: 5 (101)
  Search space: 8 states

  Iterations: 2
  Results (top 5):
    |101⟩   95.1% ← TARGET
    |010⟩    0.8%
    |111⟩    0.8%
    |100⟩    0.8%
    |110⟩    0.8%

  Target probability: 95.1%
  ✓ Done.
```

