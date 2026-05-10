### 03 — Submit to dummy + result post-processing

*Source*: ``examples/1_basic_usage/03_submit_and_postprocess.py``  
*Status*: **pass**

走一遍 ``submit_task`` → ``wait_for_result`` → ``query_task`` 的完整路径，并把结果
喂给 ``calculate_expectation`` / ``shots2prob`` 等后处理工具。

* ``backend="dummy:local:simulator"`` 表示无约束、无噪声；
* ``backend="dummy:local:virtual-line-3"`` 在虚拟线性拓扑上跑同一线路（受相邻约束）。

**Source code**

```{literalinclude} ../../../examples/1_basic_usage/03_submit_and_postprocess.py
:language: python
```

**Stdout**

```text
task_id: uqt_9b415b3bdca74c9d83cb5433ff2af2c0
counts: {'001': 0, '011': 500, '101': 0, '111': 500}
probabilities: {'001': 0.0, '011': 0.5, '101': 0.0, '111': 0.5}
status: success
<ZII> = +0.0000
<IIZ> = -1.0000
manual prob conversion: {'001': np.float64(0.0), '011': np.float64(0.5), '101': np.float64(0.0), '111': np.float64(0.5)}
```

