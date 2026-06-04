# Deprecation policy（弃用政策）

UnifiedQuantum 使用 [SemVer 2.0.0](https://semver.org/lang/zh-CN/)
进行版本管理。本页说明项目在 `0.0.x → 0.1.0` 升级窗口内的兼容性承诺
与弃用流程。所有维护者、贡献者、下游用户都应以此为准。

> **TL;DR**：任何在 `0.0.x` 中触发
> [`DeprecationWarning`](https://docs.python.org/3/library/exceptions.html#DeprecationWarning)
> 的公共 API，**在 0.1.0 中会被移除或不再保证兼容性**。
> 想要安全跨过 0.1.0 边界，请在 0.0.x 期间清理所有
> `DeprecationWarning`。

## 0.1.0 兼容性悬崖

**所有当前在 `0.0.x` 中被标记为 `DeprecationWarning` 的公共 API
（包括类、函数、关键字参数、CLI 选项、配置键、URL 路由）在
`0.1.0` 中会被彻底移除，或者不再保证与 `0.0.x` 的行为兼容。**

具体含义：

- `0.0.x → 0.0.y`：**强兼容承诺**。任何被
  `DeprecationWarning` 标记的旧 API 在所有 `0.0.x` 子版本内都会
  保留原行为，方便用户迁移。
- `0.0.x → 0.1.0`：**断点升级**。旧 API 可能直接
  从代码库中删除，或者改为只保留同名占位实现而抛 `NotImplementedError`。
  调用旧形式的代码可能会以编译错误、运行时报错或语义改变的方式失败。
- `0.1.0 之后`：除非另有声明，0.1.0 才是
  正式 “new API only” 的起点，后续版本将按 SemVer 正常承诺。

未来若在 0.0.x 末期再引入新的 `DeprecationWarning`，**这些新增弃用项
同样适用 0.1.0 悬崖**，除非随附条目明确给出更晚的删除版本。

## 公共 API 的定义

下述范围视为 **公共 API**，受兼容性政策约束：

- 直接通过 `from uniqc import X` 暴露的符号
  （见 [`uniqc/__init__.py`](../6_api/uniqc.rst)）。
- 任何在 [API 参考](../6_api/uniqc.rst) 中已有文档的子模块、类、
  函数、属性。
- `uniqc` CLI 已经在 `--help` 中列出的子命令、选项、参数。
- 网关 HTTP API 中以 `/api/...` 暴露的稳定路由。
- `~/.uniqc/config.yaml` 配置文件中的稳定配置键。

下述范围 **不是公共 API**，没有兼容性承诺，**随时可以变化**：

- 以单下划线开头的对象（如 `uniqc._deprecation`、`Adapter._delegate`）。
- `uniqc.test.*` 测试套件内部。
- 任何标注 “internal / experimental / unstable” 的对象。
- 未在 API 参考中出现的子模块（例如 `uniqc.algorithms._compat`）。

依赖私有对象等同于自担风险——Hyrum's Law 不在我们承诺范围内。

## 当前进入 0.1.0 悬崖的 API 清单

下面是 `0.0.15` 时刻已经触发 `DeprecationWarning` 的全部 API。
**全部条目都将在 `0.1.0` 中删除或不再保证兼容。**

### 模拟器

- `uniqc.simulator.get_backend()` —— 改用
  {func}`uniqc.simulator.get_simulator` 或 {func}`uniqc.simulator.create_simulator`。

### 后端 / 适配器

- `uniqc.backend_adapter.task.adapters.ibm_adapter.IBMAdapter`
  —— 改用 `QiskitAdapter`（同样基于 `qiskit-ibm-runtime`）。
- 整个 `uniqc.backend_adapter.task.adapters.quafu_adapter` 模块
  —— Quafu 平台支持已停止维护，`[quafu]` 安装 extra 已被移除。
- 通过平台原生 task id（非 `uqt_*`）查询任务的回退路径
  （位于 `uniqc.backend_adapter.task_manager`）—— 改用 uniqc 内部 task id。

### 算法构件（in-place 旧形式）

下列 `*_circuit(circuit, ...)` in-place 写法均已弃用，
请改用 fragment 形式
`*_circuit(n_qubits, ...) -> Circuit` 再
`circuit.add_circuit(fragment)`：

- `qft_circuit(circuit, ...)`
- `deutsch_jozsa_circuit(circuit, oracle, ...)`
- `dicke_state_circuit(circuit, ...)`
- `thermal_state_circuit(circuit, ...)`
- `cluster_state(circuit, ...)`、`ghz_state(circuit, ...)`、`w_state(circuit, ...)`
- `amplitude_estimation_circuit(circuit, oracle, ...)`
- `grover_oracle(circuit, marked_state, ...)`
- `grover_diffusion(circuit, ...)`
- `grover_operator(circuit, oracle, ...)`
- `vqd_circuit(circuit, ansatz_params, prev_states, ...)`

以及关键字参数：

- `grover_diffusion(..., ancilla=...)` —— 该参数无效果，请直接删掉。

## 弃用流程（针对维护者）

引入新的 `DeprecationWarning` 时，按以下步骤操作：

1. **使用集中辅助函数**：调用
   {func}`uniqc._deprecation.warn_removed_in_0_1_0`，
   不要手写 `warnings.warn(..., DeprecationWarning, ...)`。
   这样所有消息都包含字符串 `"uniqc 0.1.0"`，方便统一搜索与
   迁移工具识别。
2. **在 docstring 顶部加 `.. deprecated::` 指令**，写明替代方案。
3. **在本页“当前进入 0.1.0 悬崖的 API 清单”补一条**，
   说明何时弃用、替代方案、删除版本（默认就是 0.1.0）。
4. **在 `CHANGELOG.md` 的 `Deprecated` 小节登记**。
5. **保留行为不变**：除非这次提交是真的把弃用项删掉，
   否则不要修改旧路径的可观察行为。
6. **加测试覆盖弃用警告**：用 `pytest.warns(DeprecationWarning, match="uniqc 0.1.0")`
   验证旧路径同时仍然返回正确结果。

## 不属于弃用的兼容性变更

下列变化 **不通过 `DeprecationWarning` 表达**，
而是直接在 CHANGELOG 中以 “Changed” / “Removed” 条目公告：

- **打包变更**：例如 `pip install unified-quantum[all]` 不再
  包含 `[quark]` 子集。这是包级别的安装契约变更，没有运行时旧 API 入口。
- **环境变更**：Python 版本支持范围、第三方依赖最低版本、平台 wheel
  覆盖等。这些以 CHANGELOG + 安装文档为准。
- **错误信息措辞**：异常类型保持兼容，但 `str(exc)` 不在兼容承诺内。
- **日志格式**：`logging` / Rich 输出仅供人类阅读，不作机器消费契约。

---

## English summary

UnifiedQuantum follows SemVer 2. **Any public API that emits
`DeprecationWarning` during a `0.0.x` release is on track to be removed
(or its behaviour will no longer be guaranteed compatible) in `0.1.0`.**
There is **no compatibility guarantee for deprecated APIs across the
`0.0.x → 0.1.0` boundary.** Within the `0.0.x` line, all currently-deprecated
APIs continue to work unchanged.

“Public API” means: anything importable from `uniqc.*` and documented in
the API reference, the `uniqc` CLI subcommands and options shown in
`--help`, stable HTTP routes under `/api/...`, and stable keys in
`~/.uniqc/config.yaml`. Everything under a leading underscore, anything
in `uniqc.test.*`, and anything marked internal/experimental has **no
compatibility guarantee** (Hyrum's Law does not apply).

Packaging changes (e.g. the contents of the `[all]` extra) and supported
Python versions are announced via the `CHANGELOG.md` only — they are not
`DeprecationWarning`s but are still subject to clear migration notes.

The full list of APIs scheduled for removal in `0.1.0` is the bulleted
list above (`当前进入 0.1.0 悬崖的 API 清单`).
