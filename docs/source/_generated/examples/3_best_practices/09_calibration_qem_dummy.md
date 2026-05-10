### 09 — Calibration + QEM

*Source*: ``examples/3_best_practices/09_calibration_qem_dummy.py``  
*Status*: **skip** — missing requirements: matplotlib (matplotlib installed)

在带显式读出噪声的 dummy adapter 上运行读出校准，将校准结果写入临时缓存，再用
``ReadoutEM`` 对同一个 noisy backend 产生的观测 counts 做修正。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/09_calibration_qem_dummy.py
:language: python
```

:::{note}
Example skipped during pre-doc-execution: missing requirements: matplotlib (matplotlib installed)
:::

