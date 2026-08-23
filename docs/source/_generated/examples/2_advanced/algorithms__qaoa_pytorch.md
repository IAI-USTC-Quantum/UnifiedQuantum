### QAOA for MaxCut using TorchQuantum backend with native PyTorch autograd.

*Source*: ``examples/2_advanced/algorithms/qaoa_pytorch.py``  
*Status*: **pass**

Demonstrates Quantum Approximate Optimization Algorithm on a triangle graph
with Adam optimizer, using TorchQuantum's differentiable simulation.

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/qaoa_pytorch.py
:language: python
```

**Stdout**

```text
============================================================
QAOA for MaxCut — TorchQuantum Backend
============================================================

Graph: Triangle (3 nodes, 3 edges)
Edges: [(0, 1), (1, 2), (0, 2)]
QAOA depth p=2
Max cut value (exact): 2.0

  Iter   20 | Cut value: 1.923277
  Iter   40 | Cut value: 1.989362
  Iter   60 | Cut value: 1.999433
  Iter   80 | Cut value: 1.999974
  Iter  100 | Cut value: 1.999997

Final cut value: 1.999997
Optimal gammas: [-0.00888873916119337, 1.2550137042999268]
Optimal betas:  [-0.9653720855712891, 0.3027988076210022]
Approximation ratio: 1.0000
```

