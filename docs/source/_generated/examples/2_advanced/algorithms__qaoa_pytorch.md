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

  Iter   20 | Cut value: 1.988326
  Iter   40 | Cut value: 1.998136
  Iter   60 | Cut value: 1.999773
  Iter   80 | Cut value: 1.999964
  Iter  100 | Cut value: 1.999994

Final cut value: 1.999994
Optimal gammas: [-0.013208533637225628, -1.2689504623413086]
Optimal betas:  [1.1404902935028076, -0.3206617832183838]
Approximation ratio: 1.0000
```

