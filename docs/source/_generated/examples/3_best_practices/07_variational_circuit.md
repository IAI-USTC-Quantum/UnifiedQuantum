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
step=00 theta=0.200 <Z>=0.990 grad=-0.202
step=04 theta=0.466 <Z>=0.925 grad=-0.427
step=08 theta=1.056 <Z>=0.500 grad=-0.847
step=12 theta=2.010 <Z>=-0.400 grad=-0.920
step=16 theta=2.725 <Z>=-0.900 grad=-0.380
final theta: 2.9013
```

**Figures**

![07 — 简单变分量子线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/07_variational_circuit/figure-01.svg)

