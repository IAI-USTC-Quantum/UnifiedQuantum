"""08 — Torch 集成后的量子线路

[doc-require: pytorch, matplotlib]
[doc-output-include: stdout, figures, source]

用 PyTorch 管理参数和优化器，量子期望值由 UnifiedQuantum 线路和模拟器计算，梯度
使用 parameter-shift 写回。
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import torch

from uniqc import Circuit
from uniqc.simulator import Simulator


def circuit_for(theta):
    c = Circuit()
    c.ry(0, float(theta))
    c.measure(0)
    return c


def z_expectation(theta):
    counts = Simulator().simulate_shots(circuit_for(theta).originir, shots=400)
    total = sum(counts.values()) or 1
    return (counts.get(0, 0) - counts.get(1, 0)) / total


def main() -> None:
    torch.manual_seed(7)

    theta = torch.nn.Parameter(torch.tensor(0.1))
    optimizer = torch.optim.SGD([theta], lr=0.3)
    history = []

    for step in range(16):
        optimizer.zero_grad()
        value = z_expectation(theta.item())
        grad = 0.5 * (
            z_expectation(theta.item() + math.pi / 2)
            - z_expectation(theta.item() - math.pi / 2)
        )
        theta.grad = torch.tensor(grad)
        optimizer.step()
        history.append((step, theta.item(), value, grad))

    print("torch parameter:", theta)
    print("last rows:", history[-3:])

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot([r[0] for r in history], [r[2] for r in history], marker="o", label="<Z>")
    ax.plot([r[0] for r in history], [r[1] for r in history], marker="s", label="theta")
    ax.set_xlabel("step")
    ax.set_title("Torch optimizer with quantum expectation")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()


if __name__ == "__main__":
    main()
