### Hamiltonian Variational Ansatz (HVA) -- complete example.

*Source*: ``examples/2_advanced/algorithms/hva_example.py``  
*Status*: **pass**

Demonstrates:
  * Building HVA with commuting Hamiltonian groups
  * Hartree-Fock initial state preparation
  * Energy evaluation and optimization

Usage:
    python hva_example.py [--p-layers L] [--n-iterations N]

References:
    Wecker, D. et al. (2015). "Hackett, and A. Aspuru-Guzik,
    Progress toward practical quantum variational algorithms."
    Phys. Rev. A 92, 060303.

    Kivlichan, I.D. et al. (2018). "Quantum Simulation of Electronic
    Structure with Linear Depth and Connectivity."
    Phys. Rev. Lett. 120, 110501.

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/hva_example.py
:language: python
```

**Stdout**

```text

============================================================
HVA Example (p=2, iterations=20)
============================================================
============================================================
Demo 1: Basic HVA Construction
============================================================

  Hamiltonian groups:
    Group 1 (hopping): [('X0X1', 1.0), ('Y0Y1', 1.0)]
    Group 2 (interaction): [('Z0Z1', 0.5)]

  HVA configuration:
    Layers (p): 2
    Groups: 2
    Parameters: 4 (2 groups x 2 layers)

  HVA circuit:
    Qubits used: 2
    Gate count: 42

  Statevector norm: 1.0000000000

============================================================
Demo 2: HVA with Hartree-Fock Initial State
============================================================

  Hamiltonian groups: 3 groups
    Group 1: X hopping
    Group 2: Y hopping
    Group 3: ZZ interactions

  Without Hartree-Fock:
    Initial state: |0000>

  Circuit:
    Qubits used: 3
    Gate count: 84

  With Hartree-Fock:
    Initial state: |1100>

  Circuit:
    Qubits used: 3
    Gate count: 86

  Without HF norm: 1.0000000000
  With HF norm: 1.0000000000

============================================================
Demo 3: HVA Energy Optimization
============================================================

  Hamiltonian: H = -Z0Z1 + 0.5*I
  Expected ground state: |00> or |11>
  Expected energy: -0.5

  Optimization (coordinate descent):
    Iter  0: E = -0.500000
    Iter  5: E = -0.500000
    Iter 10: E = -0.500000
    Iter 15: E = -0.500000

  Final energy: -0.500000
  Expected:     -0.500000
  Accuracy:     0.000000

============================================================
Demo Complete
============================================================
```

