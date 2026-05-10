### Grover's search algorithm — complete example.

*Source*: ``examples/2_advanced/algorithms/grover.py``  
*Status*: **pass**

Demonstrates:
  * Oracle construction for an n-qubit Grover search
  * Diffusion operator (amplitude amplification)
  * Running the algorithm with UnifiedQuantum simulators
  * Using the measurement module for result analysis

Usage:
    python grover.py [--n-qubits N] [--marked-state STATE] [--shots N]

References:
    Grover, L. K. (1996). "A fast quantum mechanical algorithm
    for database search." STOC '96.
    https://arxiv.org/abs/quant-ph/9605043

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/grover.py
:language: python
```

**Stdout**

```text
 Grover's Search — 3 data qubits
 Marked state: 5 (101)
 Search space: 8 states

 Results (top 5 most probable states):
   |011⟩   25.8%
   |110⟩   25.7%
   |000⟩   25.0%
   |101⟩   23.4% ← TARGET

 Target probability: 23.4%
 Expected (ideal): ~95.0% (after optimal iterations)

  ✓ Run complete.
```

