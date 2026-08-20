(advanced-adding-a-platform)=
# 添加一个新云平台

本文档是"给 UnifiedQuantum 接入一个新量子云平台"的端到端开发指南，以本次
`tianyan`（天衍量子计算云平台）与 `logicalqubit`（逻辑比特超导量子云平台）
的接入为实例。阅读前请先熟悉 [云平台适配器架构](adapter_architecture.md)。

```{note}
本文描述的是**开发侧** checklist。如果你只是想**使用**某个已接入的平台，
请看 [平台文档](../platforms/index.md)。
```

(advanced-adding-a-platform-overview)=
## 总览

UnifiedQuantum **没有插件机制**：平台名硬编码在一组注册表、枚举和映射表里。
新增一个平台意味着在核心层、配置层、外围（CLI / Gateway / 前端 / 打包 /
测试 / 文档）各登记一遍。漏掉任何一处，平台会在某条路径上"半可见"——例如
能提交但 `uniqc backend list` 不列出，或 `uniqc doctor` 不检查其 SDK。

下面按层给出完整 checklist。文中以 `<p>` 表示新平台的小写标识符
（如 `tianyan`），以 `<P>` 表示类名前缀（如 `Tianyan`）。

(advanced-adding-a-platform-core)=
## 核心层：`uniqc/backend_adapter/`

### 1. `task/adapters/<p>_adapter.py` —— QuantumAdapter 实现

新建适配器类，继承
{mod}`uniqc.backend_adapter.task.adapters.base` 的 `QuantumAdapter`，实现：

| 方法 | 职责 |
|------|------|
| `translate_circuit(originir)` | OriginIR → 平台原生格式（如 tianyan 的 QCIS） |
| `submit(circuit, *, shots, **kwargs)` | 提交单个线路，返回任务 ID |
| `submit_batch(circuits, *, shots, **kwargs)` | 批量提交 |
| `query(taskid)` | 返回统一 `{"status": "success"/"failed"/"running", "result": ...}` |
| `query_batch(taskids)` | 批量查询，状态按 `failed` > `running` > `success` 合并 |
| `is_available()` | SDK / 凭证层面的可用性检查 |
| `list_backends()` | 返回平台后端原始列表（供 registry 归一化） |
| `dry_run(originir, *, shots, **kwargs)` | 离线校验，返回 `DryRunResult` |

```{warning}
`dry_run()` **必须是纯离线的**——不允许任何网络调用、不允许读取云端状态。
它只做本地可判定的校验（语法、门集、shots 上限等）。任何 dry-run 通过
但实际提交失败的情况都视为 critical bug。
```

平台 SDK（如 `cqlib`、`lqcloud`）一律在方法内部或 `__init__` 中通过
`optional_deps.require()` 懒导入，禁止模块顶层 `import`，否则未装
对应 extra 的用户连 `import uniqc` 都会变慢或报错。

### 2. `backend.py` —— Backend 薄壳

新增 `<P>Backend(QuantumBackend)` 子类：只需设置 `platform` 类变量与
`_adapter_class`，再登记进模块底部的 `BACKENDS` 注册表，使
`get_backend("<p>")` / `get_backend("<p>:<chip>")` 可用。

### 3. `backend_info.py` —— Platform 枚举

在 `Platform` 枚举中新增成员 `<P> = "<p>"`。`parse_backend_id()`、
CLI、Gateway 全部以该枚举为准。

### 4. `circuit_adapter.py` —— CircuitAdapter

新增 `<P>CircuitAdapter(CircuitAdapter[T])`，实现 `adapt(circuit)`：
把内部 `Circuit` 转为平台提交所需类型（字符串或 SDK 线路对象）。

### 5. `backend_registry.py` —— 后端归一化与适配器构造

- 新增 `_normalise_<p>(raw)`：把 `list_backends()` 的原始输出归一化为
  `BackendInfo` 列表（name / num_qubits / topology / status /
  is_simulator / is_hardware / extra / 标定数据字段）。
- 把 `_normalise_<p>` 登记进 `_NORMALISERS`。
- 在 `_build_adapter()` 中新增 `Platform.<P>` 分支（懒导入适配器）。

### 6. `task_manager.py` —— 提交路径接线

- `ADAPTER_MAP["<p>"] = <P>CircuitAdapter`：让 `submit_task(backend="<p>:<chip>")`
  找到线路转换器。
- `_PLATFORM_CHIP_KWARG["<p>"] = "<chip 参数名>"`：`backend="<p>:<chip>"`
  中的 chip 部分会以这个参数名注入到 adapter 的 `submit()` kwargs
  （例如 `backend_name` 或 `chip_id`）。

### 7. 其余核心文件

| 文件 | 要做的修改 |
|------|-----------|
| `task/options.py` | 新增 `<P>Options` dataclass 并接入 `BackendOptionsFactory` |
| `task/normalizers.py` | 新增 `normalize_<p>()`（平台原始结果 → `UnifiedResult`），并加入 `__all__` |
| `task/optional_deps.py` | 新增 `check_<p>()` 与 `<P>_AVAILABLE`（基于 `_can_import()`） |
| `task/adapters/__init__.py` | 在 `__getattr__` 中懒导出 `<P>Adapter`（不要顶层 import，避免硬依赖 SDK） |
| `preflight.py` | `PROVIDER_INSTALL_HINTS["<p>"]` 加安装提示；凭证探测分支调用 `load_<p>_config()` |

(advanced-adding-a-platform-config)=
## 配置层：`uniqc/config.py`

所有凭证统一走 `~/.uniqc/config.yaml` 的 active profile，懒加载，
不接受环境变量注入。需要修改：

- `SUPPORTED_PLATFORMS`：加入 `"<p>"`。
- `PLATFORM_REQUIRED_FIELDS`：声明必填凭证字段
  （如 tianyan 的 `["login_key"]`、logicalqubit 的 `["api_key"]`）。
- `PLATFORM_KNOWN_FIELDS`：声明全部合法字段，用于 `validate_config()`
  的"未知字段"告警（如 logicalqubit 还需包含可选的 `url`）。
- `DEFAULT_CONFIG`：给 `<p>` 一节加空模板。
- 新增 `load_<p>_config()`：缺凭证时抛出带 `uniqc config set <p>.<field>`
  提示的 `ImportError`。
- `has_platform_credentials()`：若平台的凭证字段名不是 `token`
  （如 `login_key` / `api_key`），需要在这里加分支——当前实现里
  quark 的 `QUARK_API_KEY` 就是这类特判的范例。

(advanced-adding-a-platform-peripheral)=
## 外围接线

| 位置 | 修改内容 |
|------|---------|
| `uniqc/cli/config_cmd.py` | 平台白名单元组（`config set` 校验、`config get` 参数、`config list` 遍历）与默认模板 |
| `uniqc/cli/doctor.py` | SDK 探测表加 `("<p>", ["<sdk_module>"])` |
| `uniqc/cli/backend.py` | `--platform` 帮助文案补 `<p>` |
| `uniqc/gateway/api/backends.py` | `/refresh` 路由的默认 targets 列表加 `Platform.<P>` |
| `frontend/src/pages/BackendsPage.tsx` | `PLATFORM_LABELS` 与 `DEFAULT_PLATFORM_FILTERS` 加新平台 |
| `pyproject.toml` | `[project.optional-dependencies]` 加 `<p> = ["<sdk>..."]` extra；必要时同步 `[all]` |
| `pytest.ini` | 加 `requires_<p>_credentials` marker；凭证型测试统一打这个标 |
| 文档 | 本节、[平台约定](../1_basic_usage/platform_conventions.md)、[平台章节](../platforms/index.md)、`README.md` / `README_en.md` |

(advanced-adding-a-platform-pitfalls)=
## 约定与坑

- **凭证懒加载**：adapter 构造时不读配置，首次真正需要（submit / list_backends）
  时才调用 `load_<p>_config()`。这样未配置该平台用户的其它功能不受影响。
- **SDK 懒导入**：同上，一律经 `optional_deps.require()` / `check_<p>()`。
  缺失时报 `MissingDependencyError`，提示语里给出
  `pip install unified-quantum[<p>]`。
- **backend 标识符**：用户侧一律 `backend="<platform>:<chip>"`；裸平台名
  在云提交路径上被拒绝并提示可用 chip 列表。chip 参数名经
  `_PLATFORM_CHIP_KWARG` 注入，用户显式传入的同名 kwargs 永远优先。
- **bitstring endianness**：normalizer 必须把平台原始结果改写为统一的
  cbit 框架——bitstring **最右字符对应 `c[0]`**（第一次 `measure()` 写入的
  classical bit），与平台原生顺序无关。这条约定由
  `uniqc/test/test_endianness_convention.py` 回归保护，新平台必须接入同一
  测试。详见 {ref}`平台约定的 2.6 节 <platform-bit-endianness>`。
  实例：tianyan 的结果按测量比特标签序归一、logicalqubit 原生为 qiskit
  风格大端 bitstring，两者都在各自的 `normalize_<p>()` 里完成改写。
- **废弃平台的 special-case**：参考 quafu 的做法——保留枚举与 adapter 以兼容
  存量代码，但在 `fetch_all_backends_with_status()` 中跳过、`optional_deps.require()`
  里给硬编码安装提示、使用时发 `DeprecationWarning`。新平台**不要**复制这些分支，
  它们只是历史包袱的隔离层。
- **`is_available()` ≠ 网络探活**：只做本地可判定检查（SDK 可导入、凭证存在），
  网络故障交给提交/查询路径报错。

(advanced-adding-a-platform-example)=
## 实例：tianyan 与 logicalqubit

本次接入的两个平台覆盖了 checklist 的每一行，可作为模板对照阅读：

| 维度 | tianyan（天衍） | logicalqubit（逻辑比特） |
|------|----------------|--------------------------|
| SDK | `cqlib`（extra `[tianyan]`） | `lqcloud>=0.4.2`（extra `[logicalqubit]`） |
| 凭证字段 | `tianyan.login_key` | `logicalqubit.api_key`（+ 可选 `logicalqubit.url`） |
| 线路格式 | QCIS | qiskit 风格门集 |
| 结果归一化 | 按测量比特标签序归一为 counts | qiskit 大端 bitstring → 统一 cbit 框架 |
| 特殊限制 | 仿真机分全振幅/单振幅/稳定子/张量网络等多种 | 单次 shots ≤ 50000 |

用户侧用法见各平台页面：[天衍 tianyan](../platforms/tianyan.md)、
[逻辑比特 logicalqubit](../platforms/logicalqubit.md)。
