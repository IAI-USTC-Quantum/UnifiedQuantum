"""03 — Submit to dummy + result post-processing

[doc-require: ]
[doc-output-include: stdout, source]

走一遍 ``submit_task`` → ``wait_for_result`` → ``query_task`` 的完整路径，并把结果
喂给 ``calculate_expectation`` / ``shots2prob`` 等后处理工具。

* ``backend="dummy:local:simulator"`` 表示无约束、无噪声；
* ``backend="dummy:local:virtual-line-3"`` 在虚拟线性拓扑上跑同一线路（受相邻约束）。
"""

from __future__ import annotations

import math

from uniqc import (
    Circuit,
    calculate_expectation,
    query_task,
    shots2prob,
    submit_task,
    wait_for_result,
)


def build_circuit() -> Circuit:
    c = Circuit()
    c.x(0)
    c.rx(1, math.pi)
    c.ry(2, math.pi / 2)
    c.cz(1, 2)
    c.measure(0, 1, 2)
    return c


def main() -> None:
    circuit = build_circuit()

    task_id = submit_task(circuit, backend="dummy:local:simulator", shots=1000)
    print("task_id:", task_id)

    result = wait_for_result(task_id, timeout=60)
    print("counts:", dict(result.counts))
    print("probabilities:", {k: round(v, 4) for k, v in result.probabilities.items()})

    info = query_task(task_id)
    print("status:", info.status)

    print(f"<ZII> = {calculate_expectation(result.probabilities, 'ZII'):+.4f}")
    print(f"<IIZ> = {calculate_expectation(result.probabilities, 'IIZ'):+.4f}")

    print("manual prob conversion:", shots2prob(result.counts))


if __name__ == "__main__":
    main()
