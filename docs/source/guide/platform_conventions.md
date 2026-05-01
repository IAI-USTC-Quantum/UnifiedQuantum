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
    "result": {
        "counts": {"00": 512, "11": 488},
        "probabilities": {"00": 0.512, "11": 0.488}
    }
}
```

嵌套字典，包含 `counts`（shot 统计）和 `probabilities`（理论概率）。注意：`wait_for_result()` 在 task_manager 层会解包返回 `{"counts": ..., "probabilities": ...}`。

### 2.3 IBM / Qiskit

```python
{
    "status": "success",
    "result": [{"00": 512, "11": 488}, {"01": 300, "11": 700}],
    "time": "Fri 01 May 2026, 10:00AM",
    "backend_name": "ibm_qasm_simulator"
}
```

批量提交时 `result` 为 counts 字典列表（每个电路一个）；单电路提交时也是列表（只有一个元素）。

### 2.4 Dummy

```python
{
    "status": "success",
    "result": {"00": 512, "11": 488}
}
```

与 OriginQ 相同，扁平 `{bitstring: shots}` 字典。

### 2.5 处理不同结果格式

```python
from uniqc.task_manager import wait_for_result

result = wait_for_result(task_id, backend="quafu")

# Quafu: result 是 {"counts": {...}, "probabilities": {...}}
counts = result["counts"]

# OriginQ / Dummy: result 直接是 {"00": 512, ...}
# IBM: result 是 [{"00": 512}, ...]（列表）
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
from uniqc.circuit_adapter import QuafuCircuitAdapter

adapter = QuafuCircuitAdapter()
gates = adapter.get_supported_gates()
if "T" not in gates:
    print("T 门不支持，请使用 RX/RY/RZ 近似")
```

---

## 5. 芯片/后端命名约定 {#platform-chip-names}

### OriginQ

```
origin:wuyuan:d5     # 五岳 D5 硬件
origin:wuyuan:d6     # 五岳 D6 硬件
origin:simulator:01   # 模拟器
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
| 结果格式 | `{bitstring: shots}` | `{counts, probabilities}` | `[counts, ...]` | `{bitstring: shots}` |
| 提交模式 | 异步 | 异步（`wait=` 可选） | 同步 | 同步 |
| `query_sync()` | ✅ | ✅ | ✅ | ❌ |
| 1Q 门保真度 | ✅ 可用 | ❌ 返回 None | ✅ 可用 | ❌ |
| 电路优化 | `circuit_optimize` | `auto_mapping` | `circuit_optimize` | N/A |
| 免费额度 | 有限 | 有限 | ✅ 有开放设备 | 无需联网 |

---

## 下一步 {#platform-conventions-next-steps}

- 完整示例：参考 [任务管理](task_manager.md)
- 详细 API 说明：参考 [任务提交指南](submit_task.md)
- 架构设计说明：参考 [适配器架构](../advanced/adapter_architecture.md)
