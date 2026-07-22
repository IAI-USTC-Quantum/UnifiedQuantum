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

  Iter   20 | Cut value: 1.976446
  Iter   40 | Cut value: 1.995023
  Iter   60 | Cut value: 1.999523
  Iter   80 | Cut value: 1.999922
  Iter  100 | Cut value: 1.999980

Final cut value: 1.999980
Optimal gammas: [-0.07336180657148361, 1.2970815896987915]
Optimal betas:  [0.20722956955432892, 0.24868912994861603]
Approximation ratio: 1.0000
```

