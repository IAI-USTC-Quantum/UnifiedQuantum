# OriginIR、OriginIR-ext 与 OpenQASM 2.0 的关系

## 概览

UnifiedQuantum 支持三种量子线路描述语言，它们之间存在明确的超集-子集关系：

```
┌─────────────────────────────────────────────────────────────┐
│                    OriginIR-ext (超集)                       │
│  UnifiedQuantum 的默认本地编程语言                             │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              OriginIR (官方子集)                        │  │
│  │        本源量子云服务接受的格式                           │  │
│  │                                                        │  │
│  │    ┌──────────────────────────────────────────────┐    │  │
│  │    │           两者共有的基础门集                   │    │  │
│  │    │  H, X, Y, Z, S, SX, T, I                    │    │  │
│  │    │  RX, RY, RZ, U1, U2, U3                     │    │  │
│  │    │  CNOT, CZ, SWAP, TOFFOLI, CSWAP             │    │  │
│  │    └──────────────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  OriginIR-ext 额外支持：                                     │
│    门: ECR, ISWAP, XX, YY, ZZ, XY, PHASE2Q, UU15           │
│         RPhi, RPhi90, RPhi180                               │
│    特性: named register, DEF/ENDDEF, QRAM, error channels   │
│    语法: inline dagger, controlled_by                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  OpenQASM 2.0 (跨平台)                       │
│        IBM / Quafu / Quark 平台的提交格式                     │
│        与 OriginIR 有部分重叠，但非超集关系                     │
└─────────────────────────────────────────────────────────────┘
```

## 三种语言的定位

| 语言 | 定位 | 使用场景 |
|------|------|---------|
| **OriginIR-ext** | UnifiedQuantum 默认本地语言 | 本地编程、模拟、开发调试。`circuit.originir` 输出此格式 |
| **OriginIR** (官方) | 本源量子云服务接受的语言 | 提交到 OriginQ 云平台时自动转换为此格式 |
| **OpenQASM 2.0** | 跨平台标准 | 提交到 IBM、Quafu、Quark 平台 |

## OriginIR-ext 相对 OriginIR 的扩展

### 扩展门集

以下门在 OriginIR-ext 中可直接使用，提交到 OriginQ 云时会自动分解为官方门：

| 门 | 类型 | 分解为 |
|----|------|--------|
| `ECR` | 2q, 0p | X, RX, CNOT, S |
| `ISWAP` | 2q, 0p | S, H, CNOT |
| `XX(theta)` | 2q, 1p | H, CNOT, RZ |
| `YY(theta)` | 2q, 1p | RX, CNOT, RZ |
| `ZZ(theta)` | 2q, 1p | CNOT, RZ |
| `XY(theta)` | 2q, 1p | XX, YY (递归分解) |
| `PHASE2Q(t1,t2,tzz)` | 2q, 3p | U1, CU1 |
| `UU15(params)` | 2q, 15p | U3, XX, YY, ZZ (KAK 分解) |
| `RPhi(theta,phi)` | 1q, 2p | RZ, RX |
| `RPhi90(phi)` | 1q, 1p | RZ, RX |
| `RPhi180(phi)` | 1q, 1p | RZ, RX |

### 扩展特性

- **Named Register**: `QINIT`/`CREG` 支持命名量子/经典寄存器（如 `QINIT q1[6]`），多个寄存器按声明顺序扫平到同一物理索引空间；导出时始终扁平化为单一 `QINIT`/`CREG` 头部
- **DEF/ENDDEF**: 子程序定义块，形参签名复用 named register 语法（`DEF name(q[2]) (theta)`），支持标量参数化复用，调用时就地展开
- **QRAM**: `QRAMDECL` 声明和具名 XOR 查询指令，支持地址叠加态与受控调用；仅限受支持的本地模拟器，详见 {ref}`originir-ext-qram`
- **Error Channels**: 噪声模拟通道（Depolarizing, BitFlip, PhaseFlip 等）
- **Inline 语法**: `dagger` 后缀、`controlled_by(q[...])` 子句（替代 DAGGER/CONTROL 块）

> 扩展门可以分解成官方 OriginIR 门，但并非所有扩展特性都能转换。尤其是 QRAM 没有官方 OriginIR 或 OpenQASM 2.0 等价表示；转换器遇到 `QRAMDECL` 会明确报错。

## 转换路径

```text
可转换的 OriginIR-ext ──convert_originir_ext_to_originir()──▶ OriginIR（官方）
          │
          └──────────────── circuit.qasm ─────────────────▶ OpenQASM 2.0

OriginIR（官方）◀──────────── convert_qasm_to_oir() ──────── OpenQASM 2.0

含 QRAM 的 OriginIR-ext ──X──▶ OriginIR（官方）/ OpenQASM 2.0 / 云平台
```

### 编程接口

```python
from uniqc import Circuit
from uniqc.compile import convert_originir_ext_to_originir

c = Circuit(2)
c.h(0)
c.iswap(0, 1)          # OriginIR-ext 扩展门
c.xx(0, 1, 0.5)        # OriginIR-ext 扩展门

# 本地使用：OriginIR-ext 格式（默认）
print(c.originir)

# 提交到 OriginQ 云：自动转换为官方 OriginIR
print(c.originir_official)

# 手动转换
official_str = convert_originir_ext_to_originir(c.originir)
```

### 编译器管线中的转换

```python
from uniqc.compile import compile

# output_format="originir" → 输出官方 OriginIR（已分解扩展门）
result = compile(circuit, output_format="originir")

# output_format="originir-ext" → 输出 OriginIR-ext（保留扩展门）
result = compile(circuit, output_format="originir-ext")

# output_format="auto" → 根据输入自动选择（OriginIR 输入默认输出 originir-ext）
result = compile(circuit, output_format="auto")
```

## 何时使用哪种格式

- **日常开发**: 使用 OriginIR-ext。通过 `Circuit` API 构建线路，`circuit.originir` 即为 OriginIR-ext 格式
- **提交到 OriginQ 云**: 使用 `circuit.originir_official` 或 `compile(output_format="originir")`，扩展会自动分解
- **提交到 IBM/Quafu/Quark**: 使用 QASM 格式，`compile(output_format="qasm")` 或 `circuit.qasm`
- **本地模拟**: 接受 OriginIR-ext 格式，无需转换；QRAM 仅在支持该指令的本地 statevector / density-matrix 模拟器中执行

如果线路包含 QRAM，必须保留 OriginIR-ext 格式并在本地运行；不要调用官方 OriginIR/QASM 导出，也不能提交到上述云平台。

> 官方 OriginIR 的完整规范见 [OriginIR 官方规范](originir_official.md)。
> OriginIR-ext 的完整规范见 [OriginIR-ext 规范](originir.md)。
