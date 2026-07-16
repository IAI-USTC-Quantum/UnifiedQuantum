### 02 — Named Circuit 与可复用线路

*Source*: ``examples/3_best_practices/02_named_circuit_and_reuse.py``  
*Status*: **pass**

用命名寄存器和 ``@circuit_def`` 组织可复用子线路，再组合成一个 4-qubit GHZ-like 电路。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/02_named_circuit_and_reuse.py
:language: python
```

**Stdout**

```text
DEF export:
DEF bell_pair(q[2])
  H q[0]
  CNOT q[0], q[1]
ENDDEF
operations: 9
named-register DEF program flattens to:
QINIT 4
CREG 0
H q[0]
CNOT q[0], q[1]
H q[2]
CNOT q[2], q[3]
non-zero states: {'0000': 0.24999999999999978, '0111': 0.2499999999999998, '1011': 0.24999999999999986, '1100': 0.24999999999999983}
```

**Figures**

![02 — Named Circuit 与可复用线路 — figure-01.svg](../_generated/examples/3_best_practices/figures/02_named_circuit_and_reuse/figure-01.svg)

