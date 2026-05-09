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
