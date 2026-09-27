# 本地模拟 (`uniqc simulate`)

在本地运行量子电路模拟。

## 基本用法

```bash
# 使用状态向量后端，默认 1024 shots
uniqc simulate circuit.ir

# 指定后端和 shots 数
uniqc simulate circuit.ir --backend statevector --shots 1000

# 使用密度矩阵后端
uniqc simulate circuit.ir --backend density --shots 2048
```

## 输出格式

```bash
# 表格输出（默认）
uniqc simulate circuit.ir

# JSON 输出
uniqc simulate circuit.ir --format json

# 输出到文件
uniqc simulate circuit.ir --output result.json
```

表格输出示例：

```
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Simulation Results        ┃            ┃
┡━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┩
│ State │ Count │ Probability│
├───────┼───────┼────────────┤
│ 00    │ 498   │ 49.8%      │
│ 11    │ 502   │ 50.2%      │
└───────┴───────┴────────────┘
```

## 后端类型

| 后端 | 说明 |
|------|------|
| `statevector` | 状态向量模拟器，返回精确概率分布 |
| `density` | 密度矩阵模拟器，支持噪声模拟 |

## 相关文档

- [本地模拟](../1_basic_usage/simulation.md) —— 模拟器家族总览、噪声与选型建议
- [MPS 模拟器](../2_advanced/mps_simulator.md) —— 大比特数、线性拓扑的替代后端
- [动态电路](../2_advanced/dynamic_circuits.md) —— `QIF` / `QWHILE` 电路的 per-shot 采样
- [提交任务](submit.md) —— 把电路提交到云端后端
- [结果查询](result.md) —— 查询云端任务结果
