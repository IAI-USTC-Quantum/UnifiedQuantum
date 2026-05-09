"""05 — Calibration: 1q XEB on a noisy dummy backend

[doc-require: ]
[doc-output-include: stdout, source]

XEB 通过对比理论 vs 观测的 cross-entropy 来估计每层平均门保真度。这里在带显式去极化
噪声的 ``dummy:local:simulator`` 上跑一个非常小的 1q XEB，仅做接口路径验证。
真实芯片 XEB 通过 ``uniqc calibrate xeb`` CLI 跑，结果落在
``~/.uniqc/calibration_cache/``。
"""

from __future__ import annotations

import tempfile

from uniqc import xeb_workflow


def main() -> None:
    cache_dir = tempfile.mkdtemp(prefix="uniqc-cal-xeb-")
    results = xeb_workflow.run_1q_xeb_workflow(
        backend="dummy:local:simulator",
        qubits=[0],
        depths=[1, 2, 4, 8],
        n_circuits=4,
        shots=200,
        use_readout_em=False,
        noise_model={"depol": 0.005},
        seed=3,
        cache_dir=cache_dir,
    )

    r = results[0]
    print(f"qubit:           {r.qubit}")
    print(f"depths:          {r.depths}")
    print(f"fidelity/layer:  {r.fidelity_per_layer:.6f}")
    print(f"fit  A={r.fit_a:.4f}  r={r.fit_r:.4f}  B={r.fit_b:.4f}")


if __name__ == "__main__":
    main()
