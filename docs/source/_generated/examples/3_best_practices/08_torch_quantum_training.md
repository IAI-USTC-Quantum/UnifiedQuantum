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
tensor(2.7910, requires_grad=True)
last rows: [(13, 2.489500045776367, -0.62, -0.7975000000000001), (14, 2.6679999828338623, -0.795, -0.595), (15, 2.7909998893737793, -0.895, -0.41000000000000003)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.svg)

