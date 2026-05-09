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
step=00 theta=0.200 <Z>=0.985 grad=-0.148
step=04 theta=0.445 <Z>=0.930 grad=-0.440
step=08 theta=1.062 <Z>=0.520 grad=-0.892
step=12 theta=2.023 <Z>=-0.440 grad=-0.922
step=16 theta=2.736 <Z>=-0.885 grad=-0.420
final theta: 2.915
```

**Figures**

![07 — 简单变分量子线路 — figure-01.png](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.png)

