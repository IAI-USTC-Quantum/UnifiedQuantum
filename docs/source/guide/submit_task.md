# 提交任务到量子云平台 {#guide-submit-task}

## 什么时候进入本页 {#guide-submit-task-when-to-read}

当你已经完成本地线路构建，并且已经通过 [快速上手](quickstart.md) 或 [本地模拟](simulation.md) 跑通了最小示例，接下来如果你希望：

- 把线路提交到云平台或真机执行
- 查询远端任务状态与执行结果
- 比较不同平台的接入方式与适用场景

就应该进入本页。

本页讨论的是**远端任务提交路径**，它解决的是"如何把已经在本地验证过的线路交给外部平台执行"的问题，而不是"如何在本地验证线路是否正确"。

## 本页解决的问题 {#guide-submit-task-problems}

- 什么时候应从本地模拟切换到提交任务路径
- 提交到云平台前需要准备哪些配置
- 不同平台各自适合什么场景
- 如何提交任务、查询状态并获取结果
- 使用远端平台前需要先了解哪些边界与限制

## 前置条件

阅读本页前，默认你已经完成以下至少一项：

- 已经完成 [快速上手](quickstart.md) 中的最小示例
- 已经会使用 `Circuit` 构建线路，并能导出 `originir` 或 `qasm`
- 已经通过 [本地模拟](simulation.md) 对线路做过基本验证

如果你还不确定线路是否正确、输出是否合理，建议先留在本地模拟路径，不要直接进入远端提交。

## 通用流程 {#guide-submit-task-flow}

无论选择哪个平台，远端任务提交通常都遵循以下流程：

1. **准备线路** —— 确认你已经有可提交的 `Circuit` 对象
2. **选择平台** —— 根据目标平台、依赖、成熟度与接入条件决定使用哪个后端
3. **准备配置** —— 通过环境变量配置 Token
4. **提交任务** —— 调用 `submit_task()` 提交任务
5. **查询结果** —— 通过 `wait_for_result()` 或 `query_task()` 获取结果

与本地模拟相比，这条路径多出了平台账号、配置文件、网络访问、任务排队与远端状态查询等因素。

## 统一云平台接口 {#guide-submit-task-unified-api}

UnifiedQuantum 提供统一的云平台接入层，通过一致的接口操作 OriginQ、Quafu 和 IBM 三大平台。

### 配置方式

云平台 API key 统一通过 `~/.uniqc/config.yaml` 配置：

```bash
uniqc config set originq.token "your-originq-token"
uniqc config set quafu.token "your-quafu-token"
uniqc config set ibm.token "your-ibm-token"
```

对应的 YAML 配置文件结构如下：

```yaml
active_profile: default
default:
  originq:
    token: "your-originq-token"
  quafu:
    token: "your-quafu-token"
  ibm:
    token: "your-ibm-token"
    proxy:
      http: "http://proxy:8080"
      https: "https://proxy:8080"
```

### 基本用法

> 完整 API 文档与所有可选参数（`local_compile`、`cloud_compile`、`skip_validation`、`options=`、`backend_name=`、`chip_id=` 等）见 [`uniqc.backend_adapter.task_manager.submit_task`](#guide-submit-task-api-reference)。同时也可以在交互环境中执行 `help(submit_task)` 查看完整 docstring。

```python
from uniqc import Circuit, submit_task, wait_for_result, query_task

# 1. 创建电路
circuit = Circuit()
circuit.h(0)
circuit.cnot(0, 1)
circuit.measure(0, 1)

# 2. 提交任务
#
# backend 参数必须使用 'provider:chip-name' 的规范格式。仅传 'originq'
# （或其它平台名）会报错并提示当前缓存中的 chip 列表。可用的 chip 列表
# 通过 `uniqc backend list -p originq` 或 `uniqc.list_backends()` 查询。
#
# 默认 local_compile=1：UnifiedQuantum 会先做离线 compatibility 检查，
# 若使用了非 basis 门（如 H/CNOT），会自动 transpile 到目标芯片的 basis
# 门集（CZ/SX/RZ）和拓扑后再提交，因此你不需要手动 compile() 才能提交。
task_id = submit_task(circuit, backend='originq:WK_C180', shots=1000)
print(f"Task ID: {task_id}")

# 3. 等待结果（返回 UnifiedResult；超时抛 TaskTimeoutError，失败抛 TaskFailedError）
result = wait_for_result(task_id, timeout=300)
print(f"Counts: {result.counts}")          # {'00': 512, '11': 488}
print(f"Probabilities: {result.probabilities}")

# 4. 查询任务状态
info = query_task(task_id)
print(info.status)  # TaskStatus.RUNNING / SUCCESS / FAILED
```

> **关于 `backend` 字符串的强校验（自 0.0.12 起）**：`submit_task()` /
> `submit_batch()` 要求 `backend` 满足 `provider:chip-name` 规范格式
> （如 `originq:WK_C180`、`quafu:ScQ-P10`、`ibm:ibm_brisbane`）。仅传裸平台名
> （`'originq'`）会被拒绝，错误信息会列出本地缓存里能用的 chip。需要先
> 通过 `uniqc auth login` / `uniqc config set <provider>.token …` 配好 API key，
> 然后用 `uniqc backend list -p originq` 拉一遍 backend 列表，再选一个
> chip 提交。
>
> 旧的 `submit_task(circuit, backend='originq', backend_name='WK_C180')`
> 写法仍可工作（会被自动归一为 `originq:WK_C180`），但新代码请直接用
> 规范格式。

### 平台选择

切换不同平台只需更改 `backend` 参数（保持 `provider:chip-name` 规范格式）：

```python
# OriginQ Cloud
task_id = submit_task(circuit, backend='originq:WK_C180', shots=1000)

# Quafu（需要 pip install unified-quantum[quafu]）
task_id = submit_task(circuit, backend='quafu:ScQ-P10', shots=1000)

# IBM Quantum（需要 pip install unified-quantum[qiskit]）
task_id = submit_task(circuit, backend='ibm:ibm_brisbane', shots=1000)
```

> **Quafu deprecated 说明**：`unified-quantum[all]` 不包含 Quafu/`pyquafu`。旧 `pyquafu` SDK 依赖 `numpy<2`，单独安装 `[quafu]` 可能导致环境降级。该平台路径后续不保证代码一致性和完整性，支持可能随时停止。

### 任务管理

```python
from uniqc import list_tasks, get_task, clear_completed_tasks, clear_cache

# 查看所有缓存的任务
tasks = list_tasks()
for task in tasks:
    print(f"{task.task_id}: {task.status}")

# 获取特定任务信息
task_info = get_task(task_id)

# 清理已完成的任务
cleared = clear_completed_tasks()
print(f"Cleared {cleared} tasks")

# 清空所有缓存
clear_cache()
```

### 后端信息

```python
from uniqc import backend

# 列出所有已注册后端名称
names = backend.list_backends()  # ['dummy', 'ibm', 'originq', 'quafu', 'quark']

# 获取详细状态信息
backends = backend.list_backends_by_platform()
for name, info in backends.items():
    print(f"{name}: available={info['available']}")

# 获取特定后端实例
originq_backend = backend.get_backend('originq')
print(f"OriginQ available: {originq_backend.is_available()}")
```

## Dummy 模式（本地模拟） {#guide-submit-task-dummy}

Dummy 模式允许在不连接真实云平台的情况下测试任务提交流程。通过 backend 名称前缀 ``dummy`` 激活。

### 启用方式

```python
from uniqc import submit_task, wait_for_result

# 默认 dummy 模拟
task_id = submit_task(circuit, backend='dummy')
result = wait_for_result(task_id)

# 带 chip 特征的 dummy 模拟
task_id = submit_task(circuit, backend='dummy:originq:WK_C180')

# 线性拓扑 dummy
line_task = submit_task(circuit, backend='dummy:virtual-line-3')
grid_task = submit_task(circuit, backend='dummy:virtual-grid-2x2')  # 2x2 网格、无噪声
noisy_task = submit_task(circuit, backend='dummy:originq:WK_C180')  # 真实 backend compile/transpile + 本地含噪执行
```

> **注意**：`backend='dummy:*'` 系列以及 `dummy=True` 的提交不会触发"必须带 chip"
> 的规范格式校验——dummy 路径只用于本地验证，由 dummy 适配器自行处理子标识符。

> **弃用警告**：`dummy=True` 参数已弃用，请改用 `backend='dummy'`。如果你想模拟某个真实芯片，请使用 `backend='dummy:<platform>:<backend>'`，例如 `backend='dummy:originq:WK_C180'`。这一类 chip-backed dummy 是规则型写法，不会出现在 backend 列表中。

### Dummy 模式适用场景

- 开发阶段验证提交/查询调用链路
- 本地测试任务提交流程
- 在不具备真实平台访问条件时完成联调
- 在提交到真实硬件前，用 `dummy:virtual-*` 或 `dummy:<platform>:<backend>` 验证拓扑、compile/transpile 与任务展示链路

## 批量提交

```python
from uniqc import submit_batch

# 构建多个电路
circuits = []
for i in range(10):
    c = Circuit()
    c.h(0)
    c.rx(1, i * 0.1)
    c.cnot(0, 1)
    c.measure(0, 1)
    circuits.append(c)

# 批量提交
task_ids = submit_batch(circuits, backend='originq:WK_C180', shots=1000)
print(f"Submitted {len(task_ids)} tasks")
```

## 结果处理

### Bitstring 约定（永久不变）{#guide-submit-task-bitstring-convention}

uniqc 在所有平台（OriginQ / Quafu / IBM-Qiskit / Quark / Dummy / 本地仿真）
返回的 `result.counts` / `result.probabilities` 字典 key 都满足 **同一条永久
约定**：

> **`c[0]` 始终是 bitstring 的最右侧字符（LSB），`c[N-1]` 是最左侧字符。**

`c[i]` 记录的是 **第 `i` 次** 调用 `circuit.measure(q)` 的比特，与 qubit
索引解耦。如果你按 `circuit.measure(0); circuit.measure(1)` 的顺序写测量，
那么 `c[0]` 对应 `q[0]` 的结果，`c[1]` 对应 `q[1]`。

最简自检脚本（在任何后端都应给出 `'01'` 占绝对多数）：

```python
from uniqc.circuit_builder import Circuit
from uniqc.backend_adapter.task_manager import submit_batch, wait_for_result

c = Circuit(2)
c.x(0)
c.measure(0)        # -> c[0]
c.measure(1)        # -> c[1]

uid = submit_batch([c], backend='dummy:virtual-line-2', shots=1024)
print(wait_for_result(uid)[0].counts)   # -> {'01': 1024}
```

`x(0)` 把 `q[0]` 翻成 `|1⟩`，`q[0]→c[0]→1`，所以读到的 bitstring 是 `'01'`
（左边是 `c[1]=0`，右边是 `c[0]=1`）。这一约定由
`uniqc/test/test_endianness_convention.py` 在每次发布前对所有平台 adapter
强制校验，**不会再改变**。

任何平台原生 SDK 的差异（IBM 默认 little-endian、Quafu 在某些后端 q[0]=
最左、Quark 取决于固件）都已经在 adapter 内部统一翻译为以上约定；下游代码
不必再做 `[::-1]` 之类的手工翻转。

### 返回值结构

`wait_for_result(task_id, ...)` 返回 :class:`UnifiedResult`（dict-like，统一接口）；
原生批量任务（`submit_batch(..., native_batch=True)`）返回 `list[UnifiedResult]`。

```python
result = wait_for_result(task_id)

# 访问测量结果
print(result.counts)         # {'00': 512, '11': 488}
print(result.probabilities)  # {'00': 0.512, '11': 0.488}
print(result['00'])          # dict-like 访问也可
print(result.raw())          # 原始平台 payload

# 计算期望值
from uniqc import calculate_expectation
exp_zz = calculate_expectation(result.probabilities, 'ZZ')
print(f"<ZZ> = {exp_zz}")
```

### 平台特定后端参数

```python
# Quafu: 指定芯片
task_id = submit_task(circuit, backend='quafu:ScQ-P10', auto_mapping=True)

# OriginQ: 指定芯片和优化选项
task_id = submit_task(circuit, backend='originq:WK_C180', circuit_optimize=True)
```

## 平台选择说明 {#guide-submit-task-platform-selection}

| 平台 | 定位 | 适用场景 | 额外依赖 |
|------|------|---------|---------|
| OriginQ Cloud | 主生产路径 | 生产环境、真实量子计算 | 无额外依赖 |
| Quafu | 第三方云平台（deprecated） | BAQIS ScQ 系列 | `pip install unified-quantum[quafu]`，不包含在 `[all]` 中 |
| IBM Quantum | 第三方云平台 | IBM Quantum 生态 | `pip install unified-quantum[qiskit]` |
| Dummy | 本地模拟 | 开发测试、联调 | `pip install unified-quantum[simulation]` |

## 平台边界与限制

在进入远端提交路径前，建议先确认以下几点：

- **本地模拟 != 远端提交**：本地模拟解决的是线路验证问题；远端提交解决的是平台接入与任务执行问题。
- **配置是前置条件**：不同平台需要配置相应的环境变量。
- **网络与账号会影响可用性**：远端平台可能受网络环境、认证状态、平台可用性和排队情况影响。
- **额外依赖**：IBM 需要安装额外的依赖包；Quafu 需要单独安装 `[quafu]`，但该路径已 deprecated 且有 `numpy<2` 风险。

如果你还在反复修改线路结构、量子门或输出解释，说明你仍处于本地验证阶段，建议先回到 [本地模拟](simulation.md)。

## 下一步与参考

- 如果你还没有完成线路验证，先回到 [本地模拟](simulation.md)
- 如果你还不清楚线路如何构建，先阅读 [构建量子线路](circuit.md)
- API 参考：
  - {mod}`uniqc.backend_adapter.task_manager`
  - {mod}`uniqc.backend_adapter.backend`
  - {mod}`uniqc.backend_adapter.task.adapters`
  - {mod}`uniqc.backend_adapter.task.normalizers`

## 完整 API 参考 {#guide-submit-task-api-reference}

下面把 `submit_task` 的完整签名 / 默认参数 / 隐藏 kwargs 全部展开列出，避免你必须跳到独立 API 文档去查。`submit_batch` 接受同样的 kwargs，只是把 `circuit` 换成 `circuits: list[Circuit]`，并返回 `list[str]`。

```{eval-rst}
.. autofunction:: uniqc.backend_adapter.task_manager.submit_task
   :noindex:

.. autofunction:: uniqc.backend_adapter.task_manager.submit_batch
   :noindex:

.. autofunction:: uniqc.backend_adapter.task_manager.wait_for_result
   :noindex:

.. autofunction:: uniqc.backend_adapter.task_manager.query_task
   :noindex:
```

### 关键隐式参数速查

| 参数 / 环境变量 | 默认值 | 作用 |
|------|--------|------|
| `local_compile` (kwarg) | `1` | 本地 qiskit transpile 强度。`0` 完全关闭本地编译；`1` 在校验失败时做轻量 transpile 到 basis/拓扑；`2`/`3` 走更重的优化（更慢但更短/更高保真度的线路）。详情见 `docs/source/compile/compile_levels.md`。 |
| `cloud_compile` (kwarg) | `1` | 转发给适配器的云端编译强度。`0` 关闭云端编译（如 OriginQ 适配器会收到 `circuit_optimize=False`），`>0` 开启；支持精细控制的适配器可直接读取 1/2/3。 |
| `skip_validation` (kwarg) | `False` | 完全跳过离线 compatibility 检查（不推荐，会让已知会被云端拒绝的线路也走到网络层）。 |
| `options` (kwarg) | `None` | 平台专属的强类型选项对象（`OriginQOptions` / `QuafuOptions` / `IBMOptions` 等）。 |
| `metadata` (kwarg) | `None` | 写入本地 task 缓存的附加元数据；后续可通过 `query_task(...).metadata` 取回。 |
| `backend_name` / `chip_id` (kwarg) | — | 旧式写法，把 chip 名以独立 kwarg 形式传入。新代码直接写在 `backend='provider:chip'` 即可，旧写法会被自动归一。 |

> 文档版本与代码同步保证：基本用法示例由 `uniqc/test/cloud/test_doc_basic_usage.py` 自动跑测，文档写错或代码行为漂移时 CI 会失败；如果你发现新的 doc 示例无法运行，请同步加一条对应测试。
