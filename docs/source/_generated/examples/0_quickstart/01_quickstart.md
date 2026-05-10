### 01 — Quickstart: install, simulate, submit

*Source*: ``examples/0_quickstart/01_quickstart.py``  
*Status*: **pass**

最简单的端到端验证：构建 Bell 态 → 本地 OriginIR 模拟 → 通过 ``submit_task`` 在
``dummy:local:simulator`` 上跑一遍。如果你正确装好了 ``unified-quantum`` 并能跑通
这个脚本，就证明环境是可用的。

真机提交把 ``backend`` 换成 ``"originq"`` 即可（推荐先在 ``uniqc config init`` 里
配好 ``originq.token``）。要先离线检查可加 ``dry_run=True``。

**Source code**

```{literalinclude} ../../../examples/0_quickstart/01_quickstart.py
:language: python
```

**Stdout**

```text
== OriginIR ==
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]

== Local simulator counts ==
{3: 501, 0: 523}
== dummy:local:simulator counts ==
UnifiedResult(counts={'00': 512, '11': 512}, probabilities={'00': 0.5, '11': 0.5}, shots=1024, platform='dummy', task_id='uqt_a45c9b9e5e7b4c2187bd8f205b1c8719', backend_name='dummy:local:simulator', execution_time=None, error_message=None)

Real-chip submission template (uncomment after `uniqc config set originq.token ...`):
    submit_task(circuit, backend='originq', shots=1000, backend_name='WK_C180')
```

