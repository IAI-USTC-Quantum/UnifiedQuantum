#!/usr/bin/env python
"""OriginIR-ext 符号参数往返（Parameter/Parameters ↔ PARAM）。

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

[doc-require: ]
[doc-title: OriginIR-ext 符号参数往返]
"""

import numpy as np

from uniqc import Circuit, Parameter, Parameters
from uniqc.simulator import Simulator


def build_symbolic_circuit() -> Circuit:
    """Build a 2-qubit ansatz with a scalar, an expression, and an array."""
    theta = Parameter("theta")
    phi = Parameter("phi")
    weights = Parameters("w", size=2)

    c = Circuit(2)
    c.rx(0, theta)  # bare scalar parameter
    c.ry(1, theta * 2 + phi / 3)  # symbolic expression
    c.rz(0, weights[0])  # parameter-array element
    c.ry(1, weights[1])
    c.cnot(0, 1)
    c.measure(0, 1)
    return c


def main() -> None:
    print("=" * 60)
    print("1) Build an unbound symbolic circuit")
    print("=" * 60)
    circuit = build_symbolic_circuit()
    print(f"  is_parametric  : {circuit.is_parametric}")
    print(f"  free_parameters: {circuit.free_parameters}")

    print("\n" + "=" * 60)
    print("2) Serialize to OriginIR-ext (PARAM header + inline exprs)")
    print("=" * 60)
    ir = circuit.originir
    print(ir)

    print("=" * 60)
    print("3) Round-trip: from_originir(...).originir == originir")
    print("=" * 60)
    reparsed = Circuit.from_originir(ir)
    print(f"  round-trip identical: {reparsed.originir == ir}")
    print(f"  free_parameters     : {reparsed.free_parameters}")

    print("\n" + "=" * 60)
    print("4) Bind values with assign_parameters, then simulate")
    print("=" * 60)
    bound = reparsed.assign_parameters(
        {
            "theta": np.pi / 4,
            "phi": np.pi / 2,
            "w_0": 0.3,
            "w_1": 0.7,
        }
    )
    print(f"  bound is_parametric: {bound.is_parametric}")
    print("  bound OriginIR:")
    for line in bound.originir.splitlines():
        print(f"    {line}")

    sv = Simulator().simulate_statevector(bound.originir)
    print(f"\n  statevector norm: {np.linalg.norm(sv):.10f}")

    # A Parameters object can also be bound directly.
    print("\n  Binding via a bound Parameters object also works:")
    weights = Parameters("w", size=2)
    weights.bind([0.3, 0.7])
    partial = reparsed.assign_parameters(weights)
    print(f"    remaining free after array bind: {partial.free_parameters}")


if __name__ == "__main__":
    main()
