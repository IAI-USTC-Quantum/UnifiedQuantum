### 02 — RegionSelector: pick a high-fidelity sub-region of a chip

*Source*: ``examples/2_advanced/02_region_selector.py``  
*Status*: **skip** — missing requirements: originq (pyqpanda3 + originq token configured)

``RegionSelector`` 在芯片标定数据（拓扑 + 单/双比特保真度）上为你挑选一段
**高保真度连续子区域**（链或子区域），用于把小线路放到芯片上"最好的部分"。它接受
一个 ``ChipCharacterization``，最常用的入口是 ``RegionSelector.from_backend``。

真实芯片标定数据（``uniqc backend update --platform originq`` 拉取）以及对应的
凭据。用法本身在所有平台上都一样。

**Source code**

```{literalinclude} ../../../examples/2_advanced/02_region_selector.py
:language: python
```

:::{note}
Example skipped during pre-doc-execution: missing requirements: originq (pyqpanda3 + originq token configured)
:::

