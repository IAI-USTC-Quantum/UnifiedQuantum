"""07 — 简单变分量子线路

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

用一个单参数 ansatz 最小化 ``<Z>``。该例子故意不用外部优化库，便于确认线路、模拟和
可视化路径。
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt

from uniqc import Circuit
from uniqc.simulator import OriginIR_Simulator


def build_ansatz(theta):
    c = Circuit()
    c.ry(0, float(theta))
    c.measure(0)
    return c


def z_expectation(theta):
    counts = OriginIR_Simulator().simulate_shots(build_ansatz(theta).originir, shots=400)
    total = sum(counts.values()) or 1
    p0 = counts.get(0, 0) / total
    p1 = counts.get(1, 0) / total
    return p0 - p1


def main() -> None:
    theta = 0.2
    history = []
    for step in range(18):
        value = z_expectation(theta)
        plus = z_expectation(theta + math.pi / 2)
        minus = z_expectation(theta - math.pi / 2)
        grad = 0.5 * (plus - minus)
        history.append((step, theta, value, grad))
        theta -= 0.25 * grad

    for row in history[::4]:
        print("step=%02d theta=%.3f <Z>=%.3f grad=%.3f" % row)
    print("final theta:", round(theta, 4))

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot([r[0] for r in history], [r[2] for r in history], marker="o")
    ax.set_xlabel("step")
    ax.set_ylabel("<Z>")
    ax.set_title("Variational circuit optimization")
    ax.grid(alpha=0.25)
    fig.tight_layout()


if __name__ == "__main__":
    main()
