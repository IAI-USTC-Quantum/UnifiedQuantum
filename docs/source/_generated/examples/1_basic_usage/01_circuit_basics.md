### 01 — Circuit basics: gates, qregs, OriginIR / OpenQASM export

*Source*: ``examples/1_basic_usage/01_circuit_basics.py``  
*Status*: **pass**

最常用的 ``Circuit`` 能力：原生 gate API、寄存器、测量，以及导出到 OriginIR /
OpenQASM 2.0 两种文本格式。

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/01_circuit_basics.py
:language: python
```

**Stdout**

```text
== OriginIR ==
QINIT 3
CREG 3
H q[0]
X q[1]
RX q[2], (1.5707963267948966)
CNOT q[0], q[1]
CZ q[1], q[2]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]

== OpenQASM 2.0 ==
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
x q[1];
rx(1.5707963267948966) q[2];
cx q[0], q[1];
cz q[1], q[2];
measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];

== qubit remapping ==
QINIT 103
CREG 3
H q[100]
X q[101]
RX q[102], (1.5707963267948966)
CNOT q[100], q[101]
CZ q[101], q[102]
MEASURE q[100], c[0]
MEASURE q[101], c[1]
MEASURE q[102], c[2]
```

