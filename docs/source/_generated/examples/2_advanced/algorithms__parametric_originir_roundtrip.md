### OriginIR-ext 符号参数往返

*Source*: ``examples/2_advanced/algorithms/parametric_originir_roundtrip.py``  
*Status*: **pass**

OriginIR-ext 符号参数往返（Parameter/Parameters ↔ PARAM）。

演示 UnifiedQuantum 的符号参数如何序列化为 OriginIR-ext 文本、解析回电路，
并在绑定具体数值后本地模拟：

  * 用 ``Parameter`` / ``Parameters`` 构造未绑定的参数化电路
  * ``circuit.originir`` 输出 ``PARAM`` 头 + 内联符号表达式
  * ``Circuit.from_originir`` 往返解析（保留参数名与数组结构）
  * ``circuit.assign_parameters`` 绑定数值后模拟

符号参数是 **OriginIR-ext 本地专属** 特性：提交云端或导出 QASM /
官方 OriginIR 前必须先绑定为具体数值。

Usage:
    python parametric_originir_roundtrip.py

**Source code**

```{literalinclude} ../../../examples/2_advanced/algorithms/parametric_originir_roundtrip.py
:language: python
```

**Stdout**

```text
============================================================
1) Build an unbound symbolic circuit
============================================================
  is_parametric  : True
  free_parameters: ['phi', 'theta', 'w_0', 'w_1']

============================================================
2) Serialize to OriginIR-ext (PARAM header + inline exprs)
============================================================
QINIT 2
CREG 2
PARAM phi
PARAM theta
PARAM w[2]
RX q[0], (theta)
RY q[1], (phi/3 + 2*theta)
RZ q[0], (w[0])
RY q[1], (w[1])
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]

============================================================
3) Round-trip: from_originir(...).originir == originir
============================================================
  round-trip identical: True
  free_parameters     : ['phi', 'theta', 'w_0', 'w_1']

============================================================
4) Bind values with assign_parameters, then simulate
============================================================
  bound is_parametric: False
  bound OriginIR:
    QINIT 2
    CREG 2
    RX q[0], (0.7853981633974483)
    RY q[1], (2.0943951023931953)
    RZ q[0], (0.3)
    RY q[1], (0.7)
    CNOT q[0], q[1]
    MEASURE q[0], c[0]
    MEASURE q[1], c[1]

  statevector norm: 1.0000000000

  Binding via a bound Parameters object also works:
    remaining free after array bind: ['phi', 'theta']
```

