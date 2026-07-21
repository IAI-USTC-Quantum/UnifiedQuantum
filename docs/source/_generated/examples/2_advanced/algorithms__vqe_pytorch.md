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

  Iter   20 | Energy: -0.623427
  Iter   40 | Energy: -0.852304
  Iter   60 | Energy: -0.873820
  Iter   80 | Energy: -0.875503
  Iter  100 | Energy: -0.875928

Final energy: -0.875928 Ha
Optimal params: [0.07960475236177444, -1.5700690746307373, -0.17029154300689697, 1.6225385665893555] ...

Expected: ~-1.10 Ha (simplified Hamiltonian)
```

