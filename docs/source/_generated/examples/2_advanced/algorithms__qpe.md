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
   |0000⟩  prob= 41.5%  phase=0.0000 ← most likely
   |0111⟩  prob= 40.3%  phase=0.4375
   |0100⟩  prob=  5.4%  phase=0.2500
   |0011⟩  prob=  5.2%  phase=0.1875
   |0010⟩  prob=  2.7%  phase=0.1250
   |0101⟩  prob=  1.8%  phase=0.3125
   |0110⟩  prob=  1.6%  phase=0.3750
   |0001⟩  prob=  1.4%  phase=0.0625

 Estimated phase:  0.0000
 True phase:       0.0000
 Absolute error:   0.0000
  ✓ QPE complete.
```

