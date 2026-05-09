"""01 — Quickstart: install, simulate, submit

[doc-require: ]
[doc-output-include: stdout, source]

最简单的端到端验证：构建 Bell 态 → 本地 OriginIR 模拟 → 通过 ``submit_task`` 在
``dummy:local:simulator`` 上跑一遍。如果你正确装好了 ``unified-quantum`` 并能跑通
这个脚本，就证明环境是可用的。

真机提交把 ``backend`` 换成 ``"originq"`` 即可（推荐先在 ``uniqc config init`` 里
配好 ``originq.token``）。要先离线检查可加 ``dry_run=True``。
"""

from __future__ import annotations

from uniqc import Circuit, submit_task, wait_for_result
from uniqc.simulator import OriginIR_Simulator


def main() -> None:
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.measure(0, 1)

    print("== OriginIR ==")
    print(circuit.originir)

    sim = OriginIR_Simulator()
    counts = sim.simulate_shots(circuit.originir, shots=1024)
    print("== Local simulator counts ==")
    print(counts)

    task_id = submit_task(circuit, backend="dummy:local:simulator", shots=1024)
    counts = wait_for_result(task_id)
    print("== dummy:local:simulator counts ==")
    print(counts)

    print()
    print("Real-chip submission template (uncomment after `uniqc config set originq.token ...`):")
    print("    submit_task(circuit, backend='originq', shots=1000, backend_name='WK_C180')")


if __name__ == "__main__":
    main()
