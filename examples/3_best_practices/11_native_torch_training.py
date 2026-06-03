"""11 — 原生 Torch 训练（不依赖 TorchQuantum）

[doc-require: pytorch, matplotlib]
[doc-output-include: stdout, figures, source]

使用 UnifiedQuantum 原生 ``expectation()`` 函数进行量子-经典混合训练。

无需 TorchQuantum 依赖——梯度通过纯 PyTorch 的态矢量模拟自动传播。
本示例演示三种参数风格：``has_param``、``param_dict``、直接传入 tensor。
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import torch

from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.torch_adapter.expectation import expectation


def main() -> None:
    torch.manual_seed(42)

    # ── 风格 1：has_param（类似 TorchQuantum，最简洁） ─────────────────
    print("=== 风格 1: has_param ===")
    c1 = Circuit(2)
    c1.ry(0, has_param=True)
    c1.ry(1, has_param=True)
    c1.cnot(0, 1)

    hamiltonian = [("ZZ", 1.0), ("ZI", -0.5), ("IZ", -0.5)]
    opt1 = torch.optim.Adam(c1.params, lr=0.05)

    history1 = []
    for step in range(80):
        opt1.zero_grad()
        e = expectation(c1, hamiltonian)
        e.backward()
        opt1.step()
        history1.append(e.item())

    print(f"  初始能量: {history1[0]:.4f}")
    print(f"  最终能量: {history1[-1]:.4f}")
    print(f"  参数数: {len(c1.params)}")

    # ── 风格 2：param_dict（命名引用） ─────────────────────────────────
    print("\n=== 风格 2: param_dict ===")
    params2 = {
        "theta": torch.nn.Parameter(torch.randn(1)),
        "phi": torch.nn.Parameter(torch.randn(1)),
    }
    c2 = Circuit(2, param_dict=params2)
    c2.ry(0, "theta")
    c2.ry(1, "phi")
    c2.cnot(0, 1)

    opt2 = torch.optim.Adam(params2.values(), lr=0.05)

    history2 = []
    for step in range(80):
        opt2.zero_grad()
        e = expectation(c2, hamiltonian)
        e.backward()
        opt2.step()
        history2.append(e.item())

    print(f"  初始能量: {history2[0]:.4f}")
    print(f"  最终能量: {history2[-1]:.4f}")

    # ── 风格 3：直接传入 tensor ────────────────────────────────────────
    print("\n=== 风格 3: 直接传入 tensor ===")
    t0 = torch.tensor(0.5, requires_grad=True)
    t1 = torch.tensor(0.3, requires_grad=True)
    c3 = Circuit(2)
    c3.ry(0, t0)
    c3.ry(1, t1)
    c3.cnot(0, 1)

    opt3 = torch.optim.Adam([t0, t1], lr=0.05)

    history3 = []
    for step in range(80):
        opt3.zero_grad()
        e = expectation(c3, hamiltonian)
        e.backward()
        opt3.step()
        history3.append(e.item())

    print(f"  初始能量: {history3[0]:.4f}")
    print(f"  最终能量: {history3[-1]:.4f}")

    # ── 可视化 ─────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(history1, label="has_param", linewidth=2)
    ax.plot(history2, label="param_dict", linewidth=2, linestyle="--")
    ax.plot(history3, label="tensor", linewidth=2, linestyle=":")
    ax.axhline(y=-1.5, color="gray", linestyle="-.", alpha=0.5, label="基态能量 -1.5")
    ax.set_xlabel("step")
    ax.set_ylabel("⟨H⟩")
    ax.set_title("原生 Torch 训练：三种参数风格对比")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()


if __name__ == "__main__":
    main()
