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
step=00 theta=0.200 <Z>=0.985 grad=-0.220
step=04 theta=0.466 <Z>=0.915 grad=-0.478
step=08 theta=1.065 <Z>=0.450 grad=-0.858
step=12 theta=2.014 <Z>=-0.490 grad=-0.897
step=16 theta=2.717 <Z>=-0.930 grad=-0.350
final theta: 2.8769
```

**Figures**

![07 — 简单变分量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.png)

