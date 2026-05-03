# Release Notes

这个页面汇总 UnifiedQuantum 的版本变化、升级时值得优先关注的调整，以及更完整的版本变化记录。

## 先看什么

### 当前建议先看哪个版本

如果你在跟随当前开发版，先看 `Unreleased`；如果你是从较早的正式版本直接升级，先看 `v0.0.7`。

`v0.0.7` 是目前最新的正式发布。它一次性带来大量新功能（矩阵提取、chip-display、AI 友好帮助、chip 数据层、增强转码器、dry-run 验证），同时也是目前功能最完整的正式版本。

升级时最值得先确认的是：

- 你是否在使用 `uniqc backend chip-display` 查看芯片表征数据（新命令，已整合到 `uniqc backend` 下）
- 你是否在用显式 dummy backend id，而非已废弃的 `submit_task(dummy=True)`。推荐写法是 `backend="dummy"`、`backend="dummy:virtual-line-3"`、`backend="dummy:virtual-grid-2x2"`、`backend="dummy:originq:WK_C180"`。
- 你是否理解 `dummy:<platform>:<backend>` 是规则型写法，不会作为独立 backend 展示；提交时会先按真实 backend compile/transpile，再在本地 dummy 上做含噪执行。
- 你是否在 Python API 中手动拼接 OriginIR 并提交——`uniqc submit --dry-run` 可以先做一次离线校验
- Qiskit 用户是否需要单独安装 `qiskit-ibm-runtime`（`qiskit-ibm-provider` 已从 extras 中移除，因与 qiskit ≥ 1.0 不兼容）

如果你是从更早版本直接升级，`v0.0.5` 仍然值得补读，因为它补齐了上一轮 CLI / 打包相关改动后的几个实际使用问题：

- `uniqc` CLI 在位置参数后跟选项的常见写法现在已经稳定可用
- QASM 到 OriginIR 的转换会保留 `MEASURE`，`uniqc simulate` 也能直接吃 QASM
- `uniqc task show`、`uniqc result`、`uniqc config profile list` 这些命令的展示行为更接近期望
- PyPI 包元数据不再携带 TorchQuantum 的 Git 依赖；只有真的使用对应后端时才需要额外安装

如果你是从更早版本直接升级，`v0.0.4` 仍然值得补读，因为它是第一个明显包含结构性调整的版本：

- CLI 名称从 `uniq` 调整为 `uniqc`
- Python 包名从 `uniq` 调整为 `uniqc`
- 任务缓存统一迁移到 SQLite
- 文档和 API 入口做过一轮整顿

这些变化并不只是内部清理，对已有脚本、命令和缓存位置都可能有影响。

## 发布前可验证路径检查

在创建新的 `v*` tag 前，维护者必须完成一次人工可验证路径检查。这不是 CI，而是通过 [最佳实践](../best_practices/index.md) 中的 executed notebooks 确认用户主路径没有失效。

发布前至少检查：

1. 重新运行 `python scripts/generate_best_practice_notebooks.py`，确认 notebooks 中的输出和图仍然合理。
2. 检查最佳实践覆盖矩阵是否仍覆盖当前版本支持的路径：配置 key、后端缓存、裸 `Circuit`、Named Circuit、虚拟/本地后端、API/CLI 提交、结果可视化、变分线路、Torch 集成、Calibration 和 QEM。
3. 检查 `CHANGELOG.md` 的 `[Unreleased]` 内容是否准确、完整。
4. 检查本页是否已经写入用户可见的升级重点、迁移说明和兼容性变化。
5. 通过文档构建或 `scripts/generate_release_notes.py` 确认 Release note 的自动生成内容正确。
6. 如果真实云平台没有完成验证，明确记录 dummy/dry-run 已验证的范围和真实平台验证缺口。

## 版本解读

### `Unreleased`

当前开发版统一了 dummy backend 的编号语义：

- `dummy` 表示无约束、无噪声本地虚拟机。
- `dummy:virtual-line-N` 和 `dummy:virtual-grid-RxC` 表示带虚拟拓扑约束但无噪声的本地 backend。
- `dummy:<platform>:<backend>` 表示复用真实 backend 的拓扑和 chip characterization 做本地含噪仿真；它是提交规则，不是可枚举 backend，因此不会出现在 `uniqc backend list` 或 Gateway WebUI backend 卡片中。
- chip-backed dummy 提交会忠实执行真实 backend 的 compile/transpile，并把编译后线路和实际执行线路写入 task metadata，便于 Gateway 查看。

### `v0.0.7`

这是一次功能大幅增强的版本，涵盖从量子线路分析到云端提交的全链路改进。

这版最明显的用户侧收益有六类：

- **`Circuit.get_matrix()`**：新增 `circuit.get_matrix()` 方法，直接提取线路的酉矩阵表示，适用于验证小规模电路。
- **`uniqc backend chip-display`**：新命令，全屏展示芯片表征数据（T1/T2、单双比特门保真度、读取保真度、拓扑），支持 OriginQ / Quafu / IBM 所有平台。
- **AI 友好帮助系统**：每个 `--help` 输出均包含文档链接和 Rich 面板引导；`--ai-hints` 选项（及 `UNIQC_AI_HINTS=1` 环境变量）提供 AI 工作流提示。
- **chip 数据层**：统一的 `ChipCharacterization` 数据结构持久化在 `~/.uniqc/backend-cache/`，`ChipService` 封装跨平台获取逻辑。
- **增强转码器 + `RegionSelector`**：新 `compile()` API 支持 chip-aware fidelity-weighted routing，`RegionSelector` 自动找最优比特链/区域。
- **dry-run 验证**：`uniqc submit --dry-run` 可在提交前做离线校验，`submit_task` / `submit_batch` 的 Python API 也有对应接口。

如果你正在从 `v0.0.6` 或更早版本迁移，建议优先复核：

- 你是否有使用 `uniqc chip` 命令——它已移至 `uniqc backend chip-display`
- 你是否在用 `submit_task(..., dummy=True)`——请改用 `submit_task(..., backend="dummy")`（会收到警告，但向后兼容）
- 你是否依赖 `uniqc submit` 的结果格式——v0.0.7 已统一所有平台适配器返回扁平 `{bitstring: shots}` dict

### `v0.0.7.post1`

这是一个紧急补丁，修复 v0.0.7 引入或未覆盖的 10 个实际使用问题（#39–#48）：

- `uniqc simulate --backend density` 正确映射到 `densitymatrix` 后端
- `uniqc submit --dry-run` 不再因重复 `shots` 参数而报 TypeError
- `dry_run_task(backend="dummy")` 正常工作（DummyAdapter 已正确注册）
- `uniqc backend list --format json` 输出正确的 JSON
- `uniqc config validate` 不再误报 `active_profile` 元数据键
- `submit_batch` 的 dummy 模式不再遗留 RUNNING → FAILED 状态的任务
- `DummyResult.from_probabilities()` 用 `round()` 替代 `int()` 保证 shot 总数精确
- Python API 的 OriginQ / Quafu / IBM Token 从 YAML 配置文件读取
- `qiskit-ibm-provider` 已从 extras 中移除（与 qiskit ≥ 1.0 不兼容）
- `uniqc backend chip-display` 正确显示双比特门对的 `(u, v)` 标识符（不再全是 `0, 0`）
- OriginQ 模拟器后端（`full_amplitude` 等）现在可以通过 `submit_task` 正常使用

### `v0.0.5`

这是一次以"把上一轮结构调整真正打磨到可发布可安装"为目标的发布。

这版最明显的用户侧收益有四类：

- CLI 参数解析恢复为更自然的调用方式，不再容易把位置参数后的选项误判成子命令
- QASM / OriginIR / dummy / 结果展示这条链路上的几个实用 bug 被补齐，CLI 日常使用更顺手
- TorchQuantum 相关依赖改成真正按需，基础安装不会再因为发布元数据或导入链过早触发可选依赖而变脆
- 文档与回归测试一起补上，发布链路更接近"改完就能发、发了就能装"

如果你已经在用 `v0.0.4` 或 `v0.0.4.post1`，升级到这版时建议优先复核：

- 你是否有把 QASM 先转 OriginIR 再模拟的临时绕路脚本
- 你是否在脚本里手工处理 `task show` / `result` 的输出结构
- 你是否因为 TorchQuantum / qutip 缺失而遇到过"明明没用那个功能却导入失败"的情况

### `v0.0.4.post1`

这个版本是一次紧急性质更强的补丁发布，重点是修复 wheel 构建绑定错误 Python 解释器导致的 ABI 不匹配问题。

如果你之前遇到过"能装上 wheel，但导入扩展模块时 ABI / Python 版本不匹配"的现象，优先确认自己是否已经越过这一版。

### `v0.0.4`

这是一次带有明显结构调整的发布。升级时最值得先检查的是命令名、导入路径和任务缓存相关脚本。

升级时建议优先检查：

- 你的命令行调用是否还在使用 `uniq`
- 代码导入路径是否仍引用旧包名
- 是否有依赖旧任务缓存行为的本地脚本

### `v0.0.3`

这个版本主要修正发布链路里的版本识别问题。日常使用层面的变化不大，但和打包、CI、版本展示相关。

### `v0.0.1`

这个版本主要修复了 QASM parser 对 `if` 的误判问题。

## 具体版本变化参考

下面这部分会在文档构建时根据仓库里的 tag、提交标题和文件变化自动整理，适合用来查某个版本具体包含了哪些提交和改动范围。

```{include} _generated/strict_history.md
```
