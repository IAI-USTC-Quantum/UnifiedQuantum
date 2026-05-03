# 云端任务提交 (`uniqc submit`)

将电路提交到量子云平台。

## 基本用法

```bash
# 提交单个电路
uniqc submit circuit.ir --platform originq --shots 1000

# 指定后端名称
uniqc submit circuit.ir --platform originq --backend WK_C180 --shots 1000

# 提交并等待结果
uniqc submit circuit.ir --platform originq --wait --timeout 300

# 试运行：不提交，仅验证电路兼容性
uniqc submit circuit.ir --platform originq --dry-run
```

## 批量提交

```bash
# 提交多个电路
uniqc submit circuit1.ir circuit2.ir circuit3.ir --platform originq
```

## 支持的平台

| 平台 | 说明 |
|------|------|
| `originq` | 本源量子云平台 |
| `quafu` | QUAFU 量子云平台 |
| `ibm` | IBM Quantum |
| `dummy` | 本地模拟器（用于测试） |

## 试运行模式 (`--dry-run`)

`--dry-run` 在不发起任何网络请求的情况下验证电路兼容性。检查项包括：

- 电路格式解析（OriginIR 或 OpenQASM 2.0）
- 目标平台的门集兼容性
- 量子比特数量是否超过后端限制
- 后端约束条件（拓扑、shots 上限等）

### 基本用法

```bash
# 试运行单个电路
uniqc submit circuit.ir --platform originq --dry-run

# 指定后端进行验证
uniqc submit circuit.ir --platform originq --backend WK_C180 --dry-run

# 批量试运行多个电路
uniqc submit circuit1.ir circuit2.ir --platform originq --dry-run
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
[DRY-RUN FAILED] Unsupported gate 'TOFFOLI' on platform 'quafu'
  Details: Gate 'TOFFOLI' is not in the supported gate set for Quafu.
```

批量输出（表格）：

```
┏━━━━━━━━━ Dry-Run Results ━━━━━━━━━━┓
┃ #   Status   Backend              Qubits   Details/Error            ┃
┃ 1   PASS     WK_C180                2      Circuit is valid         ┃
┃ 2   FAIL     —                    —        Unsupported gate 'T'   ┃
```

> **dummy 平台**：`--dry-run --platform dummy` 和 `backend="dummy"` 的 dry-run 验证现在支持 `backend="dummy"` 作为后端标识符，不再需要显式传入 `dummy=True`。

### 使用场景

- 在正式提交前验证电路是否被目标平台接受
- CI/CD 流水线中批量检查电路合规性
- 在没有云端凭证的环境中验证电路格式

## 输出格式

```bash
# 表格输出（默认）
uniqc submit circuit.ir --platform originq

# JSON 输出
uniqc submit circuit.ir --platform originq --format json
```
