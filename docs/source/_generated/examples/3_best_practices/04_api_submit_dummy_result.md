### 04 — Python API 提交、取回与可视化

*Source*: ``examples/3_best_practices/04_api_submit_dummy_result.py``  
*Status*: **pass**

使用 ``submit_task(backend="dummy:local:simulator")`` 验证远端任务接口的本地替代
路径：提交、等待、查询缓存、画图。

* ``backend="dummy:local:simulator"`` 表示无约束、无噪声；
* 需要虚拟拓扑时使用 ``dummy:local:virtual-line-N`` / ``dummy:local:virtual-grid-RxC``；
* 需要真实芯片噪声时使用 ``dummy:<platform>:<backend>``。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/04_api_submit_dummy_result.py
:language: python
```

**Stdout**

```text
task_id: uqt_39e3fd043ddb464ea7024ec8524269a5
status: success
counts: UnifiedResult(counts={'00': 64, '11': 64}, probabilities={'00': 0.5, '11': 0.5}, shots=128, platform='dummy', task_id='uqt_39e3fd043ddb464ea7024ec8524269a5', backend_name='dummy:local:simulator', execution_time=None, error_message=None)
```

**Figures**

![04 — Python API 提交、取回与可视化 — figure-01.svg](../_generated/examples/3_best_practices/figures/04_api_submit_dummy_result/figure-01.svg)

