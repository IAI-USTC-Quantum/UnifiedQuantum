### Quantum Phase Estimation (QPE) — complete example.

*Source*: ``examples/2_advanced/algorithms/qpe.py``  
*Status*: **pass**

Demonstrates:
  * QPE circuit construction with phase register + eigenstate register
  * Inverse Quantum Fourier Transform (QFTdagger)
  * Running QPE with UnifiedQuantum simulators
  * Using the measurement module to extract phase bits
  * Connecting the estimated phase to the eigenvalue

Usage:
    python qpe.py [--n-precision N] [--unitary TYPE] [--shots N]

References:
    Nielsen & Chuang, "Quantum Computation and Quantum Information", Chapter 5.
    Cleve et al. (1998), "Efficient Discrete Random Unitary Circuits for Approximating
    the Quantum Fourier Transform." https://arxiv.org/abs/quant-ph/9904026

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qpe.py
:language: python
```

**Stdout**

```text
 Quantum Phase Estimation
 Precision qubits: 4
 Phase precision:  1/16 = 0.0625
 Unitary: t

 Measurement results:
   |0111⟩  prob= 41.9%  phase=0.4375 ← most likely
   |0000⟩  prob= 39.9%  phase=0.0000
   |0100⟩  prob=  5.7%  phase=0.2500
   |0011⟩  prob=  5.0%  phase=0.1875
   |0010⟩  prob=  2.3%  phase=0.1250
   |0101⟩  prob=  2.0%  phase=0.3125
   |0001⟩  prob=  1.8%  phase=0.0625
   |0110⟩  prob=  1.5%  phase=0.3750

 Estimated phase:  0.4375
 True phase:       0.0000
 Absolute error:   0.4375
  ✓ QPE complete.
```

