"""02 — Local simulation paths

[doc-require: ]
[doc-output-include: stdout, source]

UnifiedQuantum 自带几条本地模拟路径：

* ``Simulator`` — 默认 statevector 模拟器；
* MPS 后端（线性拓扑 + 中等纠缠下可扩展到上百比特）—— 见
  ``examples/2_advanced/01_mps_simulator.py``；
* C++ 后端 ``uniqc_cpp`` — 自动作为 ``Simulator`` 的加速实现（如果已编译）。

这里只演示最直接的 ``simulate_pmeasure`` 与 ``simulate_shots``。
"""

from __future__ import annotations

from uniqc import Circuit
from uniqc.simulator import Simulator


def main() -> None:
    c = Circuit()
    c.h(0)
    c.cnot(0, 1)
    c.cnot(1, 2)
    c.measure(0, 1, 2)

    sim = Simulator()
    print("== probabilities ==")
    probs = sim.simulate_pmeasure(c.originir)
    for state, prob in enumerate(probs):
        if prob > 1e-9:
            print(f"  |{state:03b}>: {prob:.4f}")

    print("== shots ==")
    counts = sim.simulate_shots(c.originir, shots=2000)
    print(counts)


if __name__ == "__main__":
    main()
