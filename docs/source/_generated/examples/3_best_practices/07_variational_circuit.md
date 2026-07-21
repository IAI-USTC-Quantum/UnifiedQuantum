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
step=00 theta=0.200 <Z>=0.980 grad=-0.213
step=04 theta=0.488 <Z>=0.865 grad=-0.438
step=08 theta=1.107 <Z>=0.450 grad=-0.907
step=12 theta=2.069 <Z>=-0.430 grad=-0.860
step=16 theta=2.748 <Z>=-0.930 grad=-0.423
final theta: 2.9275
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

