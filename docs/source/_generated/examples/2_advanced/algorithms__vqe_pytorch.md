### VQE for H2 molecule using TorchQuantum backend with native PyTorch autograd.

*Source*: ``examples/2_advanced/algorithms/vqe_pytorch.py``  
*Status*: **pass**

Demonstrates variational quantum eigensolver with Adam optimizer,
using TorchQuantum's differentiable simulation (no parameter-shift rule).

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/vqe_pytorch.py
:language: python
```

**Stdout**

```text
============================================================
VQE for H2 Molecule — TorchQuantum Backend
============================================================

Molecule: H2 (STO-3G, 4 qubits)
Nuclear repulsion: 0.7149
Pauli terms: 15
Ansatz: HEA depth=2, params=16
Exact FCI energy: -1.137274 Ha

  Iter   20 | Energy: -0.204432
  Iter   40 | Energy: -0.453499
  Iter   60 | Energy: -0.857957
  Iter   80 | Energy: -0.868904
  Iter  100 | Energy: -0.873922

Final energy: -0.873922 Ha
Optimal params: [0.1613229513168335, 1.5576759576797485, 0.23028449714183807, -1.2020018100738525] ...

Expected: ~-1.10 Ha (simplified Hamiltonian)
```

