### 06 — Error mitigation: M3 / readout EM

*Source*: ``examples/2_advanced/06_qem_m3.py``  
*Status*: **pass**

读取误差是芯片上最便宜的可纠错部分。``ReadoutEM`` 自动从
``~/.uniqc/calibration_cache/`` 读 readout 校准结果，对 counts 做线性反演修正
（M3 在多比特上是更紧凑的 LSQR 实现）。

**Source code**

```{literalinclude} ../../../examples/2_advanced/06_qem_m3.py
:language: python
```

**Stdout**

```text
observed:        {0: 40, 1: 360}
mitigated (~):   {0: 0.0, 1: 400.0}
```

