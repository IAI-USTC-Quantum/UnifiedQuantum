### Arbitrary state preparation via rotation — example.

*Source*: ``examples/2_advanced/state_preparation/rotation_prepare.py``  
*Status*: **pass**

Demonstrates:
  * Preparing specific target states using rotation_prepare
  * Bell state, GHZ state, and random state preparation
  * Verifying fidelity of prepared states

Usage:
    python rotation_prepare.py [--state TYPE]

References:
    Shende, Bullock, Markov (2006). "Synthesis of Quantum Logic Circuits."
    IEEE Transactions on CAD 25(6).

**Source code**

```{literalinclude} ../../../examples/2_advanced/state_preparation/rotation_prepare.py
:language: python
```

**Stdout**

```text
Rotation-Based State Preparation
==================================================

Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2
  Fidelity: 0.00000000
  |00⟩: +0.7071+0.0000j
  |01⟩: -0.0000+0.0000j
  |10⟩: +0.0000+0.0000j
  |11⟩: -0.7071+0.0000j

Circuit:
QINIT 2
CREG 0
RY q[1], (-1.5707963267948966)
RY q[0], (1.5707963267948966)
CNOT q[1], q[0]
RY q[0], (-1.5707963267948966)
CNOT q[1], q[0]
CNOT q[1], q[0]
CNOT q[1], q[0]
```

