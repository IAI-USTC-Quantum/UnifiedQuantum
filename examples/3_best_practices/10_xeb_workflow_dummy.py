"""10 — XEB workflow

[doc-require: matplotlib]
[doc-output-include: stdout, figures, source]

使用很小的参数运行 1q XEB，覆盖校准、ReadoutEM、随机线路生成、fidelity 拟合和结果
图示。本例子使用 ``backend="dummy:local:simulator"`` 搭配显式 ``noise_model`` 做本地
含噪发布检查；如果要检查真实芯片标定噪声路径，应改用 ``backend="dummy:originq:WK_C180"``
这类规则型 backend id，它会先按真实 backend compile/transpile，再本地含噪执行。
"""

from __future__ import annotations

import tempfile

import matplotlib.pyplot as plt

from uniqc import xeb_workflow


def main() -> None:
    cache_dir = tempfile.mkdtemp(prefix="uniqc-bp-xeb-")
    results = xeb_workflow.run_1q_xeb_workflow(
        backend="dummy:local:simulator",
        qubits=[0],
        depths=[1, 2, 3],
        n_circuits=3,
        shots=128,
        use_readout_em=True,
        noise_model={"depol": 0.01, "readout": 0.04},
        seed=11,
        cache_dir=cache_dir,
    )

    result = results[0]
    print("fidelity_per_layer:", round(result.fidelity_per_layer, 6))
    print(
        "fit parameters:",
        {
            "A": round(result.fit_a, 6),
            "B": round(result.fit_b, 6),
            "r": round(result.fit_r, 6),
        },
    )
    print("depths:", result.depths)

    fitted = [
        result.fit_a * (result.fit_r ** depth) + result.fit_b for depth in result.depths
    ]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot(result.depths, fitted, marker="o")
    ax.set_xlabel("depth")
    ax.set_ylabel("fitted fidelity")
    ax.set_title("1q XEB fitted release-check result")
    ax.grid(alpha=0.25)
    fig.tight_layout()


if __name__ == "__main__":
    main()
