# 平台约定 {#guide-platform-conventions}

本文档详细说明各量子云平台的输入/输出约定、运行模式、门支持范围和配置方式。适用于完成基础使用教程后需要针对特定平台调优的场景。

---

## 1. 输入格式约定 {#platform-input-formats}

各平台接受的电路格式不同，`submit_task()` 内部会根据 `backend` 参数自动选择对应的 Circuit Adapter 进行转换，但用户也可以手动调用各平台的 adapter。

| 平台 | 输入类型 | 自动转换 | 手动转换 |
|------|----------|----------|----------|
| OriginQ | `str`（OriginIR 字符串） | `circuit.originir` | `OriginQCircuitAdapter().adapt(circuit)` → 返回 OriginIR string |
| Quafu | `quafu.QuantumCircuit` | `QuafuCircuitAdapter().adapt(circuit)` | `QuafuAdapter.translate_circuit(originir)` |
| IBM | `qiskit.QuantumCircuit` | `IBMCircuitAdapter().adapt(circuit)` | `QiskitAdapter.translate_circuit(originir)` |
| Dummy | `str`（OriginIR 字符串） | `circuit.originir` | 无需转换，直接送入本地模拟器 |

**自动转换路径**：Circuit → CircuitAdapter → Native Circuit → TaskAdapter → 云端

---

## 2. 输出格式约定 {#platform-output-formats}

所有平台的 `query()` 返回格式统一为 `{"status": "...", "result": ...}`。注意：各平台的 `result` 内层结构不同。

### 2.1 OriginQ

```python
{
    "status": "success",
    "result": {"00": 512, "11": 488}
}
```

扁平 `{bitstring: shots}` 字典。

### 2.2 Quafu

> **Deprecated / 依赖风险**：Quafu 的旧 `pyquafu` SDK 依赖 `numpy<2`，因此 Quafu 不包含在 `unified-quantum[all]` 中。只有明确安装 `unified-quantum[quafu]` 时才会启用旧 Quafu 路径。该平台 SDK 已 deprecated，后续不保证相关代码一致性和完整性，支持可能随时停止。

```python
{
    "status": "success",
    "result": {"00": 512, "11": 488}
}
```

扁平 `{bitstring: shots}` 字典，与 OriginQ / Dummy 格式统一。

### 2.3 IBM / Qiskit

```python
{
    "status": "success",
    "result": {"00": 512, "11": 488},
    "time": "Fri 01 May 2026, 10:00AM",
    "backend_name": "ibm_fez"
}
```

单电路提交返回扁平 `{bitstring: shots}` 字典。`query_batch()` 返回 `{"result": [flat_dict, ...]}`。

```python
{
    "status": "success",
    "result": {"00": 512, "11": 488}
}
```

与 OriginQ 相同，扁平 `{bitstring: shots}` 字典。

### 2.5 统一结果格式

所有平台的 `wait_for_result()` / `query_task()` 均返回统一的扁平 counts 字典：

```python
from uniqc import wait_for_result

# 所有平台统一返回 {"00": 512, "1111": 488}
result = wait_for_result(task_id, backend="quafu")
# result == {"00": 512, "1111": 488}  # 扁平 dict，无需后处理

result = wait_for_result(task_id, backend="ibm")
# result == {"00": 512, "1111": 488}  # 同样格式
```

`wait_for_result()` 的实际返回值是 `result["result"]`，各 adapter 已统一将其规范化为 `{bitstring: shots}` 扁平字典。

### 2.6 Bit endianness 与测量比特映射 {#platform-bit-endianness}

uniqc 在所有平台都把测量结果归一化到同一个 cbit 框架。除非另行说明，下面这条约定就是规范本身：

* **bitstring 的索引规则**：返回字典的 key 是定长二进制字符串。其 **最右侧字符**（索引 `-1`）对应 **classical bit `c[0]`**；索引 `-2` 对应 `c[1]`；依此类推。MSB 在最左、LSB 在最右——与 `bin(int)[2:].zfill(n)` 的视觉顺序一致。
* **classical bit 的来源**：`c[i]` 记录的是 **第 i 次** 调用 `circuit.measure(q)` 的结果，**不一定** 是 `q[i]`。也就是说，cbit 索引由测量调用顺序决定，不是由 qubit 索引决定：

  ```python
  c = Circuit()
  c.h(0); c.cnot(0, 1)
  c.measure(1)   # -> c[0]   （bitstring 的最右字符）
  c.measure(0)   # -> c[1]   （bitstring 的右数第二字符）
  # bitstring "10" 表示 c[1]=1, c[0]=0
  ```

* **跨平台一致性**：OriginQ、Quafu、IBM/Qiskit 在底层各有差异（IBM 默认 little-endian，Quafu 在某些 backend 上 big-endian），但 `uniqc` 的 normalizer 已经统一改写为上述 cbit 框架。任何依赖原始平台顺序的下游代码请改用 normalizer 输出。

如果你需要按 qubit 索引读取，请保证 `circuit.measure(q[i])` 的调用顺序与你预期的 `c[i]` 一致。

---

## 2.7 提交前格式校验 {#platform-precheck}

从 0.0.12 起，`submit_task()` / `submit_batch()` 在提交到任何云端之前，会执行一次 **离线校验**（`uniqc.compile.compatibility_report`）：

1. **Submit language**：根据后端确定提交语言 — `originq` → OriginIR；`ibm`、`quafu`、`quark` → QASM 2.0。
2. **Basis gate set**：根据后端确定基础门集合 — `originq`、`quafu`、`quark` 默认按 `cz + sx + rz` 校验；`ibm` 按 `BackendInfo.extra["basis_gates"]` 校验。
3. **Topology**：双比特门必须落在 backend 拓扑的边上。`CZ`、`ISWAP`、`SWAP`、`XX`、`YY`、`ZZ`、`XY` 视为无向；`CNOT`/`CX`、`ECR` 视为有向。
4. **Qubit count**：电路中用到的 qubit 索引必须 `< backend.num_qubits`。
5. **Topology TTL**：后端拓扑使用 `~/.uniqc/cache/backends.sqlite` 的缓存，TTL 24h；过期但仍可用的拓扑会以 warning 方式提示。

校验**通过** 时，`submit_task()` 会在 `metadata` 中附加：

```python
{
    "validation_passed": True,
    "gate_depth": 13,
    "used_gates": ["CZ", "RZ", "SX"],
    "submit_language": "originir",
    "validation_warnings": [...],   # 仅在有 warning 时出现
}
```

校验**失败**且未启用自动编译时会抛出 `UnsupportedGateError`。可以这样跳过校验或自动编译：

```python
from uniqc import submit_task, compile_for_backend, compatibility_report, is_compatible

# 直接获取报告（不会发请求）
report = compatibility_report(circuit, backend_info)
print(report)

# 简单 boolean
ok = is_compatible(circuit, backend_info)

# 让 uniqc 自动按 backend 政策编译后再提交
task_id = submit_task(circuit, backend="originq:WK_C180")

# 完全跳过校验（仅在你确信前端已经做过等价校验时使用）
task_id = submit_task(circuit, backend="originq:WK_C180", skip_validation=True)
```

或者编程式预先编译：

```python
compiled = compile_for_backend(circuit, backend_info)  # → cz/sx/rz
```

### 2.8 Gate depth 计算约定 {#platform-gate-depth}

`uniqc.compute_gate_depth(circuit, *, virtual_z=True)` 返回 **并行感知 + virtual-Z 感知** 的 depth：

* 每个 gate 占据其所有 qubit 的 *earliest free layer*；同一层中无冲突的 gate 被并行计入同一深度。**这与“gate 数”不同**——很多旧实验代码错误地把它们等同。
* `virtual_z=True`（默认）时，`Z`、`RZ`、`S`、`T`、`U1` 视为 **frame change**，深度为 0；它们仍占据该 qubit 的 cursor 以避免与非交换的相邻门折叠。
* `BARRIER` 同步它涉及的所有 qubit cursor，**但不增加** depth 数。
* `MEASURE` 不计入 gate depth。
* `CZ` **不是** virtual-Z（它是双比特门）。

```python
from uniqc import Circuit, compute_gate_depth
c = Circuit()
c.h(0); c.h(1); c.cnot(0, 1); c.rz(0, 0.5); c.h(0)
compute_gate_depth(c)                # → 3 （H 并行；CNOT；RZ 虚；H 与 CNOT 不并行 → 3）
compute_gate_depth(c, virtual_z=False)  # → 4
```

---

## 3. 运行模式约定 {#platform-run-modes}

### 3.1 提交行为对比

| 平台 | `submit()` 行为 | `submit_batch()` 行为 | `query_sync()` |
|------|----------------|----------------------|----------------|
| OriginQ | 立即返回（异步） | 立即返回（异步） | ✅ 支持 |
| Quafu | 默认异步；`wait=True` 同步等待服务器回执 | 默认异步；`wait=True` 同步等待 | ✅ 支持 |
| IBM / Qiskit | 同步（提交即阻塞） | 同步（批量在一个 Job 内执行） | ✅ 支持 |
| Dummy | 同步（本地模拟器） | 同步 | ❌ 不需要 |

### 3.2 Quafu `wait` 参数

```python
# 异步提交（默认）- 立即返回 task_id
task_id = adapter.submit(circuit, chip_id="ScQ-P18", wait=False)

# 同步等待 - 阻塞直到服务器回执
task_id = adapter.submit(circuit, chip_id="ScQ-P18", wait=True)
```

### 3.3 轮询等待模式

```python
# OriginQ / Quafu: 使用 query_sync() 轮询
results = adapter.query_sync(task_id, interval=2.0, timeout=60.0)

# IBM / Qiskit: submit() 本身就是同步的，不需要额外等待
```

---

## 4. 门支持约定 {#platform-gate-support}

### 4.1 OriginQ

使用 pyqpanda3 的 `convert_originir_string_to_qprog()`，支持完整的 OriginIR 规范：
`H`, `X`, `Y`, `Z`, `S`, `SX`, `T`, `RX`, `RY`, `RZ`, `RPhi`, `RPhi90`, `RPhi180`,
`U1`, `U2`, `U3`, `U4`, `CNOT`, `CZ`, `SWAP`, `ISWAP`, `TOFFOLI`, `CSWAP`,
`XX`, `YY`, `ZZ`, `XY`, `PHASE2Q`, `UU15`, `I`, `BARRIER`, `MEASURE`
以及 `CONTROL`/`DAGGER` 块。

#### OriginQ 模拟器后端

OriginQ 云平台提供三种模拟器后端，可通过 `backend_name` 参数使用：

| `backend_name` | 说明 | 用途 |
|---|---|---|
| `full_amplitude` | 全振幅模拟 | 多比特精确模拟 |
| `partial_amplitude` | 部分振幅 | 大规模线路的部分比特模拟 |
| `single_amplitude` | 单振幅 | 特定基态振幅计算 |

```python
from uniqc import submit_task

# 使用 OriginQ 模拟器后端
task_id = submit_task(circuit, backend="originq", backend_name="full_amplitude", shots=1000)
result = wait_for_result(task_id, backend="originq")
```

> 注意：模拟器后端在 `uniqc backend list --platform originq` 中以 `Type = sim` 标识，与 QPU 硬件后端（`Type = hw`）分开列出。模拟器后端使用 `QCloudSimulator` API 而非 QPU 的 `QCloudOptions`。

### 4.2 Quafu

`QuafuAdapter.translate_circuit()`（OriginIR → quafu.QuantumCircuit）支持：

**单比特门：** `H`, `X`, `Y`, `Z`, `S`, `SX`, `T`, `RX`, `RY`, `RZ`

**双比特门：** `CNOT`, `CZ`, `SWAP`, `ISWAP`

**测量：** `MEASURE`

**其他：** `BARRIER`（无操作，跳过）

**不支持的门**（使用会抛出 `RuntimeError`）：
`U1`, `U2`, `U3`, `TOFFOLI`, `CSWAP`, `XX`, `YY`, `ZZ`, `XY`, `RPhi`, `RPhi90`, `RPhi180`, `PHASE2Q`, `UU15`, `CONTROL`, `DAGGER` 块

### 4.3 IBM / Qiskit

`QiskitAdapter.translate_circuit()` 走 OriginIR → QASM → qiskit.QuantumCircuit 路线，借助 Qiskit 的转译器支持所有标准 OpenQASM 2.0 门。

### 4.4 门支持自检

```python
from uniqc.backend_adapter.circuit_adapter import QuafuCircuitAdapter

adapter = QuafuCircuitAdapter()
gates = adapter.get_supported_gates()
if "T" not in gates:
    print("T 门不支持，请使用 RX/RY/RZ 近似")
```

---

## 5. 芯片/后端命名约定 {#platform-chip-names}

### OriginQ

```
WK_C180         # 180 比特硬件
PQPUMESH8       # 8 比特硬件
full_amplitude  # 全振幅模拟器
```

可用 `OriginQAdapter().list_backends()` 查询所有可用后端。

### Quafu

```
ScQ-P10      # 10比特 ScQ-P10
ScQ-P18      # 18比特 ScQ-P18
ScQ-P136     # 136比特 ScQ-P136
ScQ-P10C     # 10比特（经典）
Dongling     # 训推一体机
```

`submit()` 必须指定 `chip_id`，有效值见 `QuafuAdapter.VALID_CHIP_IDS`。

### IBM

```
ibm_qasm_simulator     # QASM 模拟器（推荐测试用）
ibm_brisbane           # 真实硬件 Brisbane
ibm_sherbrooke         # 真实硬件 Sherbrooke
```

真实硬件名称因设备代数而异，使用 `QiskitAdapter()._provider.backends()` 查询可用后端。

---

## 6. 配置约定 {#platform-configuration}

### 6.1 YAML 配置文件（~/.uniqc/config.yaml）

```bash
uniqc config set originq.token "your-originq-key"
uniqc config set quafu.token "your-quafu-token"
uniqc config set ibm.token "your-ibm-token"
```

```yaml
active_profile: default
default:
  originq:
    token: "your-originq-key"
  quafu:
    token: "your-quafu-token"
  ibm:
    token: "your-ibm-token"
    proxy:
      http: "http://proxy:8080"
      https: "https://proxy:8080"
```

适配器直接读取 active profile 下的平台配置，不再通过 API token 环境变量注入凭据。

### 6.2 IBM 代理配置

```python
# 方式1：通过构造函数传入
adapter = QiskitAdapter(proxy={"https": "http://proxy:8080"})

# 方式2：通过环境变量
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
```

### 6.4 Dummy 模式

通过 backend 名称前缀 ``dummy`` 激活本地模拟，无需环境变量：

```python
task_id = submit_task(circuit, backend='dummy')                    # 默认模拟
task_id = submit_task(circuit, backend='dummy:virtual-line-3')     # 线性 3q 拓扑
```

---

## 7. 快速参考表 {#platform-quick-reference}

| 维度 | OriginQ | Quafu | IBM | Dummy |
|------|---------|-------|-----|-------|
| 地区 | 中国 | 中国（BAQIS） | 全球 | 本地 |
| 输入 | OriginIR string | quafu.QuantumCircuit | qiskit.QuantumCircuit | OriginIR string |
| 结果格式 | `{bitstring: shots}` | `{bitstring: shots}` | `{bitstring: shots}`（单电路）/ list（batch） | `{bitstring: shots}` |
| 提交模式 | 异步 | 异步（`wait=` 可选） | 同步 | 同步 |
| `query_sync()` | ✅ | ✅ | ✅ | ❌ |
| 1Q 门保真度 | ✅ 可用 | ❌ 返回 None | ✅ 可用 | ❌ |
| 电路优化 | `circuit_optimize` | `auto_mapping` | `circuit_optimize` | N/A |
| chip_characterization 支持 | ✅ | ✅ | ✅ | ✅ 从标定数据自动推导噪声参数 |
| 免费额度 | 有限 | 有限 | ✅ 有开放设备 | 无需联网 |

---

## 8. DummyBackend：编号规则、虚拟拓扑与本地噪声模拟 {#platform-dummy-backend}

DummyBackend 是本地模拟器后端，在不需要真实量子硬件的情况下执行电路。推荐通过 backend id 使用，而不是在业务代码里手动拼装 adapter。

| backend id | 语义 |
|------------|------|
| `dummy` | 无约束、无噪声虚拟机 |
| `dummy:virtual-line-N` | `N` 比特线性拓扑，无噪声 |
| `dummy:virtual-grid-RxC` | `R*C` 比特网格拓扑，无噪声 |
| `dummy:<platform>:<backend>` | 复用真实 backend 的拓扑和标定数据，先 compile/transpile，再本地含噪执行 |

`dummy:<platform>:<backend>` 是规则型写法，不是需要提前注册的 backend；它不会作为独立后端出现在 `uniqc backend list` 或 Gateway WebUI 的 backend 卡片中。运行时会解析真实 backend 的 topology / chip characterization，并把编译后的线路写入 task metadata。

### 基本用法

```python
from uniqc import submit_task, wait_for_result

# 无约束、无噪声
task_id = submit_task(circuit, backend="dummy", shots=1000)
result = wait_for_result(task_id)

# 有拓扑约束但无噪声
line_task = submit_task(circuit, backend="dummy:virtual-line-3", shots=1000)

# 针对真实 OriginQ backend 的本地含噪仿真
noisy_task = submit_task(circuit, backend="dummy:originq:WK_C180", shots=1000)
```

### `chip_characterization` 如何转换为噪声参数

使用 `dummy:<platform>:<backend>` 时，UnifiedQuantum 会从缓存或对应云平台 adapter 取得 `ChipCharacterization`，再自动提取以下数据：

| 标定数据 | 转换方式 | 用法 |
|----------|----------|------|
| `single_gate_fidelity`（逐量子比特） | `error = 1 - fidelity` | 注入单量子比特去极化噪声 |
| `gate.fidelity`（逐量子比特对） | `error = 1 - fidelity` | 注入双量子比特门去极化噪声 |
| `avg_readout_fidelity`（逐量子比特） | 对称读出误差模型 | 注入读出误差 |

若某量子比特或量子比特对缺少标定数据，使用默认值（1Q 误差 0.01，2Q 误差 0.05）。

直接使用 `DummyAdapter(chip_characterization=...)` 仍可作为底层测试或自定义 adapter 路径，但文档、示例和新业务代码应优先使用 `dummy:<platform>:<backend>`，这样 compile/transpile、task metadata 和 Gateway 展示都能走统一链路。

### `DummyOptions`（Python API）

```python
from uniqc import DummyOptions

opts = DummyOptions(
    noise_model=None,              # 可选，传入噪声模型（dict）
    available_qubits=16,           # 默认 16
    available_topology=None,        # None=all-to-all，传入 [[u,v], ...] 指定拓扑
    shots=1000,
)
```

### CLI 中的 Dummy 平台

在 CLI 中使用 `--platform dummy` 等效于选择 dummy backend id：

```bash
# 无约束、无噪声
uniqc submit circuit.ir --platform dummy --shots 1000 --wait

# 虚拟线性拓扑
uniqc submit circuit.ir --platform dummy --backend virtual-line-3 --shots 1000 --wait

# 真实 backend 的本地含噪仿真
uniqc submit circuit.ir --platform dummy --backend originq:WK_C180 --shots 1000 --wait

# 试运行验证
uniqc submit circuit.ir --platform dummy --dry-run
```

---

## 9. 统一后端工厂：`get_backend()` {#platform-get-backend}

`get_backend()` 是量子后端工厂函数（`uniqc.backend_adapter.backend`），用于获取平台后端实例。日常代码优先从 `uniqc` 直接导入。

```python
from uniqc import get_backend

# 获取 DummyBackend（纯净模拟）
backend = get_backend("dummy")
task_id = backend.submit(circuit, shots=1000)

# 获取带虚拟拓扑的 DummyBackend
backend = get_backend("dummy:virtual-line-3")

# 获取真实 backend 规则对应的 DummyBackend（提交时仍会先 compile/transpile）
backend = get_backend("dummy:originq:WK_C180")

# 获取 OriginQ 后端
backend = get_backend("originq")

# 获取 Quafu 后端
backend = get_backend("quafu")

# 获取 IBM 后端
backend = get_backend("ibm")

```

`get_backend()` 返回 `QuantumBackend` 实例，支持 `.submit()`、`.query()` 等方法。详见 [后端管理](../guide/compiler_options_region.md)。

---

## 下一步 {#platform-conventions-next-steps}

- 完整示例：参考 [任务管理](task_manager.md)
- 详细 API 说明：参考 [任务提交指南](submit_task.md)
- 架构设计说明：参考 [适配器架构](../advanced/adapter_architecture.md)
