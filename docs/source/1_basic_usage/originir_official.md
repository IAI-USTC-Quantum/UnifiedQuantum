# OriginIR 官方规范

## 什么是官方 OriginIR

官方 OriginIR 是本源量子云服务（OriginQ）接受的量子线路描述语言。它是 [OriginIR-ext](originir.md) 的**子集**——不包含扩展门、error channels 和 inline dagger/controlled_by 语法。

> **你通常不需要直接使用此规范。** UnifiedQuantum 默认使用 OriginIR-ext 作为本地语言，在提交到 OriginQ 云时会自动将扩展门分解为官方门、将 inline 语法转换为块语法。本文档仅供需要了解 OriginQ 云服务确切接受哪些特性的用户参考。

完整的关系说明见 [OriginIR、OriginIR-ext 与 OpenQASM 2.0 的关系](originir_relationship.md)。

---

## 官方门集

### 单量子比特门（无参数）

| 门 | 描述 |
|----|------|
| `H` | Hadamard 门 |
| `X` | Pauli-X (NOT) 门 |
| `Y` | Pauli-Y 门 |
| `Z` | Pauli-Z 门 |
| `S` | S（相位）门 |
| `SX` | √X 门 |
| `T` | T（π/8）门 |
| `I` | 恒等门 |

### 单量子比特参数门

| 门 | 参数 | 描述 |
|----|------|------|
| `RX(theta)` | 1 | 绕 X 轴旋转 |
| `RY(theta)` | 1 | 绕 Y 轴旋转 |
| `RZ(theta)` | 1 | 绕 Z 轴旋转 |
| `U1(lambda)` | 1 | 相位旋转 |
| `U2(phi, lambda)` | 2 | 通用单比特门（2参数） |
| `U3(theta, phi, lambda)` | 3 | 通用单比特门（3参数） |

### 双量子比特门

| 门 | 参数 | 描述 |
|----|------|------|
| `CNOT` | 0 | 受控 NOT 门 |
| `CZ` | 0 | 受控 Z 门 |
| `SWAP` | 0 | 交换门 |

### 三量子比特门

| 门 | 参数 | 描述 |
|----|------|------|
| `TOFFOLI` | 0 | Toffoli (CCNOT) 门 |
| `CSWAP` | 0 | Fredkin (受控 SWAP) 门 |

### 特殊操作

| 操作 | 描述 |
|------|------|
| `BARRIER` | 屏障（阻止编译器跨越优化） |

---

## 官方语法

### 程序结构

```text
QINIT <qubit_count>
CREG <classical_bit_count>

<gate_operations>

MEASURE q[i], c[j]
```

### 控制块语法

官方 OriginIR 使用**块级**控制和伴随语法：

```text
CONTROL q[0]
    H q[1]
ENDCONTROL

DAGGER
    RX q[0], (1.57)
ENDDAGGER
```

> **注意**：OriginIR-ext 支持 inline 语法（`H q[1] dagger controlled_by(q[0])`），但官方 OriginIR 不支持。提交到 OriginQ 云时，inline 语法会自动转换为块语法。

### 测量

```text
MEASURE q[0], c[0]
MEASURE q[1], c[1]
```

---

## 与 OriginIR-ext 的区别

| 特性 | 官方 OriginIR | OriginIR-ext |
|------|:---:|:---:|
| 基础门（H, X, CNOT 等） | Y | Y |
| ECR, ISWAP, XX, YY, ZZ, XY | - | Y |
| PHASE2Q, UU15 | - | Y |
| RPhi, RPhi90, RPhi180 | - | Y |
| DEF/ENDDEF 子程序 | - | Y |
| Error Channels | - | Y |
| inline `dagger` 语法 | - | Y |
| inline `controlled_by` 语法 | - | Y |
| CONTROL/ENDCONTROL 块 | Y | Y |
| DAGGER/ENDDAGGER 块 | Y | Y |

当 OriginIR-ext 代码提交到 OriginQ 云时，扩展门会通过 `decompose_for_originir()` 自动分解为官方门，inline 语法会通过 `opcode_to_line_originir_official()` 转换为块语法。
