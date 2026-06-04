### Quantum Amplitude Estimation (QAE) — complete example.

*Source*: ``examples/2_advanced/circuits/amplitude_estimation.py``  
*Status*: **pass**

Demonstrates:
  * Building a simple oracle for amplitude estimation
  * Running QAE to estimate the probability of "good" states
  * Using the amplitude_estimation_result function to extract the estimate

Usage:
    python amplitude_estimation.py [--n-qubits N] [--n-eval-qubits M] [--shots N]

References:
    Brassard, G., Høyer, P., Mosca, M. & Tapp, A. (2002).
    "Quantum Amplitude Amplification and Estimation."
    AMS Contemporary Mathematics, 305, 53–74.

**Source code**

```{literalinclude} ../../../examples/2_advanced/circuits/amplitude_estimation.py
:language: python
```

**Stdout**

```text
 Quantum Amplitude Estimation
 Search qubits: 2, Eval qubits: 3
 Marked state: |00⟩

 Estimated probability: 0.853553
 True probability:      0.250000
 Error:                 0.603553

 Measurement counts (eval register):
   |000⟩: 4
   |001⟩: 354
   |010⟩: 141
   |011⟩: 543
   |100⟩: 415
   |101⟩: 544
   |110⟩: 1230
   |111⟩: 865
```

