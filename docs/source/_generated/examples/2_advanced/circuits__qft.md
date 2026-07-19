### Quantum Fourier Transform (QFT) — complete example.

*Source*: ``examples/2_advanced/circuits/qft.py``  
*Status*: **pass**

Demonstrates:
  * Building a QFT circuit using qft_circuit
  * Preparing a computational basis state as input
  * Verifying QFT output via state-vector inspection
  * Running with Simulator for shot-based sampling

Usage:
    python qft.py [--n-qubits N] [--input-state STATE] [--shots N]

References:
    Nielsen, M. A. & Chuang, I. L. (2010). "Quantum Computation and
    Quantum Information." Cambridge University Press, Section 5.1.

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/qft.py
:language: python
```

**Stdout**

```text
 Quantum Fourier Transform — 3 qubits
 Input state: |5⟩ = |101⟩

 Results (top 8):
   |101⟩   12.9%
   |111⟩   12.8%
   |100⟩   12.8%
   |110⟩   12.6%
   |010⟩   12.6%
   |000⟩   12.5%
   |011⟩   12.1%
   |001⟩   11.7%

 Ideal: each basis state has probability 12.50%
 (QFT of |j⟩ produces equal-amplitude superposition with phase encoding)

  ✓ Run complete.
```

