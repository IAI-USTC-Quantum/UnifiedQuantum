### 08 — Mid-circuit measurement 与经典控制流（CREG / QIF / QWHILE）

*Source*: ``examples/2_advanced/08_mid_circuit_measurement.py``  
*Status*: **pass**

OriginIR-ext 的 classical / control-flow 扩展支持 mid-circuit measurement、一个运行时
的 classical register（CREG，每个地址一个 bit）、经典 bit 指令（``AND``/``OR``/``XOR``/
``MOV``/``NOT``），以及 ``QIF``/``QWHILE`` 经典控制流。

* ``measure_to(qubit, cbit)``：mid-circuit measurement，把 outcome 写入 CREG 的 ``c[cbit]``；
* ``qif(cond)`` / ``qelse()`` / ``endqif()``、``qwhile(cond)`` / ``endqwhile()``：条件是对
  CREG bit 的 boolean 逻辑（``and``/``or``/``xor``/``not`` 或符号 ``& | ^ ~``，可加括号）；
* ``c_and`` / ``c_or`` / ``c_xor`` / ``c_not`` / ``c_mov``：经典 bit 指令（destination-first，
  operand 是 CREG bit index 或 ``imm(0/1)`` immediate）。

这些电路是 stochastic 的（mid-circuit measurement 会 collapse 态），因此只能通过 per-shot
采样运行：``OriginIR_ext_Simulator`` 每个 shot 从 fresh state 跑完整个 program，读出末态
CREG（``c[0]`` 为 LSB）。它们是 OriginIR-ext 专属特性，不能导出到 OpenQASM 或提交到 cloud。

**Source code**

```{literalinclude} ../../../examples/2_advanced/08_mid_circuit_measurement.py
:language: python
```

**Stdout**

```text
== 反馈电路的 OriginIR-ext 文本 ==
QINIT 2
CREG 2
H q[0]
MEASURE q[0], c[0]
QIF c[0]
X q[1]
ENDQIF
MEASURE q[1], c[1]


== 直接用 OriginIR_ext_Simulator 采样（per-shot）==
  counts (c1c0): {'00': 985, '11': 1015}
  只出现 '00'/'11' -> True

== 通过统一任务接口在 dummy backend 上运行 ==
  result: {'11': 997, '00': 1003}

== 经典 bit 指令：c2 = c0 XOR c1 ==
  final CREG value: 5 -> bits c2c1c0 = 101

== QWHILE：抛硬币直到出现 1 ==
  counts: {1: 500} (恒为 {1: 500}，循环保证结束时 c0=1)
```

