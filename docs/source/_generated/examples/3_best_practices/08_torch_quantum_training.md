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
tensor(2.6305, requires_grad=True)
last rows: [(13, 2.1812500953674316, -0.295, -0.9525), (14, 2.434000015258789, -0.545, -0.8425), (15, 2.630500078201294, -0.745, -0.655)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.svg)

