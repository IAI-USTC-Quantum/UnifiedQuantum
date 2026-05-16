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
step=00 theta=0.200 <Z>=0.985 grad=-0.225
step=04 theta=0.473 <Z>=0.910 grad=-0.458
step=08 theta=1.091 <Z>=0.475 grad=-0.878
step=12 theta=2.044 <Z>=-0.490 grad=-0.900
step=16 theta=2.741 <Z>=-0.920 grad=-0.435
final theta: 2.9175
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

