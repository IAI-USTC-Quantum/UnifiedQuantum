# 电路格式转换 (`uniqc circuit`)

在 OriginIR 和 OpenQASM 2.0 格式之间转换电路。

## 基本用法

```bash
# 自动检测输入格式，转换为另一种格式
uniqc circuit input.ir

# 指定输出格式
uniqc circuit input.ir --format qasm

# 输出到文件
uniqc circuit input.ir --format qasm --output circuit.qasm
```

## 查看电路统计信息

```bash
uniqc circuit input.ir --info
```

输出示例：

```
┏━━━━━━━━━━━┳━━━━━━━┓
┃ Property  ┃ Value ┃
┡━━━━━━━━━━━╇━━━━━━━┩
│ Qubits    │ 2     │
│ Cbits     │ 2     │
│ Depth     │ 2     │
│ Gates     │ 3     │
└───────────┴───────┘
```

## 支持的格式

| 格式 | 说明 |
|------|------|
| `originir` | UnifiedQuantum 原生格式 |
| `qasm` | OpenQASM 2.0 格式 |

## 相关文档

- [构建量子线路](../1_basic_usage/circuit.md) —— `Circuit` 对象的构建与格式转换 API
- [OriginIR-ext 规范](../1_basic_usage/originir.md) —— 原生格式的语法
- [OpenQASM 2.0 支持](../1_basic_usage/qasm.md) —— QASM 门集覆盖与限制
- [线路分析](../2_advanced/circuit_analysis.md) —— `--info` 背后的 Python API 与可视化
- [线路绘制](draw.md) —— 把电路文件渲染成图
