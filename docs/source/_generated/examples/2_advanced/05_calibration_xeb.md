### 05 — Calibration: 1q XEB on a noisy dummy backend

*Source*: ``examples/2_advanced/05_calibration_xeb.py``  
*Status*: **pass**

XEB 通过对比理论 vs 观测的 cross-entropy 来估计每层平均门保真度。这里在带显式去极化
噪声的 ``dummy:local:simulator`` 上跑一个非常小的 1q XEB，仅做接口路径验证。
真实芯片 XEB 通过 ``uniqc calibrate xeb`` CLI 跑，结果落在
``~/.uniqc/calibration_cache/``。

**Source code**

```{literalinclude} ../../../examples/2_advanced/05_calibration_xeb.py
:language: python
```

**Stdout**

```text
qubit:           0
depths:          (1, 2, 4, 8)
fidelity/layer:  0.993333
fit  A=1.0000  r=0.9933  B=0.0000
```

