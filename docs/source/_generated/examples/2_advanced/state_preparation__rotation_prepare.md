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
  Fidelity: 1.00000000
  |00⟩: +0.0000-0.7071j
  |01⟩: -0.0000-0.0000j
  |10⟩: -0.0000+0.0000j
  |11⟩: +0.0000-0.7071j

Circuit:
QINIT 2
CREG 0
I q[0]
I q[1]
U3 q[0], (1.5707963267948966, 1.5707963267948966, -1.1780972450961729)
U3 q[1], (2.3561944901923453, 1.5707963267948966, 2.7488935718910685)
CNOT q[0], q[1]
U3 q[0], (2.356194490192344, -3.141592653589793, -1.5707963267948966)
U3 q[1], (1.717771517458402, 2.100699116543823, -2.100699116543823)
CNOT q[0], q[1]
U3 q[0], (1.5707963267948963, 1.1780972450961738, -3.141592653589793)
U3 q[1], (0.7853981633974484, 0.39269908169872414, 1.5707963267948966)
```

