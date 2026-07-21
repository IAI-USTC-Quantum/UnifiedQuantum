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
step=00 theta=0.200 <Z>=0.980 grad=-0.262
step=04 theta=0.512 <Z>=0.870 grad=-0.508
step=08 theta=1.169 <Z>=0.380 grad=-0.895
step=12 theta=2.126 <Z>=-0.515 grad=-0.853
step=16 theta=2.782 <Z>=-0.945 grad=-0.302
final theta: 2.9306
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

