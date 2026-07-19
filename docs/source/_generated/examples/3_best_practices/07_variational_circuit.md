### 07 — 简单变分量子线路

*Source*: ``examples/3_best_practices/07_variational_circuit.py``  
*Status*: **pass**

用一个单参数 ansatz 最小化 ``<Z>``。该例子故意不用外部优化库，便于确认线路、模拟和
可视化路径。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/07_variational_circuit.py
:language: python
```

**Stdout**

```text
step=00 theta=0.200 <Z>=0.960 grad=-0.165
step=04 theta=0.440 <Z>=0.875 grad=-0.398
step=08 theta=1.021 <Z>=0.440 grad=-0.865
step=12 theta=1.972 <Z>=-0.385 grad=-0.910
step=16 theta=2.709 <Z>=-0.915 grad=-0.407
final theta: 2.8969
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

