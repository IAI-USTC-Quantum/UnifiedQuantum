# Release Notes

这个页面汇总 UnifiedQuantum 的版本变化、升级时值得优先关注的调整，以及更完整的版本变化记录。

## 先看什么

如果你在跟随当前开发版，先看 ``Unreleased``；如果你是从较早的正式版本直接升级，
**先看 ``v0.0.16``**——这一版新增**用户自定义含噪虚拟机**（``dummy:virtual:<name>``），
并把后端发现缓存与芯片缓存统一收拢到 ``~/.uniqc/backend/``。

升级到 ``v0.0.16`` 时最值得先确认的是：

- 你是否有脚本直接读写旧的缓存路径。后端发现缓存从 ``~/.uniqc/cache/backends.json``
  迁到 ``~/.uniqc/backend/backends.json``，芯片缓存从 ``~/.uniqc/backend-cache/``
  迁到 ``~/.uniqc/backend/chips/``。首次访问会**自动迁移**，正常使用无感；但如果
  你在脚本里硬编码了旧路径，请改读新路径。
- 你是否需要"自定义拓扑 + 自定义噪声模型"的本地含噪测试。新写法：
  ``uniqc backend virtual init <name>`` 在 ``~/.uniqc/backend/virtual/<name>.yaml``
  生成配置模板，编辑后用 ``uniqc backend virtual validate <name>`` 校验，之后任何
  接受 backend id 的地方都能写 ``dummy:virtual:<name>``（例如
  ``uniqc submit ... --backend dummy:virtual:<name>``）。配置好的机器在
  ``uniqc backend list`` 和 WebUI 中显示为 ``virtual:<name>``。
- 沿用 ``v0.0.13``–``v0.0.15`` 的升级检查仍然适用：``uniqc submit`` 只用
  ``--backend <provider>:<chip>``（无 ``--platform``，缺省 ``dummy:local:simulator``）；
  ``pip install unified-quantum[all]`` 不含 ``[quark]``，也不再有 ``[quafu]`` extra；
  ``qiskit`` 已是核心依赖；所有在 ``0.0.x`` 触发 ``DeprecationWarning`` 的公共 API
  将在 ``0.1.0`` 移除；环境自检用 ``uv run uniqc doctor``。

## 弃用政策（0.1.0 兼容性悬崖）

```{toctree}
:maxdepth: 1

deprecation_policy
```

[弃用政策（0.1.0 兼容性悬崖）](deprecation_policy.md) 详细说明：所有在 ``0.0.x``
中通过 ``DeprecationWarning`` 标记的公共 API，将在 ``0.1.0`` 中移除或不再保证兼容性。
跨越 ``0.0.x → 0.1.0`` 升级前，请清理所有 ``DeprecationWarning``。

## 发布前可验证路径检查

在创建新的 ``v*`` tag 前，维护者必须完成一次人工可验证路径检查，确认用户主路径没有失效。
具体清单见 ``.claude/skills/uniqc-test-before-release/SKILL.md``。文档系统里这条路径
对应的是：

```bash
cd docs
uv run make html       # 触发完整 pre-doc-execution + sphinx 编译
```

只有所有 ``examples/<chapter>/*.py`` 都 pass（或合理地 skip）才能发布。

## 版本解读

### `v0.0.16`

这是一个功能增强版本，核心主题是**用户自定义含噪虚拟机**与**统一后端状态目录**。

本版主要变更：
- **用户自定义含噪虚拟机**（``dummy:virtual:<name>``）：在 ``~/.uniqc/backend/virtual/``
  下用 YAML 声明比特数、耦合拓扑和分层错误模型——统一 depolarizing、按门类型 /
  按门实例覆盖、T1/T2 热弛豫（由门时长换算为振幅阻尼 + 退相位）、逐比特读出错误——
  之后任何接受 backend id 的位置都可使用（``submit_task(...,
  backend="dummy:virtual:<name>")``、``uniqc submit``、标定工作流）。新模块
  ``uniqc.backend_adapter.virtual_machine`` 提供严格校验（未知键、概率范围、拓扑
  一致性、``T2 <= 2*T1``、读出对形状），报错信息带文件路径；新错误模型
  ``uniqc.simulator.ThermalRelaxation``；新 CLI 组 ``uniqc backend virtual
  init|list|show|validate``。详见 [含噪虚拟机](../2_advanced/virtual_backends.md)。
- **统一后端状态目录** ``~/.uniqc/backend/``：后端发现缓存（``backends.json``）与
  芯片表征缓存（``chips/``）统一收拢，旧路径（``~/.uniqc/cache/backends.json``、
  ``~/.uniqc/backend-cache/``）在首次访问时自动迁移。

如果你正在从 ``v0.0.15`` 迁移，主要变更对用户透明：
- 现有 ``dummy`` / ``dummy:local:*`` / ``dummy:<platform>:<backend>`` 写法不变；
- 缓存自动迁移，无需手工移动文件；无新增弃用。

已知缺口（不阻塞发布）：
- 发布验证环境中 IBM token 被 IBM Quantum 拒绝（外部凭证问题）、Quark 未配置 token；
  本轮未提交真实量子任务（未获配额授权），以平台发现 + dry-run 覆盖；
- 开发者路径 ``uv sync`` 因 ``[quark]`` extra 的 ``quarkcircuit`` 标记在 uv 通用
  解析器下不可解（``v0.0.15`` 起已存在的既有问题）；用户安装路径
  ``uv pip install`` / ``pip install`` 不受影响。

**发布验证结果**：见仓库根目录 ``RELEASE_REPORT_0.0.16.md`` —— 结论
**RELEASE WITH KNOWN GAPS**。默认测试套件 2044 passed / 0 failed；文档示例全量执行
49 pass / 5 skip / 0 fail；CLI 与文档一致；含噪虚拟机特性经 CLI / Python API / WebUI /
含噪模拟全链路验证；Gateway 前端构建与 API 健康检查通过；OriginQ 实时发现正常
（7 backends + WK_C180 标定数据）。

### `v0.0.15`

v0.0.15 重点更新：**原生 PyTorch 参数集成**、**OriginIR-ext 超集语言**、
**弃用政策（0.1.0 兼容性悬崖）**、**Python 3.14 支持**。

升级到 ``v0.0.15`` 时最值得先确认的是：

- **你是否在用 `[quark]` extra。** 从本版起 `pip install unified-quantum[all]`
  **不再包含** `[quark]`。如需 Quark 平台支持，必须显式安装
  `pip install unified-quantum[quark]`，且仅限 **Python 3.12–3.13 + Linux / macOS**。
  这是打包契约变更（不是弃用警告），详见 [CHANGELOG](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/blob/main/CHANGELOG.md)。
- **你是否在用 Python 3.14。** 本版起支持 Python 3.14（`requires-python >= 3.10, < 3.15`），
  但 `[originq]` 和 `[quark]` 在 py3.14 上不可用（上游无 cp314 wheel）。
  芯片缓存路径（`dummy:originq:*`）在 py3.14 上仍然可用，仅实时云端连接需要
  对应 SDK。详见 [安装说明 - Python 3.14 注意事项](../0_quickstart/installation.md)。
- **你是否在用已弃用的 API。** 本版建立了项目级弃用政策：所有在 `0.0.x` 中触发
  `DeprecationWarning` 的公共 API **将在 `0.1.0` 中移除**。当前弃用清单包括：
  `simulator.get_backend()`、`IBMAdapter`、`quafu_adapter`、以及所有
  `*_circuit(circuit, ...)` in-place 形式。所有弃用警告消息现在都包含
  字面量 `"uniqc 0.1.0"`，方便 `grep` 和 `pytest.warns` 过滤。
  详见 [弃用政策（0.1.0 兼容性悬崖）](deprecation_policy.md)。
- **你是否在用 `Circuit` 的参数化功能。** 本版新增 `param_map` / `param_dict` /
  `has_param` / `set_param_last`，使 `torch.Tensor` 参数成为一等公民——
  通过 `add_gate` 传入的张量参数会自动注册为 `nn.Parameter` 并可通过名称访问。
  新增的 `simulator.expectation()` 跨后端可微期望值接口。
  详见新的最佳实践示例 `examples/3_best_practices/11_native_torch_training.py`。
- **你是否在手动拼接 OriginIR。** 本版正式区分 **OriginIR-ext**（UnifiedQuantum
  默认本地语言）与 **official OriginIR**（OriginQ 云端接受的子集）。OriginIR-ext
  在官方门集之上额外提供 `ECR`/`ISWAP`/`XX`/`YY`/`ZZ`/`XY`/`PHASE2Q`/`UU15`/
  `RPhi`/`RPhi90`/`RPhi180` 等扩展门、`QRAM` 指令、`DEF`/`ENDDEF` 子程序块、
  error channel 以及 inline `dagger` / `controlled_by(...)` 语法。需要提交到
  OriginQ 云时调用 `Circuit.to_originir_official()`（或对裸文本使用
  `uniqc.compile.convert_originir_ext_to_originir()`）即可严格分解回 official
  OriginIR。三种语言（official OriginIR / OriginIR-ext / OpenQASM 2.0）的
  完整关系详见 [OriginIR-ext 规范](../1_basic_usage/originir.md) 与
  [OriginIR、OriginIR-ext 与 OpenQASM 2.0 的关系](../1_basic_usage/originir_relationship.md)。
- **`dummy:originq:*` 路径不再需要 `pyqpanda3`。** 本版修复了一个 bug：当芯片
  缓存已存在时，chip-backed dummy 路径不再强制要求安装云 SDK。

#### Python 3.14 限制一览

| Extra | py3.14 状态 | 说明 |
|-------|-----------|------|
| `[originq]` | ❌ 不可用 | `pyqpanda3` 无 cp314 wheel |
| `[quark]` | ❌ 不可用 | `srpc`/`quarkcircuit` 无 cp314 标准 wheel |
| `[simulation]` | ✅ 可用 | QuTiP 已有 cp314 wheel |
| `[visualization]` | ✅ 可用 | matplotlib 已有 cp314 wheel |
| `[pytorch]` | ✅ 可用 | torch 已有 cp314 wheel |
| `[all]` | ✅ 可用 | 不再包含 `[quark]` |

### `v0.0.14`

这是一个功能增强版本，核心主题是**变分算法工具包扩展与跨平台提交统一化**。

本版主要变更：
- **`UnifiedOptions` 跨平台提交选项**：新增 `UnifiedOptions` 数据类，支持一次编写、多平台提交，自动翻译为各平台的 `BackendOptions`。
- **Ansatz 模块大幅扩展**：新增 HVA（硬件变分 Ansatz）、ADAPT-VQE、QAOA 变体、HEA 可配置拓扑与旋转门、硬件感知 ansatz 自动选择等。`Parameter` / `Parameters` 类实现符号化参数管理。
- **QASM2 IR 分解**：新增 `decompose_to_qasm2()`，支持跨平台提交时的 OpenQASM 2.0 网关分解。
- **文档重构**：算法示例独立为第 8 章，新增 TorchQuantum 与 matplotlib 图例，所有图例改用 SVG 格式。

修复项：
- ADAPT-VQE Pauli 字符串解析（长度不匹配问题）
- `build_docs --only` 不再覆盖 `index.json`
- Windows 时钟精度导致缓存年龄为负值

如果你正在从 `v0.0.13` 迁移，主要变更对用户透明：
- API 向后兼容，无需修改现有代码
- 新增的 `UnifiedOptions` 是可选的，现有 `BackendOptions` / `**kwargs` 调用不变

## 具体版本变化参考

下面这部分会在文档构建时根据仓库里的 tag、提交标题和文件变化自动整理，适合用来查
某个版本具体包含了哪些提交和改动范围。

```{include} _generated/strict_history.md
```
