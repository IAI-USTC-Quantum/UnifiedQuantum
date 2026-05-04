# 最佳实践

最佳实践章节由一组已经执行过的 notebooks 组成。它们不是 CI，而是发布前的“可验证路径检查”：维护者通过重跑这些案例，确认用户从配置、构建线路、选择后端、提交任务、获取结果、可视化，到变分线路、Torch 集成、Calibration + QEM 的主路径仍然有效。

当前 dummy backend 的推荐写法是显式 backend id：`dummy` 表示无约束、无噪声；`dummy:virtual-line-N` / `dummy:virtual-grid-RxC` 表示带虚拟拓扑约束但无噪声；`dummy:<platform>:<backend>` 表示复用真实 backend 的拓扑和标定数据，先 compile/transpile，再本地含噪执行。最后一种是规则型写法，不会作为独立 backend 列表项展示。

## 覆盖矩阵

| 案例 | 配置 Key | 后端缓存 | 裸 Circuit | Named Circuit | 虚拟/本地后端 | API 提交 | CLI 提交 | 可视化 | 变分 | Torch | Calibration/QEM |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 00 配置与后端缓存 | ✓ | ✓ |  |  | ✓ |  |  |  |  |  |  |
| 01 裸线路模拟 |  |  | ✓ |  | ✓ |  |  | ✓ |  |  |  |
| 02 Named Circuit |  |  | ✓ | ✓ | ✓ |  |  | ✓ |  |  |  |
| 03 编译与虚拟后端 |  |  | ✓ |  | ✓ |  |  |  |  |  |  |
| 04 API 提交 |  |  | ✓ |  | ✓ | ✓ |  | ✓ |  |  |  |
| 05 CLI 提交 |  |  | ✓ |  | ✓ |  | ✓ |  |  |  |  |
| 06 云后端模板 | ✓ |  | ✓ |  | ✓ | ✓ | ✓ |  |  |  |  |
| 07 变分线路 |  |  | ✓ |  | ✓ |  |  | ✓ | ✓ |  |  |
| 08 Torch 集成 |  |  | ✓ |  | ✓ |  |  | ✓ | ✓ | ✓ |  |
| 09 Calibration + QEM |  |  |  |  | ✓ |  |  | ✓ |  |  | ✓ |
| 10 XEB workflow |  |  | ✓ |  | ✓ |  |  | ✓ |  |  | ✓ |

## 案例目录

```{toctree}
:maxdepth: 1

00_config_and_backend_cache
01_bare_circuit_simulation
02_named_circuit_and_reuse
03_compile_region_dummy_backend
04_api_submit_dummy_result
05_cli_workflow_dummy
06_cloud_backend_template
07_variational_circuit
08_torch_quantum_training
09_calibration_qem_dummy
10_xeb_workflow_dummy
```

## 发布前重跑

维护者发布前应在完整开发环境中重新生成这些 notebooks：

```bash
uv sync --extra all --group dev --group docs --upgrade
uv run python scripts/generate_best_practice_notebooks.py
cd docs
uv run make html
```

如果某个案例因为真实云平台不可用而无法执行，应保持 dummy/dry-run 路径可执行，并在 Release note 中说明真实平台验证的缺口。

如果由 AI agent 执行发布前检查，建议先运行 `uniqc config always-ai-hint on`，或在单条 CLI 命令中加 `--ai-hints` / `--ai-hint`。`docs/source/cli/workflow.md` 是工作流说明页，不对应 `uniqc workflow` 子命令。
