### 09 — Calibration + QEM

*Source*: ``examples/3_best_practices/09_calibration_qem_dummy.py``  
*Status*: **pass**

在带显式读出噪声的 dummy adapter 上运行读出校准，将校准结果写入临时缓存，再用
``ReadoutEM`` 对同一个 noisy backend 产生的观测 counts 做修正。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/09_calibration_qem_dummy.py
:language: python
```

**Stdout**

```text
assignment fidelity: 0.9
confusion matrix: ((0.92, 0.12), (0.08, 0.88))
observed: {0: 24, 1: 176}
corrected: {0: 0.0, 1: 200.0}
```

**Figures**

![09 — Calibration + QEM — figure-01.png](../_generated/examples/3_best_practices/figures/09_calibration_qem_dummy/figure-01.png)

