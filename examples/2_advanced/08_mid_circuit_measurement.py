"""08 — Mid-circuit measurement 与经典控制流（CREG / QIF / QWHILE）

[doc-require: ]
[doc-output-include: stdout, source]

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
"""

from __future__ import annotations

from uniqc import Circuit
from uniqc.backend_adapter.task_manager import submit_task, wait_for_result
from uniqc.circuit_builder.classical_program import imm
from uniqc.simulator import OriginIR_ext_Simulator


def build_feedback_circuit() -> Circuit:
    """H q0 后 measure→c0；若 c0=1 则对 q1 做一次 X correction，再 measure q1→c1。

    因此 c1 恒等于 c0：结果只会出现 ``'00'`` 与 ``'11'``，各约一半。
    """
    c = Circuit(2)
    c.creg(2)
    c.h(0)
    c.measure_to(0, 0)  # mid-circuit measurement -> CREG bit 0
    c.qif("c[0]")  # 经典条件：c[0] 为真时执行 then-block
    c.x(1)
    c.endqif()
    c.measure_to(1, 1)
    return c


def build_qwhile_circuit() -> Circuit:
    """反复抛硬币直到测得 1：``QWHILE ~c[0]`` 循环体里 H + measure，直到 c0 变为 1。"""
    c = Circuit(1)
    c.creg(1)
    c.qwhile("~c[0]")  # 只要 c[0] 仍为 0 就继续
    c.h(0)
    c.measure_to(0, 0)
    c.endqwhile()
    return c


def main() -> None:
    print("== 反馈电路的 OriginIR-ext 文本 ==")
    circuit = build_feedback_circuit()
    print(circuit.originir)

    print("\n== 直接用 OriginIR_ext_Simulator 采样（per-shot）==")
    sim = OriginIR_ext_Simulator("statevector", seed=2024)
    counts = sim.simulate_shots(circuit, shots=2000)
    # 结果 key 是 CREG 整数值（c[0] 为 LSB）：0 -> '00'，3 -> '11'
    pretty = {format(v, "02b"): n for v, n in sorted(counts.items())}
    print("  counts (c1c0):", pretty)
    print("  只出现 '00'/'11' ->", set(pretty) <= {"00", "11"})

    print("\n== 通过统一任务接口在 dummy backend 上运行 ==")
    task = submit_task(circuit, backend="dummy:local:simulator", shots=2000)
    print("  result:", wait_for_result(task, timeout=60).counts)

    print("\n== 经典 bit 指令：c2 = c0 XOR c1 ==")
    logic = Circuit(2)
    logic.creg(3)
    logic.x(0)  # q0 -> |1>
    logic.measure_to(0, 0)  # c0 = 1
    logic.measure_to(1, 1)  # c1 = 0
    logic.c_xor(2, 0, 1)  # c2 = c[0] ^ c[1] = 1
    logic.c_not(1, imm(1))  # c1 = ~1 = 0 (imm 明确表示 immediate)
    value = OriginIR_ext_Simulator("statevector", seed=7).simulate_single_shot(logic)
    print("  final CREG value:", value, "-> bits c2c1c0 =", format(value, "03b"))

    print("\n== QWHILE：抛硬币直到出现 1 ==")
    qwhile_counts = OriginIR_ext_Simulator("statevector", seed=11).simulate_shots(build_qwhile_circuit(), shots=500)
    print("  counts:", qwhile_counts, "(恒为 {1: 500}，循环保证结束时 c0=1)")


if __name__ == "__main__":
    main()
