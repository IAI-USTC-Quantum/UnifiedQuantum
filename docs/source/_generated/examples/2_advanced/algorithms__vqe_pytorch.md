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

  Iter   20 | Energy: -0.088256
  Iter   40 | Energy: -0.422964
  Iter   60 | Energy: -0.602616
  Iter   80 | Energy: -0.849158
  Iter  100 | Energy: -0.873256

Final energy: -0.873256 Ha
Optimal params: [0.24899430572986603, 1.5495481491088867, 0.5918601155281067, -1.380683183670044] ...

Expected: ~-1.10 Ha (simplified Hamiltonian)
```

