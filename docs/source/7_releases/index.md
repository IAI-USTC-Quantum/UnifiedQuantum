# Release Notes

这个页面汇总 UnifiedQuantum 的版本变化、升级时值得优先关注的调整，以及更完整的版本变化记录。

## 先看什么

如果你在跟随当前开发版，先看 ``Unreleased``；如果你是从较早的正式版本直接升级，
先看 ``v0.0.10``。

升级时最值得先确认的是：

- 你是否在用 ``uniqc calibrate`` 进行芯片标定实验（``xeb`` / ``readout`` / ``pattern`` 三个子命令）
- 你是否在用显式 dummy backend id，而非已废弃的 ``submit_task(dummy=True)``。推荐写法是
  ``backend="dummy:local:simulator"``、``backend="dummy:local:virtual-line-3"``、
  ``backend="dummy:local:virtual-grid-2x2"``、``backend="dummy:originq:WK_C180"``。
- 你是否理解 ``dummy:<platform>:<backend>`` 是规则型写法，不会作为独立 backend 展示；
  提交时会先按真实 backend compile/transpile，再在本地 dummy 上做含噪执行。
- 你是否在 Python API 中手动拼接 OriginIR 并提交——``uniqc submit --dry-run`` 可以先做一次离线校验
- Qiskit 用户是否需要单独安装 ``qiskit-ibm-runtime``（``qiskit-ibm-provider`` 已从 extras 中移除）

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
