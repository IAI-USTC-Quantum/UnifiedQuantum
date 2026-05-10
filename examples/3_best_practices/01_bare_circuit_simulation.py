"""01 — 裸 Circuit、本地模拟与结果可视化

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

从空 ``Circuit`` 构造 Bell 态，导出 OriginIR / OpenQASM 2.0，使用本地模拟器得到
概率分布并画图。
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt

from uniqc import Circuit
from uniqc.simulator import Simulator


def probability_dict(values):
    if isinstance(values, dict):
        total = sum(values.values()) or 1
        return {
            format(int(k), "b") if isinstance(k, int) else str(k): v / total
            for k, v in values.items()
        }
    n = int(math.log2(len(values))) if values else 0
    return {
        format(i, f"0{n}b"): float(p)
        for i, p in enumerate(values)
        if abs(float(p)) > 1e-12
    }


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

    print("OriginIR:")
    print(circuit.originir)
    print("QASM header:")
    print("\n".join(circuit.qasm.splitlines()[:6]))

    sim = Simulator()
    probs = probability_dict(sim.simulate_pmeasure(circuit.originir))
    print("probabilities:", probs)
    plot_probs(probs, "Bell state probabilities")


if __name__ == "__main__":
    main()
