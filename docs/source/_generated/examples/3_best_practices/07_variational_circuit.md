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
step=00 theta=0.200 <Z>=0.990 grad=-0.240
step=04 theta=0.496 <Z>=0.850 grad=-0.495
step=08 theta=1.130 <Z>=0.385 grad=-0.912
step=12 theta=2.098 <Z>=-0.505 grad=-0.872
step=16 theta=2.748 <Z>=-0.925 grad=-0.463
final theta: 2.9356
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

