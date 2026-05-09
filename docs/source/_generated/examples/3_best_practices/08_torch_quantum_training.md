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
tensor(2.7865, requires_grad=True)
last rows: [(13, 2.4625000953674316, -0.57, -0.7949999999999999), (14, 2.632000207901001, -0.72, -0.565), (15, 2.7865002155303955, -0.875, -0.515)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.png)

