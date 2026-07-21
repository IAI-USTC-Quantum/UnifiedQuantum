# CLI 快速上手：提交 GHZ 电路到云端

本目录包含一个 4-qubit GHZ 态制备电路，分别以两种格式保存：

| 文件 | 格式 | 适用平台 |
|------|------|---------|
| `circuit.originir` | OriginIR | OriginQ、QuarkStudio、Dummy |
| `circuit.qasm` | OpenQASM 2.0 | IBM |

## 前置条件

### 1. 安装 CLI

```bash
uv tool install unified-quantum
```

### 2. 配置平台凭证

```bash
# 初始化配置文件
python -m uniqc.cli config init

# 设置各平台 API Token
python -m uniqc.cli config set originq.token YOUR_ORIGINQ_TOKEN
python -m uniqc.cli config set quark.QUARK_API_KEY YOUR_QUARK_TOKEN
python -m uniqc.cli config set ibm.token     YOUR_IBM_TOKEN
```

---

## 第一步：验证连接性

提交任务前，优先验证凭证是否有效、平台是否可达：

```bash
# 验证所有已配置平台的凭证
python -m uniqc.cli config validate

# 单独查看某个平台的配置状态
python -m uniqc.cli config get originq
python -m uniqc.cli config get quark
python -m uniqc.cli config get ibm
```

预期输出示例（有效凭证）：
```
Platform: originq
  token:   ✅ configured
Platform: quark
  QUARK_API_KEY: ✅ configured
Platform: ibm
  token:   ✅ configured
```

---

## 第二步：查看可用后端

```bash
# 列出所有平台的可用后端（默认只显示 available）
python -m uniqc.cli backend list

# 仅看 QuarkStudio 平台
python -m uniqc.cli backend list -p quark

# 仅看 IBM 平台
python -m uniqc.cli backend list -p ibm

# 显示后端详情（含保真度信息）
python -m uniqc.cli backend list -p quark --info
python -m uniqc.cli backend list -p ibm --info

# 强制从云端刷新后端列表
python -m uniqc.cli backend update
```

### 查看后端详情和芯片标定

```bash
# 查看单个后端的完整信息（含保真度和拓扑）
python -m uniqc.cli backend show originq:wuyuan:d5
python -m uniqc.cli backend show originq:simulator:01

# 查看芯片逐量子比特标定数据
python -m uniqc.cli backend chip-display originq/wuyuan:d5

# 强制刷新标定数据
python -m uniqc.cli backend chip-display originq/wuyuan:d5 --update
```

输出示例：
```
Platform: quark
  Name                Status       Type      Qubits
  Baihua             available    hw
  Dongling           available    hw

Platform: ibm
  Name                Status       Type      Qubits
  ibm_fez            available    hw       127
  ibm_marrakesh      available    hw        127
```

---

## 第三步：提交线路

### 方式 A：提交后立即返回 task_id（异步）

```bash
# 提交到 QuarkStudio（OriginIR 格式，需指定 chip）
python -m uniqc.cli submit circuit.originir --backend quark:Baihua -s 1000

# 提交到 IBM（QASM 格式，需指定 chip）
python -m uniqc.cli submit circuit.qasm --backend ibm:ibm_fez -s 1000

# 等价的 -b 简写
python -m uniqc.cli submit circuit.originir -b quark:Baihua -s 1000
python -m uniqc.cli submit circuit.qasm -b ibm:ibm_fez -s 1000
```

成功后会返回类似以下内容：
```
✅ Task submitted successfully!
   Task ID:  abc123def456
   Platform: quark
   Backend:  Baihua
   Shots:    1000
```

### 方式 B：提交后阻塞等待结果（同步）

```bash
# 同步提交，等结果最久等 300 秒
python -m uniqc.cli submit circuit.originir --backend quark:Baihua -s 1000 --wait --timeout 300
python -m uniqc.cli submit circuit.qasm --backend ibm:ibm_fez -s 1000 --wait --timeout 300
```

---

### 试运行（不提交）

在正式提交前，可使用 `--dry-run` 在不发起网络请求的情况下验证电路兼容性：

```bash
# 单电路试运行
python -m uniqc.cli submit circuit.originir --backend quark:Baihua --dry-run

# 指定不同的 chip 进行验证
python -m uniqc.cli submit circuit.originir --backend originq:WK_C180 --dry-run

# 批量试运行
python -m uniqc.cli submit circuit1.originir circuit2.originir --backend originq:WK_C180 --dry-run
```

---

## 第四步：查询结果

提交成功后，用返回的 `task_id` 查询结果：

```bash
# 查询结果（异步轮询，最久等 300 秒）
python -m uniqc.cli result <task_id> -p quark --wait --timeout 300
python -m uniqc.cli result <task_id> -p ibm --wait --timeout 300

# 不等待，直接查询当前状态
python -m uniqc.cli result <task_id> -p quark
python -m uniqc.cli result <task_id> -p ibm
```

输出示例（`--format table`）：
```
Task ID:  abc123def456
Status:   success
Platform: quark

Bitstring    Shots    Probability
  0000        502        50.2%
  1111        498        49.8%
```

---

## 完整流程示例（QuarkStudio）

```bash
# 1. 验证凭证
python -m uniqc.cli config validate

# 2. 查看可用后端
python -m uniqc.cli backend list -p quark

# 3. 同步提交（一步到位）
python -m uniqc.cli submit circuit.originir --backend quark:Baihua -s 1000 --wait --timeout 300

# 或分步操作：
# 3a. 提交（异步）
python -m uniqc.cli submit circuit.originir --backend quark:Baihua -s 1000
#   → 拿到 task_id：abc123def456

# 3b. 轮询结果
python -m uniqc.cli result abc123def456 -p quark --wait --timeout 300
```

## 完整流程示例（IBM）

```bash
# 1. 验证凭证
python -m uniqc.cli config validate

# 2. 查看可用后端
python -m uniqc.cli backend list -p ibm

# 3. 提交（IBM 接受 QASM 格式）
python -m uniqc.cli submit circuit.qasm --backend ibm:ibm_fez -s 1000 --wait --timeout 300
```

## 结果格式说明

所有平台的 `wait_for_result()` / `result` 命令返回统一格式：**扁平 `{bitstring: shots}` 字典**，无需按平台分别适配。

| 平台 | `result["result"]` 结构 | 示例 |
|------|------------------------|------|
| OriginQ | `{bitstring: shots}` 扁平 dict | `{"0000": 502, "1111": 498}` |
| QuarkStudio | `{bitstring: shots}` 扁平 dict | `{"0000": 502, "1111": 498}` |
| IBM | `{bitstring: shots}` 扁平 dict（单电路） | `{"0000": 502, "1111": 498}` |
| Dummy | `{bitstring: shots}` 扁平 dict | `{"0000": 502, "1111": 498}` |

批量提交（`submit_batch`）时，`result["result"]` 为扁平 dict 列表：`[{"0000": 502, ...}, {"1111": 498, ...}]`。

> 详见 [平台约定文档](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/blob/main/docs/source/guide/platform_conventions.md)。
