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
command: /home/agony/projects/uniqc-dev/UnifiedQuantum/.venv/bin/python3 -m uniqc.cli submit /tmp/uniqc-bp-cli-hz7lj89h/bell.originir --backend dummy -s 64 --wait --format json
[1m{[0m
  [32m"task_id"[0m: [32m"uqt_05bb167b019e4c248f9a58d9eb968016"[0m,
  [32m"backend"[0m: [32m"dummy:local:simulator"[0m,
  [32m"shots"[0m: [1;36m64[0m
[1m}[0m
[1m{[0m
  [32m"counts"[0m: [1m{[0m
    [32m"00"[0m: [1;36m32[0m,
    [32m"11"[0m: [1;36m32[0m
  [1m}[0m,
  [32m"probabilities"[0m: [1m{[0m
    [32m"00"[0m: [1;36m0.5[0m,
    [32m"11"[0m: [1;36m0.5[0m
  [1m}[0m,
  [32m"shots"[0m: [1;36m64[0m,
  [32m"platform"[0m: [32m"dummy"[0m,
  [32m"task_id"[0m: [32m"uqt_05bb167b019e4c248f9a58d9eb968016"[0m,
  [32m"backend_name"[0m: [32m"dummy:local:simulator"[0m,
  [32m"execution_time"[0m: null,
  [32m"error_message"[0m: null
[1m}[0m
```

