### 05 — CLI 提交完整链路

*Source*: ``examples/3_best_practices/05_cli_workflow_dummy.py``  
*Status*: **pass**

通过 ``subprocess.run`` 执行 CLI：写出 OriginIR 文件，``uniqc submit --backend dummy --wait``，
并展示返回结果。

* ``--backend dummy``（默认）对应无约束、无噪声的 ``dummy:local:simulator``；
* 可通过 ``--backend dummy:local:virtual-line-3`` 指定虚拟拓扑；
* 也可通过 ``--backend dummy:originq:WK_C180`` 走真实 backend compile/transpile + 本地含噪执行。

**Source code**

```{literalinclude} ../../../examples/3_best_practices/05_cli_workflow_dummy.py
:language: python
```

**Stdout**

```text
command: /home/agony/projects/uniqc-dev/UnifiedQuantum/.venv/bin/python3 -m uniqc.cli submit /tmp/uniqc-bp-cli-_x2r5t8y/bell.originir --backend dummy -s 64 --wait --format json
{
  "task_id": "uqt_ed3f17897c5f44c88fd8696722ae7d50",
  "backend": "dummy:local:simulator",
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
  "task_id": "uqt_ed3f17897c5f44c88fd8696722ae7d50",
  "backend_name": "dummy:local:simulator",
  "execution_time": null,
  "error_message": null
}
```

