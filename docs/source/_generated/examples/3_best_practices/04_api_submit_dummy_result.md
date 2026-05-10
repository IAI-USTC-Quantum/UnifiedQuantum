### 04 — Python API 提交、取回与可视化

*Source*: ``examples/3_best_practices/04_api_submit_dummy_result.py``  
*Status*: **skip** — missing requirements: matplotlib (matplotlib installed)

使用 ``submit_task(backend="dummy:local:simulator")`` 验证远端任务接口的本地替代
路径：提交、等待、查询缓存、画图。

* ``backend="dummy:local:simulator"`` 表示无约束、无噪声；
* 需要虚拟拓扑时使用 ``dummy:local:virtual-line-N`` / ``dummy:local:virtual-grid-RxC``；
* 需要真实芯片噪声时使用 ``dummy:<platform>:<backend>``。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/04_api_submit_dummy_result.py
:language: python
```

:::{note}
Example skipped during pre-doc-execution: missing requirements: matplotlib (matplotlib installed)
:::

