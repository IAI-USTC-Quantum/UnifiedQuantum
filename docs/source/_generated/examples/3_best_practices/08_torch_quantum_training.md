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
tensor(2.6620, requires_grad=True)
last rows: [(13, 2.2690000534057617, -0.485, -0.9), (14, 2.49399995803833, -0.63, -0.75), (15, 2.6619999408721924, -0.815, -0.56)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.svg)

