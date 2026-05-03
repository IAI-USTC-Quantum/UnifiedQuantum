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

### 6.1 环境变量（优先级最高）

```bash
export ORIGINQ_API_KEY="your-originq-key"
export QUAFU_API_TOKEN="your-quafu-token"
export IBM_TOKEN="your-ibm-token"
```

### 6.2 YAML 配置文件（~/.uniqc/uniqc.yml）

```yaml
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

`sync_tokens_to_env()` 在 `backend_registry._build_adapter()` 内部自动调用，用户无需手动触发。

### 6.3 IBM 代理配置

```python
# 方式1：通过构造函数传入
adapter = QiskitAdapter(proxy={"https": "http://proxy:8080"})

# 方式2：通过环境变量
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
```

### 6.4 Dummy 模式

```bash
export UNIQC_DUMMY=true
# 可选：指定拓扑
export ORIGINQ_AVAILABLE_QUBITS='[0,1,2,3]'
export ORIGINQ_AVAILABLE_TOPOLOGY='[[0,1],[1,2],[2,3]]'
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

## 8. DummyBackend：芯片标定与本地噪声模拟 {#platform-dummy-backend}

DummyAdapter 是本地模拟器适配器，在不需要真实量子硬件的情况下执行电路。它完整支持 `ChipCharacterization` 标定数据，可实现真实的噪声模拟。

### 基本用法

```python
from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

# 纯净模拟（无噪声）
adapter = DummyAdapter()

# 从芯片标定获取真实噪声参数
from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter

originq = OriginQAdapter()
chip = originq.get_chip_characterization("WK_C180")
adapter = DummyAdapter(chip_characterization=chip)

# 提交（结果立即可用，无需等待）
task_id = adapter.submit(circuit, shots=1000)
result = adapter.query(task_id)
```

### `chip_characterization` 如何转换为噪声参数

当传入 `ChipCharacterization` 对象时，`DummyAdapter` 自动提取以下数据：

| 标定数据 | 转换方式 | 用法 |
|----------|----------|------|
| `single_gate_fidelity`（逐量子比特） | `error = 1 - fidelity` | 注入单量子比特去极化噪声 |
| `gate.fidelity`（逐量子比特对） | `error = 1 - fidelity` | 注入双量子比特门去极化噪声 |
| `avg_readout_fidelity`（逐量子比特） | 对称读出误差模型 | 注入读出误差 |

若某量子比特或量子比特对缺少标定数据，使用默认值（1Q 误差 0.01，2Q 误差 0.05）。

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

在 CLI 中使用 `--platform dummy` 等效于使用 `DummyAdapter`：

```bash
# CLI：本地模拟（纯净）
uniqc submit circuit.ir --platform dummy --shots 1000 --wait

# CLI：试运行验证
uniqc submit circuit.ir --platform dummy --dry-run
```

---

## 9. 统一后端工厂：`get_backend()` {#platform-get-backend}

`get_backend()` 是量子后端工厂函数（`uniqc.backend_adapter.backend`），用于获取平台后端实例。日常代码优先从 `uniqc` 直接导入。

```python
from uniqc import get_backend

# 获取 DummyBackend（含芯片标定噪声模拟）
from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter

chip = OriginQAdapter().get_chip_characterization("WK_C180")
backend = get_backend("dummy", config={"chip_characterization": chip})
task_id = backend.submit(circuit, shots=1000)

# 获取 OriginQ 后端
backend = get_backend("originq")

# 获取 Quafu 后端
backend = get_backend("quafu")

# 获取 IBM 后端
backend = get_backend("ibm")

# 获取 DummyBackend（纯净模拟）
backend = get_backend("dummy")
```

`get_backend()` 返回 `QuantumBackend` 实例，支持 `.submit()`、`.query()` 等方法。详见 [后端管理](../guide/compiler_options_region.md)。

---

## 下一步 {#platform-conventions-next-steps}

- 完整示例：参考 [任务管理](task_manager.md)
- 详细 API 说明：参考 [任务提交指南](submit_task.md)
- 架构设计说明：参考 [适配器架构](../advanced/adapter_architecture.md)
