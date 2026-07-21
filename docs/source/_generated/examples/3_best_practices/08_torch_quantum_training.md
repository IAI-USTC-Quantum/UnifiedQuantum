### 08 — Torch 集成后的量子线路

*Source*: ``examples/3_best_practices/08_torch_quantum_training.py``  
*Status*: **pass**

用 PyTorch 管理参数和优化器，量子期望值由 UnifiedQuantum 线路和模拟器计算，梯度
使用 parameter-shift 写回。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/08_torch_quantum_training.py
:language: python
```

**Stdout**

```text
torch parameter: Parameter containing:
tensor(2.8578, requires_grad=True)
last rows: [(13, 2.5495004653930664, -0.71, -0.7675000000000001), (14, 2.722750425338745, -0.85, -0.5774999999999999), (15, 2.857750415802002, -0.925, -0.44999999999999996)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.svg)

