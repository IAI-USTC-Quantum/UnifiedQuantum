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
step=00 theta=0.200 <Z>=0.975 grad=-0.220
step=04 theta=0.498 <Z>=0.895 grad=-0.455
step=08 theta=1.126 <Z>=0.445 grad=-0.882
step=12 theta=2.077 <Z>=-0.480 grad=-0.853
step=16 theta=2.751 <Z>=-0.895 grad=-0.392
final theta: 2.9144
```

**Figures**

![07 — 简单变分量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.png)

