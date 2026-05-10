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
tensor(2.7790, requires_grad=True)
last rows: [(13, 2.4625000953674316, -0.67, -0.815), (14, 2.6514999866485596, -0.8, -0.63), (15, 2.7790000438690186, -0.88, -0.42500000000000004)]
```

**Figures**

![08 — Torch 集成后的量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/08_torch_quantum_training/figure-01.png)

