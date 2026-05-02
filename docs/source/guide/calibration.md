# 芯片校准与量子错误缓解

UnifiedQuantum 提供完整的芯片校准和量子错误缓解（QEM）工作流。核心架构将**校准实验**（写入 `~/.uniqc/calibration_cache/`）与**错误缓解**（读取缓存，强制 TTL 过期策略）分离。

## 架构概述

```
uniqc.calibration/     校准实验 — 执行电路，记录 calibrated_at，写入缓存
uniqc.qem/             量子错误缓解 — 读取缓存，强制 max_age_hours TTL
uniqc.algorithm/       高级工作流 — 组合校准 + QEM + 芯片执行
examples/wk180/        WK180 (OriginQ) 示例
```

所有校准结果以 ISO-8601 时间戳 `calibrated_at` 为标志，存储在 `~/.uniqc/calibration_cache/` 中，文件命名格式：

```
{type}_{backend}_{identifier}_{timestamp}.json
# 示例：readout_1q_dummy_q0_20260502T143000.json
```

---

## 1. 读出误差校准（Readout Calibration）

测量误差（readout error）通过构建**混淆矩阵**（confusion matrix）来表征：

- **单比特**：2×2 矩阵，行=测量结果，列=准备状态
- **双比特**：4×4 矩阵，行=测量结果，列=准备状态（|00⟩,|01⟩,|10⟩,|11⟩）

### Python API

```python
from uniqc.calibration.readout import ReadoutCalibrator
from uniqc.task.adapters import DummyAdapter

# 创建校准器
adapter = DummyAdapter()
cal = ReadoutCalibrator(adapter=adapter, shots=1000)

# 单比特校准
result_1q = cal.calibrate_1q(qubit=0)
# result_1q["confusion_matrix"]  → 2×2
# result_1q["assignment_fidelity"]  → 接近 1.0（理想值）

# 双比特联合校准
result_2q = cal.calibrate_2q(qubit_u=0, qubit_v=1)
# result_2q["confusion_matrix"]  → 4×4
```

### CLI

```bash
# 单比特 + 双比特读出校准
uniqc calibrate readout --qubits 0 1 2 --type both --shots 1000

# 仅单比特
uniqc calibrate readout --qubits 0 1 --type 1q

# 输出到文件
uniqc calibrate readout --qubits 0 --output /tmp/readout.json
```

### 工作原理

1. 对每个比特准备基础态（|0⟩, |1⟩）或双比特基础态（|00⟩,|01⟩,|10⟩,|11⟩）
2. 执行测量，统计每个基础态被误读为其他态的概率
3. 构建混淆矩阵 C，其中 `C[meas][prep] = P(meas|prep)`
4. 保存到缓存，结果包含 `calibrated_at` 时间戳

---

## 2. M3 读出误差缓解（M3 Mitigator）

M3（Matrix Mitigation of Measurement errors）通过混淆矩阵的线性求逆来修正测量结果。

```python
from uniqc.qem import M3Mitigator, StaleCalibrationError

# 直接传入校准结果
m3 = M3Mitigator(calibration_result=result_1q, max_age_hours=24.0)

# 修正 counts
corrected_counts = m3.mitigate_counts({"0": 45, "1": 55})
# 返回概率分布，已归一化

# 也可以传入概率向量
corrected_probs = m3.mitigate_probabilities({"0": 0.45, "1": 0.55})
```

### TTL 强制策略

`max_age_hours` 参数强制校准数据的新鲜度：

```python
from uniqc.qem import M3Mitigator

m3 = M3Mitigator(
    cache_path="/path/to/calibration.json",
    max_age_hours=24.0,       # 超过 24h 抛出 StaleCalibrationError
    backend="dummy",
    qubit=0
)
```

---

## 3. 统一读出误差缓解（ReadoutEM）

`ReadoutEM` 自动调用 1q/2q 校准器，并提供统一接口：

```python
from uniqc.qem import ReadoutEM
from uniqc.task.adapters import DummyAdapter

adapter = DummyAdapter()
readout_em = ReadoutEM(adapter, max_age_hours=24.0, shots=1000)

# 单比特修正
mitigated_1q = readout_em.mitigate_counts(
    {"0": 45, "1": 55},
    measured_qubits=[0]
)

# 双比特联合修正
mitigated_2q = readout_em.mitigate_counts(
    {"00": 20, "01": 5, "10": 3, "11": 72},
    measured_qubits=[0, 1]
)

# 3+ 比特自动使用逐比特张量积近似
mitigated_nq = readout_em.mitigate_counts(
    {"000": 50, "111": 50},
    measured_qubits=[0, 1, 2]
)
```

---

## 4. XEB 交叉熵基准测试

XEB（Cross-Entropy Benchmarking）通过随机电路测量每层门保真度。

### Python API

```python
from uniqc.calibration.xeb.benchmarker import XEBenchmarker
from uniqc.qem import ReadoutEM
from uniqc.task.adapters import DummyAdapter

adapter = DummyAdapter()
readout_em = ReadoutEM(adapter, shots=1000)

bench = XEBenchmarker(adapter, shots=1000, readout_em=readout_em, seed=42)

# 单比特 XEB
result_1q = bench.run_1q(qubit=0, depths=[5, 10, 20, 50], n_circuits=50)
print(f"每层保真度 r = {result_1q.fidelity_per_layer:.5f}")

# 双比特 XEB
result_2q = bench.run_2q(
    qubit_u=0, qubit_v=1,
    depths=[5, 10, 20],
    n_circuits=50,
    entangler_gate="CNOT"
)

# 并行双比特 XEB（多个不相交的 qubit pair）
result_parallel = bench.run_parallel_2q(
    pairs=[(0, 1), (2, 3)],
    depth=10,
    n_circuits=50
)
```

### CLI

```bash
# 单比特 XEB
uniqc calibrate xeb --qubits 0 1 2 --type 1q --depths 5 10 20 --n-circuits 50

# 双比特 XEB
uniqc calibrate xeb --qubits 0 1 --type 2q --depths 5 10 --n-circuits 50

# 跳过读出误差修正
uniqc calibrate xeb --qubits 0 --type 1q --no-readout-em
```

### XEB 结果解读

| 字段 | 含义 |
|------|------|
| `fidelity_per_layer` | 每层保真度 r（0<r≤1），越高越好 |
| `fit_r` | 指数拟合参数 r |
| `fit_a`, `fit_b` | 拟合系数：F(m) = A·r^m + B |
| `fidelity_std_error` | r 的标准误差 |
| `n_circuits` | 每个深度的随机电路数量 |

---

## 5. 并行模式生成（Parallel Pattern）

使用 **DSatur 图着色算法**将 2-比特门自动分配到最小并行轮次。

```python
from uniqc.calibration.xeb.patterns import ParallelPatternGenerator

# 从拓扑自动生成
topology = [(0, 1), (1, 2), (2, 3), (3, 4)]
gen = ParallelPatternGenerator(topology)
result = gen.auto_generate()
print(f"链式拓扑需要 {result.n_rounds} 轮（理论上最少 2 轮）")
# result.groups → ((edges_in_round_1), (edges_in_round_2), ...)

# 从 OriginIR 电路提取
originir = """
QINIT 4
CNOT q[0], q[1]
CNOT q[2], q[3]
CNOT q[1], q[2]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
MEASURE q[3], c[3]
"""
result = gen.from_circuit(originir)
print(f"该电路需要 {result.n_rounds} 轮")
```

### CLI

```bash
# 从拓扑分析（自动模式）
uniqc calibrate pattern --qubits 0 1 2 3 --type auto

# 从 OriginIR 文件分析
uniqc calibrate pattern --circuit circuit.oir --type circuit
```

---

## 6. 高级工作流

### XEB 工作流

组合校准 → XEB → 指数拟合的完整流程：

```python
from uniqc.algorithm import xeb_workflow

# 1q XEB（自动调用 ReadoutEM）
results_1q = xeb_workflow.run_1q_xeb_workflow(
    backend="dummy",
    qubits=[0, 1, 2],
    depths=[5, 10, 20, 50],
    n_circuits=50,
    shots=1000,
    use_readout_em=True,
    max_age_hours=24.0,
)

# 2q XEB（使用拓扑找 qubit pairs）
results_2q = xeb_workflow.run_2q_xeb_workflow(
    backend="dummy",
    pairs=[(0, 1), (1, 2)],
    depths=[5, 10, 20],
    n_circuits=50,
)

# 并行 XEB（全芯片）
results_parallel = xeb_workflow.run_parallel_xeb_workflow(
    backend="dummy",
    chip_characterization=chip_char,
    depths=[5, 10],
    n_circuits=50,
)
```

### 读出 EM 工作流

校准并返回可直接使用的 `ReadoutEM` 实例：

```python
from uniqc.algorithm import readout_em_workflow

readout_em = readout_em_workflow.run_readout_em_workflow(
    backend="dummy",
    qubits=[0, 1, 2],
    pairs=[(0, 1), (1, 2)],
    shots=1000,
    max_age_hours=24.0,
)

# 后续实验直接使用
corrected = readout_em.mitigate_counts({"0": 90, "1": 10}, measured_qubits=[0])
```

---

## 7. WK180 (OriginQ) 示例

```python
from examples.wk180 import xeb, readout_em

# 读出误差校准
readout_em.run_wk180_readout_em(
    qubits=[0, 1, 2, 3],
    pairs=[(0, 1), (1, 2)],
    dummy=True,          # 本地模拟
    max_age_hours=24.0,
)

# XEB 基准测试
xeb.run_wk180_xeb(
    qubits=[0, 1],
    xeb_type="both",
    depths=[5, 10, 20, 50],
    n_circuits=50,
    dummy=True,
    use_readout_em=True,
)
```

---

## 8. 缓存管理

```python
from uniqc.calibration.results import (
    find_cached_results,
    load_calibration_result,
    save_calibration_result,
)

# 查找 24h 内有效的校准结果
paths = find_cached_results(
    backend="dummy",
    result_type="readout_1q",
    max_age_hours=24.0,
)

# 加载
result = load_calibration_result(paths[0])

# 手动保存（通常由校准器自动调用）
save_calibration_result(result, type_prefix="readout_1q", cache_dir="/tmp/calibration")
```

---

## 关键设计原则

1. **TTL 由 QEM 层强制执行** — 校准模块只写缓存，从不删除；QEM 模块在读取时检查 `calibrated_at` 时间戳，超出 `max_age_hours` 则抛出 `StaleCalibrationError`
2. **XEB 使用 ReadoutEM** — 所有 XEB 基准测试在计算 Hellinger fidelity 之前先应用读出误差修正
3. **工作流与芯片无关** — `algorithm/` 下的工作流接受任意 `QuantumAdapter`，WK180 示例仅用于演示真实硬件集成

---

## 附录：API 注意事项

### `Circuit.measure()` 的正确用法

`Circuit.measure()` API 将**所有位置参数**视为量子比特索引：

```python
c = Circuit(4)

# ✓ 正确：测量量子比特 0, 1, 2, 3
c.measure(0, 1, 2, 3)

# ✗ 错误：不要传入经典比特索引
c.measure(0, 0)   # 这意味着"测量量子比特 0 两次"！

# ✓ 单比特测量
c.measure(0)

# ✓ 2q 测量
c.measure(0)
c.measure(1)
```

> **历史兼容性**：某些旧代码可能使用 `c.measure(qubit, cbit)` 格式（将第二个参数当作经典比特索引）。此写法在新版 API 中已被移除。如遇此问题，请将 `c.measure(q, b)` 改为 `c.measure(q)`。

### DummyAdapter 含噪模拟与 ChipCharacterization

`DummyAdapter` 支持从真实芯片的校准数据中注入噪声，实现高保真度本地模拟：

```python
from uniqc.task.adapters import DummyAdapter
from uniqc.cli.chip_info import (
    ChipCharacterization, SingleQubitData, TwoQubitData,
    TwoQubitGateData, QubitTopology, Platform,
)

# 构建芯片特性数据
chip_char = ChipCharacterization(
    platform=Platform.ORIGINQ,
    chip_name="my_chip",
    full_id="test:0",
    available_qubits=(0, 1),
    connectivity=(QubitTopology(u=0, v=1),),
    single_qubit_data=(
        SingleQubitData(
            qubit_id=0,
            single_gate_fidelity=0.999,   # 单比特门保真度
            readout_fidelity_0=0.99,      # |0⟩ 读出保真度
            readout_fidelity_1=0.98,       # |1⟩ 读出保真度
            avg_readout_fidelity=0.985,    # 平均读出保真度
        ),
        SingleQubitData(qubit_id=1, single_gate_fidelity=0.999,
                       readout_fidelity_0=0.99, readout_fidelity_1=0.98,
                       avg_readout_fidelity=0.985),
    ),
    two_qubit_data=(
        TwoQubitData(
            qubit_u=0, qubit_v=1,
            gates=(TwoQubitGateData(gate="CNOT", fidelity=0.97),)
        ),
    ),
    calibrated_at="2026-05-02T00:00:00+00:00",
)

# 创建含噪模拟器
adapter = DummyAdapter(chip_characterization=chip_char)
```

注入的噪声类型：
- **单比特门**：由 `single_gate_fidelity` 推导的去极化噪声
- **双比特门**：由 `TwoQubitGateData.fidelity` 推导的去极化噪声
- **读出误差**：由 `readout_fidelity_0/1` 构建的混淆矩阵

使用 `OriginQAdapter` 时，可直接从云端获取芯片特性：

```python
from uniqc.task.adapters import OriginQAdapter, DummyAdapter

# 从云端获取 WK180 芯片特性
orig_adapter = OriginQAdapter()
chip_char = orig_adapter.get_chip_characterization("origin:wuyuan:wk180")

# 用真实数据做本地含噪模拟
local_adapter = DummyAdapter(chip_characterization=chip_char)
```

> **注意**：`chip_characterization` 为 `None` 时，DummyAdapter 执行理想（无噪声）模拟。

### XEB 电路的可复现性

所有 XEB 电路生成器使用 `np.random.default_rng(seed)` 构造本地 RNG，支持完全确定性复现：

```python
from uniqc.calibration.xeb.circuits import (
    generate_1q_xeb_circuits,
    generate_2q_xeb_circuits,
    generate_parallel_2q_xeb_circuits,
)

# ✓ seed=0 是有效的随机种子（不是 None）
circuits = generate_1q_xeb_circuits(
    qubit=0,
    depths=[5, 10, 20],
    n_circuits=50,
    seed=0,   # 有效种子，会被正确使用
)

# 同一 seed 产生完全相同的电路序列
circuits2 = generate_1q_xeb_circuits(
    qubit=0,
    depths=[5, 10, 20],
    n_circuits=50,
    seed=0,
)
assert circuits[0].originir == circuits2[0].originir
```

> `seed=None`（默认）每次生成不同的随机电路。`seed=0` 产生固定序列（适用于基准测试和回归测试）。
