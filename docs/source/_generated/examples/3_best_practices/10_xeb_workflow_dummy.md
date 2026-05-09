### 10 — XEB workflow

*Source*: ``examples/3_best_practices/10_xeb_workflow_dummy.py``  
*Status*: **pass**

使用很小的参数运行 1q XEB，覆盖校准、ReadoutEM、随机线路生成、fidelity 拟合和结果
图示。本例子使用 ``backend="dummy:local:simulator"`` 搭配显式 ``noise_model`` 做本地
含噪发布检查；如果要检查真实芯片标定噪声路径，应改用 ``backend="dummy:originq:WK_C180"``
这类规则型 backend id，它会先按真实 backend compile/transpile，再本地含噪执行。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/10_xeb_workflow_dummy.py
:language: python
```

**Stdout**

```text
fidelity_per_layer: 0.983341
fit parameters: {'A': 1.01276, 'B': 0.0, 'r': 0.983341}
depths: (1, 2, 3)
```

**Figures**

![10 — XEB workflow — figure-01.png](../_generated/examples/3_best_practices/figures/10_xeb_workflow_dummy/figure-01.png)

