### 05 — CLI 提交完整链路

*Source*: ``examples/3_best_practices/05_cli_workflow_dummy.py``  
*Status*: **pass**

通过 ``subprocess.run`` 执行 CLI：写出 OriginIR 文件，``uniqc submit --platform dummy --wait``，
并展示返回结果。

* ``--platform dummy`` 默认对应无约束、无噪声的 ``dummy``；
* 可通过 ``--backend virtual-line-3`` 指定虚拟拓扑；
* 也可通过 ``--backend originq:WK_C180`` 走真实 backend compile/transpile + 本地含噪执行。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/05_cli_workflow_dummy.py
:language: python
```

**Stdout**

```text
command: /home/agony/projects/quantum-simulator-paper-new/UnifiedQuantum/.venv/bin/python3 -m uniqc.cli submit /tmp/uniqc-bp-cli-48p0kjyp/bell.originir -p dummy -s 64 --wait --format json
{
  "task_id": "uqt_8cc935de0a1a43068d8bc72b45388c39",
  "platform": "dummy",
  "shots": 64
}
{
  "counts": {
    "00": 32,
    "11": 32
  },
  "probabilities": {
    "00": 0.5,
    "11": 0.5
  },
  "shots": 64,
  "platform": "dummy",
  "task_id": "uqt_8cc935de0a1a43068d8bc72b45388c39",
  "backend_name": "dummy:local:simulator",
  "execution_time": null,
  "error_message": null
}
```

