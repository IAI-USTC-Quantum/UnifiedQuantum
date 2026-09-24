# Release Notes

这个页面汇总 UnifiedQuantum 的版本变化、升级时值得优先关注的调整，以及更完整的版本变化记录。

## 先看什么

如果你在跟随当前开发版，先看 ``v0.1.1``（**电路可视化引擎**：自研渲染内核
+ 7 种输出模式 + ``uniqc draw`` CLI；``visualization.draw/draw_html`` 弃用）；
如果你是从 ``0.0.x`` 直接升级，**先看 ``v0.1.0`` 的迁移部分**——逐项迁移对照见
[0.1.0 迁移指南](migration_0.1.0.md)。

升级到 ``v0.1.1`` 时最值得先确认的是：

- **你是否在用旧的绘图入口。** ``uniqc.visualization.draw()`` / ``draw_html()``
  已弃用（``0.2.0`` 移除），改用 {py:meth}`Circuit.draw(...) <uniqc.circuit_builder.qcircuit.Circuit.draw>`、
  {py:func}`uniqc.visualization.render(...) <uniqc.visualization.circuit_render.render>` 或 [`uniqc draw`](../4_cli/draw.md) CLI；新的 ``text``
  模式由自研渲染器输出，不再委托 pyqpanda3（Python 3.14 可用）。
- **其余变更对用户透明**：新渲染引擎是纯增量能力，旧 OriginIR / QASM /
  提交工作流不受影响。

## 弃用政策（0.1.0 兼容性悬崖）

```{toctree}
:maxdepth: 1

deprecation_policy
migration_0.1.0
```

[弃用政策（0.1.0 兼容性悬崖）](deprecation_policy.md) 详细说明：所有在 ``0.0.x``
中通过 ``DeprecationWarning`` 标记的公共 API，将在 ``0.1.0`` 中移除或不再保证兼容性。
**0.1.0 已按该政策完成全部移除**，逐项迁移对照见
[0.1.0 迁移指南](migration_0.1.0.md)。

## 发布验证报告

```{toctree}
:maxdepth: 1

reports/0.1.0
reports/0.0.17.post1
reports/0.0.17
reports/0.0.16
```

## 发布前可验证路径检查

在创建新的 ``v*`` tag 前，维护者必须完成一次人工可验证路径检查，确认用户主路径没有失效。
具体清单见 ``.agents/skills/uniqc-test-before-release/SKILL.md``。文档系统里这条路径
对应的是：

```bash
cd docs
uv run make html       # 触发完整 pre-doc-execution + sphinx 编译
```

只有所有 ``examples/<chapter>/*.py`` 都 pass（或合理地 skip）才能发布。

## 版本解读

### `v0.1.1`（电路可视化引擎）

这是一个**功能增强版本**，核心主题是**自研电路可视化引擎**：一个布局内核
驱动 7 种输出模式，取代此前委托 pyqpanda3 的字符画绘制。

本版主要变更：

- **新渲染引擎**（``uniqc/visualization/circuit_render/``）：``text``
  （ASCII/Unicode 字符画，自研、不依赖 pyqpanda3、Python 3.14 可用）、
  ``svg``、``png``、``mpl``、``latex``（quantikz 源码）、``html`` 与
  ``interactive``（点击查看门详情）7 种模式；4 套皮肤（默认 ``quantikz``、
  ``qiskit``、``modern``、``print``）、明暗主题、按行折叠、横竖排布、
  比特序翻转、π 分数/小数/符号/隐藏参数显示，以及完整 OriginIR-ext 覆盖
  （扩展门、``dagger``、``controlled_by``、符号参数、QRAM、错误信道、
  DEF 子例程、中途 MEASURE/RESET、经典指令、QIF/QWHILE 括号）。
- **入口**：``Circuit.draw(mode, ...)``、Jupyter ``_repr_svg_`` 富显示、
  ``print(circuit)`` 字符画、模块级 ``uniqc.visualization.render(...)``、
  以及新 CLI 子命令 ``uniqc draw <file>``。
- **弃用**：``uniqc.visualization.draw()`` / ``draw_html()``（含
  ``uniqc.compile.draw`` re-export）改为发出 ``DeprecationWarning`` 的包装，
  **0.2.0 移除**；改用 ``uniqc.visualization.render()`` 或 ``Circuit.draw()``。

如果你正在从 ``v0.1.0`` 迁移，主要变更对用户透明（除非你在用旧绘图入口，
见上文迁移说明）。

已知缺口（不阻塞发布，维护者已确认接受）：

- OriginQ 实时后端发现因配置的 token 被上游拒绝（``Unauthorized``）失败；
  stale 缓存回退可用，后端列表 / ``backend show`` / dry-run / chip-display
  （缓存模式）不受影响；
- 验证环境的 IBM 账号被 IBM Quantum 上游封锁（凭据问题，非代码缺陷）；
- 本轮未提交真实量子任务（未获配额授权），以全平台发现 + dry-run 覆盖；
- Gateway 前端仅经 HTTP / 构建产物验证（验证机无浏览器自动化）。

**发布验证结果**（2026-09-19，commit ``ab3e401``）：结论
**RELEASE WITH KNOWN GAPS**。默认测试套件 2520 passed / 0 failed；
best-practices 文档门禁 12/12、全量示例 55/55；Sphinx 构建成功（新增
1 条 ``draw.md`` myst 锚点警告，非阻塞）；CLI 17 组 help 与文档精确一致；
Gateway 前端构建 + API 全通；Quark / TianYan / LogicalQubit 实时发现
通过。发布验证工件（``RELEASE_REPORT_0.1.1.md`` /
``RELEASE_EXECUTION_PLAN_0.1.1.md``）自本版起为本地文件，不再入库。

### `v0.1.0`（弃用政策落地 + 纯 Python 打包）

这是一个**破坏性变更版本**，核心主题是**弃用政策落地**与**C++ 模拟器独立打包**。

本版主要变更：

- **移除全部 `0.0.x` 弃用 API**（逐项对照见 [0.1.0 迁移指南](migration_0.1.0.md)）：
  Quafu 平台（BAQIS 芯片改用 ``quark:<chip>``）、``uniqc.simulator.get_backend()``
  （改用 {py:func}`get_simulator() <uniqc.simulator.get_backend.get_simulator>` / {py:func}`create_simulator() <uniqc.simulator.get_backend.create_simulator>`）、``IBMAdapter``
  （改用 {py:class}`QiskitAdapter <uniqc.backend_adapter.task.adapters.qiskit_adapter.QiskitAdapter>`）、平台 task-id 回退查询、12 个算法 building block
  的 in-place 形式（改用 {py:meth}`circuit.add_circuit(fragment) <uniqc.circuit_builder.qcircuit.Circuit.add_circuit>`）。
- **C++ 模拟器拆分为独立包** ``uniqc-cppsimulator>=1.0.1,<2``：主包变为纯
  Python wheel，源码构建不再需要 CMake / C++ 工具链；import 名 ``uniqc_cpp``
  不变，Python 侧用法无感。
- **``[quark]`` 回归 ``[all]``**：上游 ``quarkstudio`` / ``quarkcircuit`` /
  ``srpc`` 已发布 Linux/macOS/Windows wheel（含 cp314），仅要求 Python ≥ 3.12。
- **新增**：``~/.uniqc/config.yaml`` schema 版本化（``config_version`` 自动迁移）；
  ``uniqc sync upload``（confsync 凭据同步）；Quark / TianYan / LogicalQubit
  chip characterization（``uniqc backend chip-display`` 全平台打通）；
  ``classical_shadow()`` 新增 ``seed`` 参数。
- **修复**：dry-run 校验线路比特对芯片（Quark 离线、TianYan/LogicalQubit 走
  芯片缓存）；TianYan 发现的比特数不再取型号名；Quark ``wait_for_result``
  解包嵌套 histogram；TianYan 平台 task id 解包；LogicalQubit 发现状态归一化；
  提交编译在发现缓存缺少拓扑时回退芯片缓存。
- **文档基建**：示例执行全面确定化（固定种子 + task id/时间戳归一化 +
  确定性 SVG），``example-exec-logs/`` 的内容性 diff 现在可靠地代表真实行为变化。

已知缺口（不阻塞发布，维护者已确认接受）：

- OriginQ 实时后端发现在上游 ``pyqpanda3`` 0.4.1（PyPI 最新）中失败
  （``QCloudService.backends()`` 抛 ``RuntimeError``）；本地自动回退 stale
  缓存，后端列表 / dry-run / chip-display（有缓存时）均不受影响；
- 验证环境的 IBM token 被 IBM Quantum 拒绝（凭据问题，非代码缺陷）；
- 本轮未提交真实量子任务（未获配额授权），以全平台发现 + dry-run 覆盖。

**发布验证结果**：见 [0.1.0 发布验证报告](reports/0.1.0.md) —— 结论
**RELEASE WITH KNOWN GAPS**。默认测试套件 2488 passed / 0 failed；
best-practices 示例 12/12 通过；Sphinx 0 警告；CLI 17 组 help 与文档一致；
Gateway 前端构建 + API 全通；Quark / TianYan / LogicalQubit 实时发现与
dry-run 通过。

### `v0.0.17.post1`（快速修复）

`v0.0.17` 之后的热修复版本，包含两项内容：

- **`uniqc sync`**：把 `~/.uniqc/config.yaml` 中的平台凭据与 Infisical
  密钥管理项目同步（`sync setup / status / push / pull`），用于多台机器
  共享或恢复凭据。详见[凭据同步 (`uniqc sync`)](../4_cli/sync.md)。
- **修复 OriginQ 真机任务结果为空**（issue #119）：`WK_C180` 等芯片的
  FINISHED 任务在 `get_counts()` 路径下返回空计数的问题，现回退解析
  原始 `probCount` 数据；本地任务库中已记录为"成功但结果为空"的旧任务
  在下次查询时自动重新拉取恢复。

完整验证结果见 [0.0.17.post1 Hotfix Release Validation](reports/0.0.17.post1.md)。

### `v0.0.17`（Release Candidate）

这是 v0.1.0 前的梳理性稳定版本：统一 gate semantics、补齐 task lifecycle
持久化、修复 VQD/PyTorch/HEA 路径，并把 docs、Ruff、example freshness、Skill
smoke 与双仓 contract parity 变成 blocking gate。

完整验证结果见 [0.0.17 Release Candidate Validation](reports/0.0.17.md)。

### `v0.0.16`

这是一个功能增强版本，核心主题是**用户自定义含噪虚拟机**与**统一后端状态目录**。

本版主要变更：
- **用户自定义含噪虚拟机**（``dummy:virtual:<name>``）：在 ``~/.uniqc/backend/virtual/``
  下用 YAML 声明比特数、耦合拓扑和分层错误模型——统一 depolarizing、按门类型 /
  按门实例覆盖、T1/T2 热弛豫（由门时长换算为振幅阻尼 + 退相位）、逐比特读出错误——
  之后任何接受 backend id 的位置都可使用（``submit_task(...,
  backend="dummy:virtual:<name>")``、[`uniqc submit`](../4_cli/submit.md)、标定工作流）。新模块
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

**发布验证结果**：见 [0.0.16 发布验证报告](reports/0.0.16.md) —— 结论
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
  `DeprecationWarning` 的公共 API **已在 `0.1.0` 中移除**（包括
  `simulator.get_backend()`、`IBMAdapter`、Quafu 平台、平台 task id 回退，
  以及所有 `*_circuit(circuit, ...)` in-place 形式）。迁移对照见
  [0.1.0 迁移指南](migration_0.1.0.md)；政策框架详见
  [弃用政策（0.1.0 兼容性悬崖）](deprecation_policy.md)。
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
| `[pytorch]` | ✅ 可用 | torch 与 torchquantum-ng 通过 cp314 安装/运行矩阵 |
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
