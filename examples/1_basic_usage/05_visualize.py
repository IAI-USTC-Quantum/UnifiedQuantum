"""05 — Visualize circuits and results

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

两类常用的可视化：

* 测量结果直方图（``matplotlib`` 直接画 counts/probabilities）；
* 时序图 ``plot_time_line``（如果安装了 ``visualization`` extra），用来排查 timeline /
  并行度问题。

Uses ``Simulator`` (unified simulator class from ``uniqc.simulator``).
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from uniqc import Circuit
from uniqc.simulator import Simulator


def main() -> None:
    c = Circuit()
    c.h(0)
    c.cnot(0, 1)
    c.cnot(1, 2)
    c.measure(0, 1, 2)

    counts = Simulator().simulate_shots(c.originir, shots=1024)
    total = sum(counts.values()) or 1
    n = c.qubit_num
    probs = {format(int(k), f"0{n}b"): v / total for k, v in counts.items()}

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar(list(probs.keys()), list(probs.values()), color="#2a9d8f")
    ax.set_xlabel("bitstring")
    ax.set_ylabel("probability")
    ax.set_title("3-qubit GHZ probabilities")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    print("counts:", counts)
    print("probabilities:", probs)


if __name__ == "__main__":
    main()
