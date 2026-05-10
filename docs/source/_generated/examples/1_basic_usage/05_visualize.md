### 05 — Visualize circuits and results

*Source*: ``examples/1_basic_usage/05_visualize.py``  
*Status*: **skip** — missing requirements: matplotlib (matplotlib installed)

两类常用的可视化：

* 测量结果直方图（``matplotlib`` 直接画 counts/probabilities）；
* 时序图 ``plot_time_line``（如果安装了 ``visualization`` extra），用来排查 timeline /
  并行度问题。

Uses ``Simulator`` (unified simulator class from ``uniqc.simulator``).

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/05_visualize.py
:language: python
```

:::{note}
Example skipped during pre-doc-execution: missing requirements: matplotlib (matplotlib installed)
:::

