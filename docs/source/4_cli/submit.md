# 云端任务提交 (`uniqc submit`)

将电路提交到量子云平台。

后端命名规则和典型示例见 [提交任务 → 后端命名规则](../1_basic_usage/submit_task.md#guide-submit-task-backend-naming)。

## 基本用法

```bash
# 提交到 OriginQ 真机（需要 token）
uniqc submit circuit.ir --backend originq:WK_C180 --shots 1000

# 提交到 OriginQ 全振幅模拟器
uniqc submit circuit.ir --backend originq:full_amplitude --shots 1000

# 提交到 IBM Quantum
uniqc submit circuit.ir --backend ibm:ibm_brisbane --shots 1000

# 使用 dummy 本地模拟（默认后端）
uniqc submit circuit.ir                        # 等价于 --backend dummy:local:simulator
uniqc submit circuit.ir --backend dummy        # 同上，简写

# 提交并等待结果
uniqc submit circuit.ir --backend originq:WK_C180 --wait --timeout 300

# 试运行：不提交，仅验证电路兼容性
uniqc submit circuit.ir --backend originq:WK_C180 --dry-run
```

## Dummy 后端

```bash
# 无约束、无噪声（默认）
uniqc submit circuit.ir --backend dummy

# 虚拟线性拓扑
uniqc submit circuit.ir --backend dummy:local:virtual-line-3

# 虚拟网格拓扑
uniqc submit circuit.ir --backend dummy:local:virtual-grid-2x2

# MPS 模拟器（隐式参数 chi/cutoff 可选）
uniqc submit circuit.ir --backend dummy:local:mps-linear-32:chi=64:cutoff=1e-10

# 真实 backend 的本地含噪仿真
uniqc submit circuit.ir --backend dummy:originq:WK_C180
```

> `dummy:<platform>:<backend>` 是规则型写法，不会作为独立 backend 列表项展示；提交时会先按真实 backend compile/transpile，再在本地 dummy 上执行含噪模拟。完整后端命名规则见 [提交任务 → 后端命名规则](../1_basic_usage/submit_task.md#guide-submit-task-backend-naming)。

## 批量提交

```bash
# 提交多个电路
uniqc submit circuit1.ir circuit2.ir circuit3.ir --backend originq:WK_C180
```

## 支持的平台

| 平台 | 说明 |
|------|------|
| `originq` | 本源量子云平台 |
| `ibm` | IBM Quantum |
| `dummy` | 本地模拟器（用于测试） |

## 试运行模式 (`--dry-run`)

`--dry-run` 在不发起任何网络请求的情况下验证电路兼容性。检查项包括：

- 电路格式解析（OriginIR 或 OpenQASM 2.0）
- 目标后端的门集兼容性
- 量子比特数量是否超过后端限制
- 后端约束条件（拓扑、shots 上限等）

### 基本用法

```bash
# 试运行单个电路
uniqc submit circuit.ir --backend originq:WK_C180 --dry-run

# Dummy 后端试运行
uniqc submit circuit.ir --backend dummy --dry-run

# 批量试运行多个电路
uniqc submit circuit1.ir circuit2.ir --backend originq:WK_C180 --dry-run
```

### 输出示例

通过：

```
[DRY-RUN PASSED] Circuit is valid for backend 'originq' with 2 qubits
  Backend: WK_C180
  Circuit qubits: 2
```

失败：

```
[DRY-RUN FAILED] Unsupported gate 'TOFFOLI' on platform 'ibm'
  Details: Gate 'TOFFOLI' is not in the supported gate set for IBM.
```

批量输出（表格）：

```
┏━━━━━━━━━ Dry-Run Results ━━━━━━━━━━┓
┃ #   Status   Backend              Qubits   Details/Error            ┃
┃ 1   PASS     WK_C180                2      Circuit is valid         ┃
┃ 2   FAIL     —                    —        Unsupported gate 'T'   ┃
```

### 使用场景

- 在正式提交前验证电路是否被目标后端接受
- CI/CD 流水线中批量检查电路合规性
- 在没有云端凭证的环境中验证电路格式

## 输出格式

```bash
# 表格输出（默认）
uniqc submit circuit.ir --backend originq:WK_C180

# JSON 输出
uniqc submit circuit.ir --backend originq:WK_C180 --format json
```
