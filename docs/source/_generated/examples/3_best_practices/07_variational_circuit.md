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
step=00 theta=0.200 <Z>=0.975 grad=-0.210
step=04 theta=0.493 <Z>=0.875 grad=-0.450
step=08 theta=1.123 <Z>=0.460 grad=-0.880
step=12 theta=2.076 <Z>=-0.525 grad=-0.870
step=16 theta=2.764 <Z>=-0.940 grad=-0.363
final theta: 2.9256
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

