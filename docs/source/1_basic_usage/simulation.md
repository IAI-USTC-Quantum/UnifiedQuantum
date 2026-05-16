# 本地模拟 {#guide-simulation}

## 什么时候进入本页 {#guide-simulation-when-to-read}

当你已经有一条线路，想在本地验证结果、查看概率分布、做多次采样，或比较不同模拟后端时，进入本页。

本页解决的核心问题是：**如何把已经写好的线路跑起来，并根据目标选择合适的模拟方式与后端**。

## 本页解决的问题 {#guide-simulation-problems}

- 如何把已有线路送入模拟器
- 如何查看概率测量、状态向量、多次采样等不同输出
- 如何选择 Simulator、OpcodeSimulator 等不同模拟入口
- 如何根据目标选择 statevector、density matrix、density matrix_qutip 等后端
- 如何在本地验证时识别已知限制与风险
- `uniqc.simulator` 与 `Backend=dummy` 有什么区别、该用哪个

## 前置条件

阅读本页前，默认你已经完成以下至少一项：

- 已经会使用 `Circuit` 构建基础线路
- 已经拿到了 `originir` 或 `qasm` 字符串
- 已经完成 [快速上手](quickstart.md) 中的最小示例

如果你还不清楚如何创建线路、添加量子门或导出线路格式，建议先阅读 [构建量子线路](circuit.md)。

## 推荐阅读顺序 {#guide-simulation-reading-order}

建议按以下顺序阅读本页内容：

1. **Simulator** — 先跑通最常见的本地模拟路径
2. **概率测量 / 状态向量 / 多次采样** — 理解不同输出类型分别回答什么问题
3. **Opcode 模拟器** — 需要底层控制或特定后端时再进入
4. **带噪声模拟** — 当你需要加入噪声模型时阅读
5. **后端对比** — 根据验证目标选择不同后端
6. **simulator vs dummy** — `uniqc.simulator` 与 `Backend=dummy` 的区别与选择
7. **已知限制** — 在使用 density matrix 或复杂噪声路径前优先确认

## 本地模拟入口总览 {#guide-simulation-entry-overview}

在 UnifiedQuantum 中，“本地模拟”指的是**不提交远端任务、直接在当前环境运行线路并查看结果**。常见入口可以先按输入格式与验证目标来分：

| 本地模拟入口 | 输入形式 | 适合先看什么问题 |
| --- | --- | --- |
| {class}`uniqc.simulator.Simulator` | `AnyQuantumCircuit`（`Circuit` 对象、`originir` 字符串或 `qasm` 字符串） | 已经用 {class}`uniqc.circuit_builder.Circuit` 构好线路，想先快速验证概率分布、状态向量或采样结果；也适用于 OpenQASM 2.0 输入，`Simulator` 会自动检测格式 |
| {class}`uniqc.simulator.OpcodeSimulator` | opcode 列表 | 需要更底层控制、特定后端或排查后端差异 |
| {class}`uniqc.simulator.NoisySimulator` | `AnyQuantumCircuit` + 噪声配置 | 想在本地模拟阶段加入噪声模型并观察结果变化 |
| `MPSSimulator`（见 [MPS 模拟器](../advanced/mps_simulator.md)） | `AnyQuantumCircuit` + `MPSConfig` | 比特数较多但纠缠/键维 (`χ`) 受控，`statevector` 装不下时使用 |
| `TorchQuantumSimulator`（需要 `unified-quantum[pytorch]` 与 git 安装的 `torchquantum`） | `Circuit` / `originir` | 想把模拟接入 PyTorch 计算图、做端到端可微分实验 |

> `MPSSimulator` 与 `TorchQuantumSimulator` 也可通过统一工厂入口构造：`create_simulator(backend='mps')` / `create_simulator(backend='torchquantum')`。

如果你还在决定线路该如何表达，先回到 [构建量子线路](circuit.md#guide-circuit-when-to-read)；如果你已经完成本地验证，准备提交到云平台或真机执行，转到 [提交任务](submit_task.md#guide-submit-task-entry-overview)。

## uniqc.simulator 与 Backend=dummy 的区别 {#guide-simulation-vs-dummy}

`uniqc.simulator`（`Simulator` / `NoisySimulator`）与 `submit_task(backend='dummy:*')` 都在本地用经典计算模拟量子线路，但面向不同场景。

| 维度 | `uniqc.simulator` | `Backend=dummy` |
| --- | --- | --- |
| 入口方式 | `Simulator().simulate_pmeasure(code)` | `submit_task(circuit, backend='dummy:*')` |
| 工作流程 | 直接调用本地模拟方法 | 经过 submit → query → wait 任务管道（与真实后端一致） |
| 噪声控制 | 通过 `NoisySimulator` + `ErrorLoader` 手动配置噪声参数 | 自动从 `chip_characterization` 校准数据派生噪声模型 |
| 输出类型 | pmeasure / statevector / density_matrix / shots | `UnifiedResult`（与真实后端输出格式一致） |
| 适用场景 | 快速调试、算法验证、查看中间态 | 验证编译→提交→查询的完整链路 |
| 后端选择 | `statevector` / `density_matrix` / `density_matrix_qutip` | `dummy:local:simulator` 或 `dummy:<platform>:<backend>` |

**选择建议**：

- **快速验证概率分布或状态向量** → 用 `Simulator`，可直接拿到 pmeasure、statevector 等中间结果。
- **验证从编译到结果获取的完整链路** → 用 `submit_task(backend='dummy:*')`，走与真实提交相同的管道。
- **需要噪声但想手动配置** → 用 `NoisySimulator` + `ErrorLoader`。
- **需要噪声且想模拟真实芯片特征** → 用 `submit_task(backend='dummy:<platform>:<backend>')`，噪声自动从 chip 校准数据派生。

> `Backend=dummy` 的详细用法见 [提交任务 — Dummy 模式](submit_task.md#guide-submit-task-dummy)。

## Simulator {#guide-simulation-originir}

最常用的模拟器，统一接受 `Circuit` 对象、`originir` 字符串或 `qasm` 字符串，并自动检测输入格式。无论是 OriginIR 还是 OpenQASM 2.0 线路，都可以直接使用同一个 `Simulator` 类。

```python
from uniqc import Circuit
from uniqc.simulator import Simulator

circuit = Circuit()
circuit.h(0)
circuit.cnot(0, 1)
circuit.measure(0, 1)

sim = Simulator()
```

### 概率测量

```python
prob = sim.simulate_pmeasure(circuit.originir)
# 返回各测量结果的概率分布
```

### 状态向量

```python
sv = sim.simulate_statevector(circuit.originir)
# 返回状态向量
```

### 多次采样

```python
result = sim.simulate_shots(circuit.originir, shots=1000)
# 返回 1000 次采样的统计结果
```

## Opcode 模拟器与本地模拟后端 {#guide-simulation-opcode}

底层模拟器，直接操作 opcode 列表。支持多后端（每个后端都接受多种别名，便于在 CLI、Python API、文档之间互换）：

| 规范名 (canonical) | 别名 (aliases) | 说明 |
|--------------------|----------------|------|
| `statevector` | `state_vector` | 状态向量（无噪声） |
| `density_operator` | `density_matrix`, `densitymatrix`, `densityoperator`, `density` (CLI) | 密度矩阵（支持噪声） |
| `density_operator_qutip` | `density_matrix_qutip` | 基于 QuTiP 的密度矩阵；需要 `unified-quantum[simulation]` extra（`qutip` + `qutip-qip`） |

> 别名在 {func}`uniqc.simulator.backend_alias` 中统一解析；`OpcodeSimulator`、`create_simulator` 与 CLI `uniqc simulate --backend` 接受同一组别名。

```python
from uniqc.simulator import OpcodeSimulator

sim = OpcodeSimulator(backend_type='statevector')
```

> Opcode 的详细文档见 [Opcode](../advanced/opcode.md)。

## 带噪声的本地模拟 {#guide-simulation-noisy}

```python
from uniqc.simulator import NoisySimulator

sim = NoisySimulator(
    backend_type='density_matrix',  # 噪声模拟必须使用 density_matrix 后端
    error_loader=my_error_loader,
    readout_error={0: [0.01, 0.02], 1: [0.01, 0.02]}
)
prob = sim.simulate_pmeasure(circuit.originir)
```

> 噪声模拟必须显式指定 `backend_type='density_matrix'`；默认的 `statevector` 后端不支持噪声通道，调用 `simulate_pmeasure` 时会抛 `ValueError`。

> 噪声模型的详细配置见 [噪声模拟](../advanced/noise_simulation.md)。

## 后端对比

| 后端 | 适用场景 | 噪声支持 | 性能 |
|------|---------|---------|------|
| `statevector` | 无噪声快速模拟，小规模线路（< 30 量子比特） | ❌ | 最快 |
| `density_matrix` | 含噪声模拟，双比特门为主 | ✅ | 较慢（内存 O(4^n)） |
| `density_matrix_qutip` | 复杂噪声模型，高精度需求 | ✅ | 较慢，依赖 Qutip |

> **CLI 与 Python API 的别名一致性**：CLI `uniqc simulate --backend density` 与 Python API 的 `density_matrix` / `density_operator` / `densitymatrix` / `density` 都是同一种密度矩阵后端的别名（在 {func}`uniqc.simulator.backend_alias` 内部归一化为 `density_operator`）。`density_operator_qutip` 与其别名 `density_matrix_qutip` 同理。

**选择建议**：
- 一般无噪声模拟 → {class}`uniqc.simulator.Simulator`（基于 statevector）
- 需要噪声模拟 → {class}`uniqc.simulator.NoisySimulator`（基于 density_matrix）
- 复杂多比特噪声模型 → `density_matrix_qutip`

## 已知限制 {#guide-simulation-known-limitations}

- `statevector` 后端无法模拟噪声。
- 多比特门（> 2）在 density matrix 后端支持有限。

## API 参考

完整的模拟器 API 见：

- {mod}`uniqc.simulator` — 模拟器模块
- {class}`uniqc.simulator.OpcodeSimulator`
- {class}`uniqc.simulator.Simulator`
- {class}`uniqc.simulator.NoisySimulator`
- `uniqc.simulator.mps_simulator.MPSSimulator` / `MPSConfig` — MPS 后端，详见 [MPS 模拟器](../advanced/mps_simulator.md)
- `uniqc.simulator.torchquantum_simulator.TorchQuantumSimulator` — 基于 torchquantum 的可微分后端（需要 `unified-quantum[pytorch]` extra 以及 git 安装的 `torchquantum`）
- `create_simulator(backend=...)` — 统一工厂入口，`backend` 支持 `'statevector' | 'density_matrix' | 'mps' | 'torchquantum'` 等

## 下一步

- 如果你发现自己仍不清楚线路该如何表达、量子门如何组织，回看 [构建量子线路](circuit.md)。
- 如果你已经完成本地验证，并准备把线路提交到云平台或真机执行，进入 [提交任务](submit_task.md)。这一步开始关注的将不再是本地后端选择，而是平台配置、任务提交、状态查询与远端结果获取。

## 相关测试

- `test_simulator.py`：噪声模拟器单元测试
- `test_random_OriginIR.py`：随机回归测试（密度矩阵对比）
- `test_random_QASM.py`：随机回归测试（statevector/density matrix 对比）
- `test_demos.py`：示例端到端测试

详见 [测试覆盖说明](testing.md)。
