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

  Iter   20 | Cut value: 1.987837
  Iter   40 | Cut value: 1.999460
  Iter   60 | Cut value: 1.999789
  Iter   80 | Cut value: 1.999865
  Iter  100 | Cut value: 1.999989

Final cut value: 1.999989
Optimal gammas: [-1.2162392139434814, -0.18375138938426971]
Optimal betas:  [-0.2439461052417755, -0.06568664312362671]
Approximation ratio: 1.0000
```

