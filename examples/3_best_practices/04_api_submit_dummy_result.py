"""04 — Python API 提交、取回与可视化

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

使用 ``submit_task(backend="dummy:local:simulator")`` 验证远端任务接口的本地替代
路径：提交、等待、查询缓存、画图。

* ``backend="dummy:local:simulator"`` 表示无约束、无噪声；
* 需要虚拟拓扑时使用 ``dummy:local:virtual-line-N`` / ``dummy:local:virtual-grid-RxC``；
* 需要真实芯片噪声时使用 ``dummy:<platform>:<backend>``。
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from uniqc import Circuit, get_task, submit_task, wait_for_result


def plot_probs(probs, title):
    labels = list(probs)
    values = [probs[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(labels, values, color="#3267a8")
    ax.set_ylim(0, max(1.0, max(values, default=0) * 1.2))
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()


def main() -> None:
    circuit = Circuit()
    circuit.h(0)
    circuit.cnot(0, 1)
    circuit.measure(0, 1)

    task_id = submit_task(
        circuit,
        backend="dummy:local:simulator",
        shots=128,
        metadata={"example": "best-practices-api"},
    )
    counts = wait_for_result(task_id)
    task = get_task(task_id)

    print("task_id:", task_id)
    print("status:", task.status)
    print("counts:", counts)

    probs = {k: v / sum(counts.values()) for k, v in counts.items()}
    plot_probs(probs, "API dummy submission result")


if __name__ == "__main__":
    main()
