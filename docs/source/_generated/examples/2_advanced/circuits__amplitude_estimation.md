### Quantum Amplitude Estimation (QAE) — complete example.

*Source*: ``examples/2_advanced/circuits/amplitude_estimation.py``  
*Status*: **not-executed**

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

:::{note}
Listed for reference; not executed during the docs build (``[doc-skip-execute]``).
:::

