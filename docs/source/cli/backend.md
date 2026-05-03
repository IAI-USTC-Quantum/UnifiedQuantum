# 后端管理 (`uniqc backend`)

列出、检查和刷新量子云平台后端信息。

## 概述

`uniqc backend` 默认行为等同于 `uniqc backend list`，直接输出后端列表。支持 4 个子命令：

| 子命令 | 说明 |
|--------|------|
| `list` | 列出所有平台的后端（默认） |
| `update` | 强制从云端 API 刷新后端列表缓存 |
| `show` | 显示单个后端的详细信息 |
| `chip-display` | 显示芯片逐量子比特标定数据 |

所有子命令支持 `--ai-hints` 标志（也可通过环境变量 `UNIQC_AI_HINTS=1` 启用），用于显示 AI 工作流提示。

## 列出后端 (`uniqc backend list`)

### 基本用法

### 仅显示指定平台

```bash
uniqc backend list --platform originq
uniqc backend list --platform quafu
uniqc backend list --platform ibm

# 短格式
uniqc backend list -p originq
```

### 状态与类型筛选

```bash
# 只看硬件后端（真实量子设备）
uniqc backend list --status hardware

# 只看模拟器后端
uniqc backend list --status simulator

# 显示所有后端（含 deprecated / unavailable）
uniqc backend list --all
```

### 显示附加信息

```bash
# 显示 1Q/2Q 保真度和 T1/T2 相干时间
uniqc backend list --info
```

`--info` 模式下额外显示 1Q Fid. 和 2Q Fid. 列。示例输出：

```
┏━━━━━━━━━━━━━━━━━ Available Backends ━━━━━━━━━━━━━━━━━━━┓
┃ Platform  Name                    Qubits  Status    Type ┃
┃ originq   WK_C180                    180  available  hw  ┃
┃ originq   origin:simulator:01          0  available  sim ┃
┃ quafu     ScQ-P18                     18  available  hw  ┃
┃ ibm       ibm_fez                    127  available  hw  ┃
```

### 输出格式

```bash
# 表格输出（默认）
uniqc backend list

# JSON 输出
uniqc backend list --format json
```

## 刷新后端缓存 (`uniqc backend update`)

### 基本用法

```bash
# 强制刷新所有平台的缓存（绕过 24 小时缓存）
uniqc backend update

# 只刷新指定平台
uniqc backend update --platform originq
uniqc backend update -p originq

# 清除缓存后强制重新拉取
uniqc backend update --clear
uniqc backend update -c
```

> 默认情况下，后端列表缓存有效期为 24 小时。如平台侧更新了硬件拓扑或新增后端，需运行此命令使列表同步。

## 查看后端详情 (`uniqc backend show`)

### 基本用法

```bash
# 查看单个后端详情
uniqc backend show originq:WK_C180
uniqc backend show originq:PQPUMESH8
uniqc backend show originq:full_amplitude
```

### 输出格式

```bash
# 详细表格输出（默认，rich 格式）
uniqc backend show originq:WK_C180

# JSON 输出
uniqc backend show originq:WK_C180 --format json
```

rich 格式输出包含以下面板：

- **Overview** — 平台、名称、类型（Hardware / Simulator）、量子比特数、状态
- **Fidelity & Coherence**（若有数据）— 1Q 保真度、2Q 保真度、读出保真度、T1 / T2 相干时间
- **Qubit Topology** — 连接拓扑边列表（仅限非模拟器后端）
- **Additional Information** — 平台返回的额外字段

## 芯片标定数据 (`uniqc backend chip-display`)

显示指定芯片的逐量子比特标定数据，包括 T1/T2 相干时间、单量子比特门保真度、读出保真度（R0 / R1 / 平均）以及双量子比特门保真度。

### 基本用法

```bash
# 查看芯片标定数据（使用缓存，若无缓存则自动拉取）
uniqc backend chip-display originq/WK_C180
uniqc backend chip-display quafu/ScQ-P18
uniqc backend chip-display ibm/sherbrooke
```

### 强制刷新

```bash
# 强制从云端重新拉取标定数据
uniqc backend chip-display originq/WK_C180 --update
uniqc backend chip-display originq/WK_C180 -u
```

### 输出内容

该命令输出两个表格：

**逐量子比特数据（Per-Qubit Data）**

| 列 | 说明 |
|----|------|
| ID | 量子比特编号 |
| T1 (μs) | T1 相干时间（微秒） |
| T2 (μs) | T2 相干时间（微秒） |
| 1Q Fid. | 单量子比特门平均保真度 |
| R0 | 读出保真度 P(0\|0) |
| R1 | 读出保真度 P(1\|1) |
| Avg R | 平均读出保真度 |

**逐对双量子比特门数据（Per-Pair 2Q Gate Data）**

| 列 | 说明 |
|----|------|
| Qubit U / V | 量子比特对编号 |
| Gate | 门类型（如 CNOT、CZ） |
| Fidelity | 该量子比特对的双量子比特门保真度 |

> 标定数据可用于量子比特选择（RegionSelector）和噪声感知编译（`compile()`），详见[编译选项与区域选择](../guide/compiler_options_region.md)。

## 完整工作流

```bash
# 1. 验证凭证
uniqc config validate

# 2. 查看可用后端
uniqc backend list --platform originq

# 3. 查看后端详情（含保真度和拓扑）
uniqc backend show originq:WK_C180

# 4. 查看芯片标定数据
uniqc backend chip-display originq/WK_C180 --update

# 5. 提交任务（使用查得的后端名）
uniqc submit circuit.ir --platform originq --backend WK_C180 --shots 1000
```

## 选项速查

| 选项 | 作用域 | 说明 |
|------|--------|------|
| `--platform`, `-p` | `list`, `update` | 仅显示/刷新指定平台 |
| `--status`, `-s` | `list` | 按状态筛选：available / unavailable / deprecated / simulator / hardware |
| `--all`, `-a` | `list` | 显示所有后端（含 unavailable） |
| `--info`, `-i` | `list` | 显示保真度和相干时间数据 |
| `--format` | `list` | 输出格式：`table`（默认）或 `json` |
| `--clear`, `-c` | `update` | 清除缓存后强制刷新 |
| `--format` | `show` | 输出格式：`rich`（默认）或 `json` |
| `--update`, `-u` | `chip-display` | 强制从云端刷新标定数据 |
