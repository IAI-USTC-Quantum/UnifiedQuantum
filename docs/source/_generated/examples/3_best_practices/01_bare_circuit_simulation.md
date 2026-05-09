### 01 — 裸 Circuit、本地模拟与结果可视化

*Source*: ``examples/3_best_practices/01_bare_circuit_simulation.py``  
*Status*: **pass**

从空 ``Circuit`` 构造 Bell 态，导出 OriginIR / OpenQASM 2.0，使用本地模拟器得到
概率分布并画图。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/01_bare_circuit_simulation.py
:language: python
```

**Stdout**

```text
OriginIR:
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]

QASM header:
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
probabilities: {'00': 0.4999999999999999, '11': 0.4999999999999999}
```

**Figures**

![01 — 裸 Circuit、本地模拟与结果可视化 — figure-01.png](../_generated/examples/3_best_practices/figures/01_bare_circuit_simulation/figure-01.png)

