### 03 — 编译、拓扑与虚拟后端

*Source*: ``examples/3_best_practices/03_compile_region_dummy_backend.py``  
*Status*: **pass**

构造一个虚拟线性拓扑后端，把不满足相邻拓扑的线路编译到目标基门集合，并检查编译产物。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/03_compile_region_dummy_backend.py
:language: python
```

**Stdout**

```text
backend: dummy:virtual-line-3
compiled OriginIR:
QINIT 2
CREG 0
RZ q[0], (1.5707963267948966)
SX q[0]
RZ q[0], (1.5707963267948966)
RZ q[1], (1.5707963267948966)
SX q[1]
RZ q[1], (3.141592653589793)
CZ q[0], q[1]
SX q[1]
RZ q[1], (1.5707963267948966)

compiled QASM first lines:
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[0];
rz(pi/2) q[0];
sx q[0];
rz(pi/2) q[0];
rz(pi/2) q[1];
```

