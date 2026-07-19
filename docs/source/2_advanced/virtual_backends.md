# 自定义含噪量子虚拟机 (`dummy:virtual:`)

除了内置的虚拟拓扑 fixture(`virtual-line-N` / `virtual-grid-RxC`）和复用真实芯片标定数据的
`dummy:<platform>:<chip>`，uniqc 还支持**完全由用户定义的含噪量子虚拟机**：在
`~/.uniqc/backend/virtual/` 下写一个 YAML 文件，声明比特数、耦合拓扑、分层 gate error
model、T1/T2 热弛豫和逐比特读出错误，然后以 `dummy:virtual:<name>` 作为 backend
标识符在任意接受 backend 的地方使用（`submit_task`、`uniqc submit`、XEB / 读出标定工作流等）。

## 目录布局

`~/.uniqc/backend/` 是所有 backend 信息的统一根目录：

```
~/.uniqc/backend/
├── virtual/                    # 用户手写的含噪虚拟机 YAML（本页主题）
│   └── my-machine.yaml
├── backends.json               # backend 发现缓存（uniqc backend update 写入）
└── chips/                      # 芯片表征缓存（uniqc backend chip-display 写入）
    └── originq-WK_C180.json
```

```{note}
旧路径 `~/.uniqc/cache/backends.json` 与 `~/.uniqc/backend-cache/` 会在首次访问时
自动迁移到新位置，无需手动处理。
```

## 快速开始

```bash
# 1. 生成带完整注释的模板
uniqc backend virtual init my-machine

# 2. 编辑 ~/.uniqc/backend/virtual/my-machine.yaml 后校验
uniqc backend virtual validate my-machine

# 3. 查看解析结果与派生噪声参数
uniqc backend virtual show my-machine

# 4. 使用(出现在 backend 列表中)
uniqc backend list                 # 显示 virtual:my-machine
uniqc submit circuit.qasm --backend dummy:virtual:my-machine --shots 1000
```

Python API:

```python
from uniqc import submit_task

task_id = submit_task(circuit, backend="dummy:virtual:my-machine", shots=1000)
```

虚拟机名称即 YAML 文件名（不含扩展名），只允许字母、数字、`-`、`_`。

## YAML 配置参考

完整示例（与 `uniqc backend virtual init` 生成的模板一致）:

```yaml
description: 自定义含噪虚拟机

# 比特声明(二选一): qubits: [0, 1, 2, 3] 或 num_qubits: 4
num_qubits: 4

# 耦合拓扑(可选;删除本节表示全连接、无拓扑约束),2q 门双向可用
topology:
  - [0, 1]
  - [1, 2]
  - [2, 3]

# 门时长(纳秒);配置 thermal_relaxation 时必需
gate_times_ns:
  default_1q: 30        # 所有 1q 门的默认时长
  default_2q: 80        # 所有 2q 门的默认时长
  # CZ: 120             # 可按门类型单独覆盖

noise:
  # 按门类型的均匀退极化噪声(概率 ∈ [0, 1])
  depolarizing:
    1q: 0.001           # 所有 1q 门
    2q: 0.01            # 所有 2q 门(真双比特退极化通道)

  # 按门类型覆盖(与均匀噪声叠加);也可简写为 H: 0.0005
  gate_type:
    CZ: {depolarizing: 0.02}

  # 按具体门实例配置(与上面各层叠加;CZ 的比特顺序无关)
  gate_instance:
    - {gate: CZ, qubits: [0, 1], depolarizing: 0.05}
    - {gate: H,  qubits: [2],  depolarizing: 0.003}

  # T1/T2 热弛豫(微秒 μs),需配合 gate_times_ns;要求 t2_us <= 2 * t1_us
  thermal_relaxation:
    default: {t1_us: 50, t2_us: 40}
    qubits:
      2: {t1_us: 30, t2_us: 25}

  # 读出错误 [p(0→1), p(1→0)]
  readout:
    default: [0.02, 0.02]
    qubits:
      3: [0.05, 0.08]
```

### 各节说明

| 键 | 说明 |
|----|------|
| `description` | 可选描述文本，显示在 `uniqc backend list` / WebUI 中 |
| `qubits` / `num_qubits` | 比特列表或比特数(二选一，必填) |
| `topology` | 可选耦合边列表；省略表示全连接。2q `gate_instance` 的边必须在其中 |
| `gate_times_ns` | 门时长(ns)。`default_1q` / `default_2q` 按 arity 提供默认值，门名键(如 `CZ`)覆盖特定门。配置热弛豫时必需 |
| `noise.depolarizing` | 均匀退极化：`1q` 作用于所有 1q 门，`2q` 作用于所有 2q 门（真双比特退极化通道 `TwoQubitDepolarizing`) |
| `noise.gate_type` | 按门类型的退极化率，与均匀噪声叠加；值可写 `{depolarizing: p}` 或简写 `p` |
| `noise.gate_instance` | 按具体门实例的退极化率列表；CZ 比特顺序无关（自动归一化） |
| `noise.thermal_relaxation` | 逐比特 T1/T2(μs),`default` 作用于全部比特，`qubits` 按比特覆盖 |
| `noise.readout` | 逐比特读出错误 `[p(0→1), p(1→0)]`，结构同上 |

各噪声层**叠加生效**：一个 CZ 门可能同时受到均匀 2q depolarizing、`gate_type` 覆盖、
`gate_instance` 覆盖和热弛豫四类噪声。

### T1/T2 热弛豫模型

热弛豫按门的实际时长换算为振幅阻尼 + 退相位通道（纯 Python 实现，复用
`AmplitudeDamping` / `PhaseFlip` opcode)。对比特 q、门时长 t（统一换算为 ns):

- 振幅阻尼：`γ = 1 - exp(-t / T1)`（仅当配置了 T1)
- 退相位：`p_φ = 0.5 * (1 - exp(-t * (1/T2 - 1/(2*T1))))`(T1、T2 均配置时）;
  仅配置 T2 时为纯退相位 `p_φ = 0.5 * (1 - exp(-t / T2))`

约束：`T2 ≤ 2 * T1`（否则退相位概率为负，校验时报错）。门时长来自
`gate_times_ns`：优先取门名覆盖值，否则按 arity 取 `default_1q` / `default_2q`;
某 arity 没有默认值时该 arity 的门不施加热弛豫。

## 与 `dummy:<platform>:<chip>` 的噪声语义差异

两条路径最终都注入到同一台密度矩阵含噪模拟器，但噪声构造不同：

- `dummy:originq:WK_C180` 从**芯片标定数据**换算：2q 门噪声按比特分解为逐比特 1q
  depolarizing 近似，读出错误取 `avg_readout_fidelity` 对称拆分，T1/T2 不参与换算。
- `dummy:virtual:<name>` 按 **YAML 声明**构造：2q depolarizing 是**真双比特退极化
  通道**,T1/T2 通过 `gate_times_ns` 换算为热弛豫。

## 校验与错误排查

`uniqc backend virtual validate <name>` 会逐项校验：未知键、概率越界、拓扑边引用未声明
比特、`gate_instance` 边不在拓扑中、`t2_us > 2 * t1_us`、热弛豫缺少 `gate_times_ns`、
读出错误不是二元组等。提交任务时 preflight 也会加载配置，配置缺失或非法会在提交前
以带文件路径的错误信息失败。

`uniqc backend virtual list` 会同时列出合法与非法的配置文件（非法项标红并附原因）,
`uniqc backend list` / WebUI 只展示合法虚拟机（非法文件以 warning 形式跳过）。

## CLI 参考

| 命令 | 说明 |
|------|------|
| `uniqc backend virtual init <name> [--force]` | 在 `~/.uniqc/backend/virtual/` 生成带注释的模板 |
| `uniqc backend virtual list` | 列出全部虚拟机（名称、比特数、边数、噪声摘要、合法性） |
| `uniqc backend virtual show <name>` | 展示解析后的配置与派生噪声参数 |
| `uniqc backend virtual validate <name>` | 校验配置文件，退出码反映合法性 |
