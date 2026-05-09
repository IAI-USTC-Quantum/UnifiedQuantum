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
step=00 theta=0.200 <Z>=0.985 grad=-0.228
step=04 theta=0.518 <Z>=0.865 grad=-0.537
step=08 theta=1.189 <Z>=0.390 grad=-0.943
step=12 theta=2.155 <Z>=-0.570 grad=-0.863
step=16 theta=2.781 <Z>=-0.935 grad=-0.362
final theta: 2.9375
```

**Figures**

![07 — 简单变分量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.png)

