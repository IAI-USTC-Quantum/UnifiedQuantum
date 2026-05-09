### 01 — Compile internals: levels, basis gates, virtual backends

*Source*: ``examples/2_advanced/01_compile_options.py``  
*Status*: **pass**

``uniqc.compile.compile`` 把任意 ``Circuit`` 编译到目标后端的拓扑、基门集合和提交
语言。常用旋钮：

* ``backend_info`` — 目标后端（拓扑 + basis gates 的来源）；
* ``output_format="originir" | "qasm"`` — 提交语言；
* ``optimization_level=0..3`` — 编译激进度。

这里在两个虚拟后端上对比同一个跨距 CNOT 线路的编译产物。

**Source code**

```{literalinclude} ../../../examples/2_advanced/01_compile_options.py
:language: python
```

**Stdout**

```text
== compile target: dummy:virtual-line-4 ==
QINIT 4
CREG 2
RZ q[0], (1.5707963267948966)
SX q[0]
RZ q[0], (1.5707963267948966)
RZ q[1], (1.5707963267948966)
SX q[1]
RZ q[1], (3.141592653589793)
CZ q[0], q[1]
SX q[1]
RZ q[1], (1.5707963267948966)
MEASURE q[0], c[0]
MEASURE q[1], c[1]

== compile target: dummy:virtual-grid-2x2 ==
QINIT 4
CREG 2
RZ q[0], (1.5707963267948966)
SX q[0]
RZ q[0], (1.5707963267948966)
RZ q[1], (1.5707963267948966)
SX q[1]
RZ q[1], (3.141592653589793)
CZ q[0], q[1]
SX q[1]
RZ q[1], (1.5707963267948966)
MEASURE q[0], c[0]
MEASURE q[1], c[1]
```

