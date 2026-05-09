### Deutsch-Jozsa algorithm — complete example.

*Source*: ``examples/2_advanced/circuits/deutsch-jozsa.py``  
*Status*: **pass**

Demonstrates:
  * Building constant and balanced oracles
  * Running the Deutsch-Jozsa algorithm
  * Distinguishing constant from balanced functions with a single query

Usage:
    python deutsch-jozsa.py [--n-qubits N] [--oracle-type TYPE] [--shots N]

References:
    Deutsch, D. & Jozsa, R. (1992). "Rapid solutions of problems by
    quantum computation." Proceedings of the Royal Society of London A.

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/deutsch-jozsa.py
:language: python
```

**Stdout**

```text
 Deutsch-Jozsa Algorithm — 3 data qubits
 Oracle type: balanced

 Results (top outcomes):
   |000⟩  100.0% ← all zeros

  → CONSTANT function (all measurements = |000⟩)

  ✓ Run complete.
```

