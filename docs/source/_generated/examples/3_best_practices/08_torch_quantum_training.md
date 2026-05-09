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
tensor(2.8173, requires_grad=True)
last rows: [(13, 2.4850001335144043, -0.665, -0.7925), (14, 2.6777501106262207, -0.83, -0.6425000000000001), (15, 2.8172500133514404, -0.92, -0.46499999999999997)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.png)

