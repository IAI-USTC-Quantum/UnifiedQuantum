# 编译、选项与区域选择 {#guide-compiler-options}

## 什么时候进入本页 {#guide-compiler-options-when-to-read}

当你已经掌握线路构建和本地模拟的基础流程，并希望：

- 将线路编译到特定量子芯片的拓扑结构上
- 利用芯片的标定数据（各量子比特和门 fidelity）进行感知路由
- 使用类型化的后端选项替代手写 `**kwargs`
- 根据芯片标定数据自动寻找最优物理量子比特区域

就应该进入本页。

本页涵盖三个相互独立又相互配合的新模块：

| 模块 | 文件 | 用途 |
|------|------|------|
| 增强编译 (`compile`) | `uniqc/compile/compiler.py` | Qiskit 感知路由 + 多格式输出 |
| 后端选项 (`BackendOptions`) | `uniqc/backend_adapter/task/options.py` | 类型化后端选项 |
| 区域选择器 (`RegionSelector`) | `uniqc/backend_adapter/region_selector.py` | 最优量子比特区域发现 |

---

## 1. 增强编译：`compile()` 函数

### 1.1 为什么需要 `compile()`？

现有的 `transpile_originir()` / `transpile_qasm()` 返回字符串，缺少：

- **芯片标定感知路由**：根据各量子比特 fidelity 选择高保真路径
- **统一的返回类型**：可返回 `Circuit` 对象而非字符串
- **编译元数据**：SWAP 插入数量、预估成功率

`compile()` 是这三个问题的统一解决方案。

### 1.2 核心签名

```python
from uniqc.compile import compile
from uniqc import TranspilerConfig

# 最简用法
compiled = compile(circuit, backend_info=backend_info)

# 完整参数
compiled = compile(
    circuit,                          # Circuit 对象或 OriginIR 字符串
    backend_info=backend_info,         # 提供拓扑图（可选，有 ChipCharacterization 时可省略）
    level=2,                          # Qiskit 优化级别 0–3，默认 2
    basis_gates=["cz", "sx", "rz"],  # 目标基门集，默认 ["cz", "sx", "rz"]
    chip_characterization=chip,        # 芯片标定数据（可选）
    output_format="circuit",          # "circuit" | "originir" | "qasm"，默认 "circuit"
)
```

### 1.3 拓扑来源优先级

```
compile() 拓扑来源优先级：
1. backend_info.topology  （明确指定 BackendInfo）
2. chip_characterization.connectivity  （从芯片标定获取）
3. ValueError  （两处都没有则抛出异常）
```

### 1.4 输出格式

```python
# 返回 Circuit 对象（推荐）
circ = compile(circuit, backend_info=info, output_format="circuit")
assert isinstance(circ, Circuit)

# 返回 OriginIR 字符串
oir = compile(circuit, backend_info=info, output_format="originir")
assert "QINIT" in oir

# 返回 OpenQASM 2.0 字符串
qasm = compile(circuit, backend_info=info, output_format="qasm")
assert "OPENQASM" in qasm
```

### 1.5 `TranspilerConfig`：类型化配置（可选）

`TranspilerConfig` 是一个 `frozen=True` 的数据类，可用于打包并复用一组编译参数（便于缓存、传参）。注意：`compile()` 当前不直接接受 `config` 参数，调用时需要把字段展开传入：

```python
from uniqc import TranspilerConfig, compile, find_backend

config = TranspilerConfig(
    type="qiskit",                # 目前仅支持 "qiskit"，预留扩展
    level=3,                      # 最强优化
    basis_gates=["cz", "sx", "rz"],  # 自定义基门集
    chip_characterization=chip,   # 传入标定数据以启用感知路由
)

backend_info = find_backend('originq:WK_C180')
compiled = compile(
    circuit,
    backend_info,
    type=config.type,
    level=config.level,
    basis_gates=config.basis_gates,
    chip_characterization=config.chip_characterization,
)
```

`compile()` 总是直接返回 `Circuit`（或字符串，取决于 `output_format`）。需要拿到 SWAP 数量、估算成功率等编译元数据时，请使用内部 API `compile_full()`，它返回 `CompilationResult`（注意：`compile_full` 与 `CompilationResult` 当前未在公开命名空间暴露）。

### 1.6 芯片标定感知路由

当传入 `chip_characterization` 时，`compile()` 内部会：

1. 构建加权图，边权重 = `1 - fidelity`（低权重 = 高保真）
2. 对每个不满足拓扑的 2Q 门，用 Dijkstra 找最高保真路径
3. 在路径上插入 SWAP 门
4. 返回插入的 SWAP 数量和预估电路成功率

```python
from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter

adapter = OriginQAdapter()
chip = adapter.get_chip_characterization("WK_C180")

compiled = compile(
    circuit,
    chip_characterization=chip,
    output_format="circuit",
)
# 内部自动使用 chip.two_qubit_data 中的 fidelity 数据选择路由路径
```

### 1.7 与现有 API 的关系

```
transpile_originir(circuit_str, backend_info)
    ↓ 返回 str（OriginIR）
    ↓
compile(circuit, backend_info)
    ↓ 返回 Circuit | str
    ↓ 两函数并存，compile() 为推荐入口
transpile_qasm(qasm_strs, ...)
    ↓ 返回 str（QASM）
```

`compile()` **不替代** 现有函数，而是提供更高层的统一入口。现有 `transpile_originir()` 和 `transpile_qasm()` 保持不变。

---

## 2. 类型化后端选项：`BackendOptions`

### 2.1 为什么需要 `BackendOptions`？

现有 `submit_task(circuit, "originq", shots=1000, backend_name="WK_C180")` 的问题：

- **无 IDE 自动补全**：字符串参数无法提供类型提示
- **无文档注解**：不知道有哪些可选参数
- **平台间不一致**：各平台参数名不同，无法统一处理

`BackendOptions` 在保留 `**kwargs` 兼容性的同时，提供了类型安全的替代接口。

### 2.2 类层次结构

```
BackendOptions（基类）
├── OriginQOptions
├── QuafuOptions
├── IBMOptions
└── DummyOptions
```

### 2.3 各平台选项

#### OriginQ

```python
from uniqc import OriginQOptions

opts = OriginQOptions(
    backend_name="WK_C180",           # OriginQ 后端名
    circuit_optimize=True,             # 默认 True，后端执行时优化
    measurement_amend=False,           # 默认 False，测量误差缓解
    auto_mapping=False,                # 默认 False
    shots=1000,                       # 继承自 BackendOptions 基类
)
```

#### Quafu

```python
from uniqc import QuafuOptions

opts = QuafuOptions(
    chip_id="ScQ-P18",        # 默认
    auto_mapping=True,        # 默认 True
    task_name="my-task",      # 可选，服务端任务名
    group_name="my-group",    # 可选，批次跟踪
    wait=False,               # 默认 False，阻塞直到服务端确认
    shots=1000,
)
```

#### IBM

```python
from uniqc import IBMOptions

opts = IBMOptions(
    chip_id="ibm_kyoto",       # 可选，不填则使用 IBM 默认后端
    auto_mapping=True,          # 默认 True
    circuit_optimize=True,      # 默认 True
    task_name="ibm-task",      # 可选
    shots=1000,
)
```

#### Dummy（本地模拟器）

```python
from uniqc import DummyOptions

opts = DummyOptions(
    noise_model=None,           # 可选，传入噪声模型进行噪声模拟
    available_qubits=16,        # 默认 16
    available_topology=None,    # 可选，指定拓扑 [[u,v], ...]，None=all-to-all
    shots=1000,
)
```

### 2.4 `BackendOptionsFactory`：工厂模式

```python
from uniqc import BackendOptionsFactory, OriginQOptions

# 从 kwargs dict 构建
opts = BackendOptionsFactory.from_kwargs("originq", {
    "backend_name": "WK_C180",
    "circuit_optimize": False,
})
assert isinstance(opts, OriginQOptions)

# 从 None 创建平台默认值
opts = BackendOptionsFactory.normalize_options(None, "quafu")
# → QuafuOptions(chip_id="ScQ-P18", auto_mapping=True, ...)

# 从 dict 规范化（normalize_options 的主入口）
opts = BackendOptionsFactory.normalize_options(
    {"chip_id": "ScQ-P10"}, "quafu"
)
```

### 2.5 与 `submit_task()` 集成

```python
from uniqc import submit_task, OriginQOptions

# 方式 1：直接传入 BackendOptions 实例（推荐）
opts = OriginQOptions(backend_name="WK_C180", shots=2000)
task_id = submit_task(circuit, "originq", options=opts)

# 方式 2：传入 dict（底层自动转换为 BackendOptions）
task_id = submit_task(circuit, "originq", shots=500, options={
    "backend_name": "WK_C180",
})

# 方式 3：纯 kwargs（向后完全兼容，无变化）
task_id = submit_task(circuit, "originq", shots=500,
    backend_name="WK_C180",
)
```

**向后兼容性保证**：当 `options=None` 且没有平台特定 kwargs 时，函数行为与之前完全相同。`options` 参数是纯增量的。

---

## 3. 区域选择器：`RegionSelector`

### 3.1 为什么需要 `RegionSelector`？

量子芯片上的物理量子比特具有不同的门保真度（由标定数据表征）。对于一个需要 N 个量子比特的电路，选择**哪 N 个量子比特**会直接影响执行成功率。

`RegionSelector` 通过分析 `ChipCharacterization` 标定数据，自动找到：

- 最高保真度的线性链（1D）
- 适合给定电路的 2D 区域

### 3.2 初始化

```python
from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
from uniqc import RegionSelector

adapter = OriginQAdapter()
chip = adapter.get_chip_characterization("WK_C180")
selector = RegionSelector(chip)
```

### 3.3 `find_best_1D_chain`：寻找最优线性链

适用于线性拓扑电路（如 GHZ 态、线性葡萄串结构）。

```python
from uniqc import ChainSearchResult

# 在全芯片上找最优 5-qubit 链
result = selector.find_best_1D_chain(5)
print(f"最优链: {result.chain}")           # e.g. [0, 1, 2, 3, 4]
print(f"预估成功率: {result.estimated_fidelity:.4f}")  # e.g. 0.9405
print(f"所需 SWAP 门数: {result.num_swaps}")

# 指定起始量子比特（强制从某处开始）
result = selector.find_best_1D_chain(4, start=2)
# → 从 qubit 2 开始的最优 4-qubit 链

# 无法达到精确长度时，返回最长可用链
result = selector.find_best_1D_chain(100)  # 芯片只有 10 个 qubit
print(f"最长链: {result.chain}")  # 返回全芯片最长路径
```

**算法说明**：

1. **贪心扩展**：从起始量子比特出发，每次选择 fidelity 最高的邻居
2. **DFS 回溯**：若贪心陷入死路，用带剪枝的深度优先搜索找最长路径
3. **保真度计算**：`F = \prod fidelity(edge_i)`，即所有边 fidelity 的乘积

### 3.4 `find_best_2D_from_circuit`：寻找最优 2D 区域

适用于需要 2D 连接的电路（如量子游走、VQE ansatz）。

```python
from uniqc import RegionSearchResult

# 从芯片标定数据中找最适合 circuit 的 2D 区域
result = selector.find_best_2D_from_circuit(
    circuit,
    min_qubits=4,              # 覆盖电路所需最小量子比特数（可覆盖）
    max_region_size=36,        # 最大搜索范围（默认 36，对应 6×6）
    max_search_seconds=10.0,   # 搜索超时（防止大芯片搜索爆炸）
    transpiler=None,           # 可选：传入 fidelity 评估函数
)
print(f"最优区域: {result.qubits}")
print(f"区域形状: {result.region_shape}")   # e.g. (2, 3)
print(f"预估成功率: {result.estimated_fidelity:.4f}")
```

**算法说明**：

1. 解析电路的量子比特需求（`max(circuit.max_qubit + 1, circuit.qubit_num)`）
2. 枚举矩形子图：尝试 1×N, 2×N, 3×N, ... 形状的连通子图
3. 用 `estimate_circuit_fidelity()` 对每个候选区域打分
4. 返回预估成功率最高的区域

### 3.5 `estimate_circuit_fidelity`：电路保真度估算

基于**乘积保真度公式**：

```
P_success = \prod(1Q gate fidelity) \times \prod(2Q gate fidelity) \times \prod(readout fidelity)
```

```python
# 对全芯片所有量子比特估算
fid = selector.estimate_circuit_fidelity(circuit)

# 对特定量子比特子集估算
fid = selector.estimate_circuit_fidelity(circuit, qubits={0, 1, 2, 3})

# 与 RegionSelector 配合使用
result = selector.find_best_2D_from_circuit(circuit, min_qubits=4)
if result.qubits:
    fid = selector.estimate_circuit_fidelity(circuit, qubits=result.qubits)
    print(f"最优区域预估成功率: {fid:.4f}")
```

**缺失数据处理**：当某量子比特或边不在标定数据中时，默认使用 0.99 fidelity（即 1% 错误率）。这避免了对部分标定芯片返回 0 的问题。

### 3.6 辅助方法

```python
# 获取所有量子比特按单门 fidelity 排名
rankings = selector.get_qubit_rankings()
# → [(qubit_id, fidelity), ...]，按 fidelity 降序

# 获取所有边按 2Q 门 fidelity 排名
edge_rankings = selector.get_edge_rankings()
# → [((qubit_u, qubit_v), fidelity), ...]
```

---

## 4. 组合使用示例

### 4.1 完整流水线：RegionSelector → compile → submit_task

```python
from uniqc import (
    RegionSelector,
    OriginQOptions,
    submit_task,
    BackendOptionsFactory,
)
from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
from uniqc.compile import compile
from uniqc import Circuit

# 1. 构建电路
circuit = Circuit()
for i in range(5):
    circuit.h(i)
for i in range(4):
    circuit.cnot(i, i + 1)
circuit.measure(list(range(5)), list(range(5)))

# 2. 获取芯片标定
adapter = OriginQAdapter()
chip = adapter.get_chip_characterization("WK_C180")

# 3. 找最优量子比特区域
selector = RegionSelector(chip)
region = selector.find_best_2D_from_circuit(circuit, min_qubits=5)
print(f"最优执行区域: {region.qubits}")

# 4. 将电路编译到该区域
compiled = compile(
    circuit,
    chip_characterization=chip,
    output_format="circuit",
)
print(f"编译后电路: {compiled.originir[:100]}...")

# 5. 提交任务
opts = OriginQOptions(shots=1000)
task_id = submit_task(compiled, "originq", options=opts)
print(f"任务 ID: {task_id}")
```

### 4.2 仅使用 BackendOptions 提交

```python
from uniqc import QuafuOptions, submit_task
from uniqc import Circuit

circuit = Circuit()
circuit.h(0)
circuit.cnot(0, 1)

# 类型安全的选项写法
opts = QuafuOptions(
    chip_id="ScQ-P10",
    task_name="ghz-experiment",
    wait=True,
)
task_id = submit_task(circuit, "quafu", options=opts)
```

---

## 5. API 速查

### `compile()`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `circuit` | `Circuit \| str` | — | 输入电路 |
| `backend_info` | `BackendInfo \| None` | `None` | 提供拓扑信息 |
| `level` | `int` | `2` | Qiskit 优化级别 0–3 |
| `basis_gates` | `list[str] \| None` | `["cz","sx","rz"]` | 目标基门集 |
| `chip_characterization` | `ChipCharacterization \| None` | `None` | 标定数据（启用感知路由） |
| `output_format` | `"circuit" \| "originir" \| "qasm"` | `"circuit"` | 输出格式 |

### `OriginQOptions`

| 字段 | 类型 | 默认值 |
|------|------|--------|
| `backend_name` | `str` | `"WK_C180"` |
| `circuit_optimize` | `bool` | `True` |
| `measurement_amend` | `bool` | `False` |
| `auto_mapping` | `bool` | `False` |
| `shots` | `int` | `1000` |

### `QuafuOptions`

| 字段 | 类型 | 默认值 |
|------|------|--------|
| `chip_id` | `str` | `"ScQ-P18"` |
| `auto_mapping` | `bool` | `True` |
| `task_name` | `str \| None` | `None` |
| `group_name` | `str \| None` | `None` |
| `wait` | `bool` | `False` |
| `shots` | `int` | `1000` |

### `RegionSelector`

| 方法 | 说明 |
|------|------|
| `find_best_1D_chain(length, start)` | 找最优 `length`-qubit 线性链 |
| `find_best_2D_from_circuit(circuit, ...)` | 找最适合电路的 2D 区域 |
| `estimate_circuit_fidelity(circuit, qubits)` | 估算电路在给定量子比特上的成功率 |
| `get_qubit_rankings()` | 按 fidelity 排名所有量子比特 |
| `get_edge_rankings()` | 按 2Q fidelity 排名所有边 |

### 常见错误

**缺少 Qiskit 依赖**

调用 `compile()` 时若 Qiskit 未安装，会抛出 `CompilationFailedException`，提示：

```
pip install unified-quantum[qiskit]
```

或使用 uv：

```
uv pip install unified-quantum[qiskit]
```

**绘图功能需要 matplotlib**

`plot_time_line()` 需要 matplotlib。若未安装，调用时返回 `None` 而不抛异常。若需脉冲序列可视化：

```
pip install matplotlib
```

:::{note}
🔧 `schedule_circuit` 与 `plot_time_line*` 在内部依赖 `compile()` 把逻辑线路展开为芯片原生门，因此同样需要可选的 `unified-quantum[qiskit]` extra。如果你只想对**已经编译过、且只使用平台原生门**的线路做调度，可在不安装 `[qiskit]` 的前提下直接传入；否则请先 `pip install unified-quantum[qiskit]`。
:::
