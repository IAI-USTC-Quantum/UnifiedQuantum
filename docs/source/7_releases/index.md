# Release Notes

这个页面汇总 UnifiedQuantum 的版本变化、升级时值得优先关注的调整，以及更完整的版本变化记录。

## 先看什么

如果你在跟随当前开发版，先看 ``Unreleased``；如果你是从较早的正式版本直接升级，
**先看 ``v0.0.13``**——这一版集中收敛了 CLI / 模拟器 / Python API 的入口。

升级到 ``v0.0.13`` 时最值得先确认的是：

- 你是否还在用 ``uniqc submit --platform <p> [--backend <b>]`` 这种写法。``--platform``
  在 ``v0.0.13`` 已经从 ``submit`` 移除，只能用 ``uniqc submit ... --backend
  <provider>:<chip>``（例如 ``--backend originq:WK_C180``、``--backend ibm:ibm_fez``、
  ``--backend dummy:local:simulator``、``--backend dummy:originq:WK_C180``）。
  ``--backend`` 不写时默认为 ``dummy:local:simulator``。``backend list/update`` /
  ``task list`` / ``result`` 这些子命令仍然接受 ``--platform``。
- 你是否在 Python 层面 ``from uniqc.simulator import OriginIR_Simulator`` 或
  ``QASM_Simulator``。这两个类在 ``v0.0.13`` 已经被合并为统一的 ``Simulator`` /
  ``NoisySimulator``；``program_type=`` 参数同时移除，输入直接走 ``AnyQuantumCircuit``
  自动归一化。
- 你是否在用 ``unified-quantum[qiskit]`` 或 ``unified-quantum[quafu]`` 这两个 extras
  装包。``v0.0.13`` 起 ``qiskit`` 已经是核心依赖（``pip install unified-quantum``
  即可），而 ``quafu`` 已归档，需要的人请独立 ``pip install pyquafu`` 并接受
  ``numpy<2`` 约束。
- 你是否在用 ``uniqc calibrate`` 进行芯片标定实验（``xeb`` / ``readout`` / ``pattern``
  三个子命令；``v0.0.13`` 新增了 parallel-CZ XEB 模块和严格的预飞行检查）
- 你是否在用显式 dummy backend id，而非已废弃的 ``submit_task(dummy=True)``。推荐写法是
  ``backend="dummy:local:simulator"``、``backend="dummy:local:virtual-line-3"``、
  ``backend="dummy:local:virtual-grid-2x2"``、``backend="dummy:originq:WK_C180"``。
- 你是否理解 ``dummy:<platform>:<backend>`` 是规则型写法，不会作为独立 backend 展示；
  提交时会先按真实 backend compile/transpile，再在本地 dummy 上做含噪执行。
- 你是否在 Python API 中手动拼接 OriginIR 并提交——``uniqc submit --dry-run`` 可以先做一次离线校验
- 装包 / 配置出问题时，先跑一遍 ``uv run uniqc doctor``——``v0.0.13`` 新增了这个环境
  自检命令。

## 发布前可验证路径检查

在创建新的 ``v*`` tag 前，维护者必须完成一次人工可验证路径检查，确认用户主路径没有失效。
具体清单见 ``.claude/skills/uniqc-test-before-release/SKILL.md``。文档系统里这条路径
对应的是：

```bash
cd docs
uv run make html       # 触发完整 pre-doc-execution + sphinx 编译
```

只有所有 ``examples/<chapter>/*.py`` 都 pass（或合理地 skip）才能发布。

## 具体版本变化参考

下面这部分会在文档构建时根据仓库里的 tag、提交标题和文件变化自动整理，适合用来查
某个版本具体包含了哪些提交和改动范围。

```{include} _generated/strict_history.md
```
