### 05 — Visualize circuits and results

*Source*: ``examples/1_basic_usage/05_visualize.py``  
*Status*: **pass**

两类常用的可视化：

* 测量结果直方图（``matplotlib`` 直接画 counts/probabilities）；
* 时序图 ``plot_time_line``（如果安装了 ``visualization`` extra），用来排查 timeline /
  并行度问题。

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/05_visualize.py
:language: python
```

**Stdout**

```text
counts: {0: 519, 7: 505}
probabilities: {'000': 0.5068359375, '111': 0.4931640625}
```

**Figures**

![05 — Visualize circuits and results — figure-01.png](../_generated/examples/1_basic_usage/figures/05_visualize/figure-01.png)

