# OriginIR-ext 规范

> **本文档是 OriginIR-ext 的权威语言规范**——UnifiedQuantum 的默认本地量子线路描述语言，官方 OriginIR 的超集。
>
> 官方 OriginIR 子集（本源量子云服务接受）见 [OriginIR 官方规范](originir_official.md)；三种语言（OriginIR / OriginIR-ext / OpenQASM 2.0）的关系见 [语言关系说明](originir_relationship.md)。

## 什么时候进入本页

- 你需要理解 `circuit.originir` 输出文本的格式，或想手写 OriginIR-ext 文本
- 你在排查解析错误、序列化差异、提交被拒等格式相关问题
- 你想查阅某条指令的精确语法、参数与边界（导出 / 提交 / 模拟器支持矩阵）

> 如果你还不知道如何用 Python API 构建线路，请先读 [构建量子线路](circuit.md)。本文档是**语言参考**，不是入门教程。

## 设计立场

**内部表示 vs 导出格式。** 线路在内存中以 `Circuit` 对象及其 `opcode_list: list[OpcodeType]` 存储（`uniqc.circuit_builder.opcode`）。`.originir` 与 `.qasm` 都是把 opcode 序列序列化为文本的**导出视图**，不是内部存储格式。模拟器直接消费 opcode，不经过 OriginIR 文本中转。

**默认本地语言。** `circuit.originir` 输出 OriginIR-ext。提交 OriginQ 云时，扩展门自动经 {func}`uniqc.compile.decompose_for_originir` 降级为官方 OriginIR；动态电路扩展和 QRAM 不能降级，会被明确拒绝而不是静默丢弃。

---

## 程序结构

一个 OriginIR-ext 程序由头部、可选子程序定义、主体程序、可选末尾测量组成：

```text
[QRAMDECL 声明 ...]        # 可选；必须在 QINIT 之前（仅 OriginIR-ext）
QINIT <声明>               # 必需；可重复出现或多寄存器单行
[PARAM <声明>]             # 可选；可出现在头部任意位置（仅 OriginIR-ext）
CREG <声明>                # 必需；可重复出现或多寄存器单行；任何 CREG 必须在所有 QINIT 之后

[DEF 块定义 ...]           # 可选；子程序定义（仅 OriginIR-ext）

<主体: 量子门 / 测量 / 复位 / 控制块 / DEF 调用 / QRAM 调用 / 动态指令>

[MEASURE ...]              # 可选；末端测量
```

**硬性约束**（由 `uniqc.compile.originir.originir_base_parser._extract_header` 强制）：

- `QINIT` 与 `CREG` 至少各出现一次
- **任何 `QINIT` 不能出现在 `CREG` 之后**——否则报错
- `QRAMDECL` 必须位于 `QINIT` 之前；`PARAM` 是唯一可在头部任意位置插入的声明

---

## 头部语句

### QINIT

声明量子比特寄存器。支持三种等价形式（解析器在 `originir_base_parser._parse_register_decl`）：

```text
QINIT <n>                       # 裸整数；等价于 QINIT q[<n>]
QINIT <name>[<size>]            # 命名寄存器
QINIT <n1>[<s1>], <n2>[<s2>]    # 一行声明多个命名寄存器
```

- `<name>` 必须匹配 `[A-Za-z_][A-Za-z0-9_]*`
- 多条 `QINIT` 语句**累积**生效，物理索引按声明顺序接续
- 所有寄存器**扫平**到同一个物理索引空间；例如 `QINIT q[6]` 后再 `QINIT anc[2]`，则 `anc[0]` 占物理比特 6、`anc[1]` 占物理比特 7
- 量子寄存器名与经典寄存器名空间相互独立，但同名不能同时用于两者

**导出始终扫平。** 命名寄存器只存在于源文本与构建期。解析后所有引用立即映射为物理索引；`circuit.originir` / `to_extended_originir()` 始终输出单条 `QINIT <total>` 头部与物理 `q[i]` 操作数，**不保留**寄存器名。

```text
QINIT 5                     # 等价于 QINIT q[5]
QINIT q[6]
QINIT data[4], anc[2]       # 一行多寄存器；data→0-3，anc→4-5
```

### CREG

声明经典比特寄存器，语法与 `QINIT` 对称：

```text
CREG <n>
CREG <name>[<size>]
CREG <n1>[<s1>], <n2>[<s2>]
```

经典比特用于存储测量结果，并作为动态电路扩展中经典指令与控制条件的操作数（见 [动态电路扩展](originir-ext-dynamic)）。

(originir-ext-param)=
### PARAM

`PARAM` 是 OriginIR-ext 的**符号参数头**（仅本地模拟；与 Python 侧 {class}`uniqc.circuit_builder.parameter.Parameter` / `Parameters` 对应）。声明在头部，可以被后续门的角度槽位以符号表达式引用。

```text
PARAM <name>                 # 标量参数
PARAM <name>[<size>]         # 数组参数；展开为 <name>_0 ... <name>_<size-1>
```

**示例：**

```text
QINIT 2
CREG 0
PARAM theta
PARAM alpha[4]

RX q[0], (theta)             # 标量引用
RY q[1], (alpha[2])          # 数组元素引用；解析时重写为 alpha_2
RZ q[0], (2*theta + alpha_0/3)   # 算术表达式
```

**表达式约束**（解析器正则在 `originir_line_parser._parse_param`）：

- 数组元素 `name[idx]` 在解析时重写为符号 `name_idx`
- 表达式通过 sympy 解析；**不能包含逗号或括号**（即不能有嵌套分组或函数调用）
- 复杂角度请拆成多个具名参数
- 标识符不与 sympy 内置符号（`I`、`E`、`pi`、`gamma` 等）冲突——解析器会把每个标识符强制为普通 `Symbol`

未绑定的 `PARAM` 符号可以序列化回 OriginIR-ext 文本，但**不能**直接模拟、导出为官方 OriginIR / OpenQASM 或提交云。绑定前请先通过 {meth}`uniqc.circuit_builder.Circuit.assign_parameters` 赋具体值。

---

## 量子门

### 量子比特与经典比特引用

```text
q[<i>]              # 默认量子寄存器的物理比特 i
<qreg>[<i>]         # 命名量子寄存器（解析时映射到物理索引）
c[<j>]              # 默认经典寄存器的比特 j
<creg>[<j>]         # 命名经典寄存器
```

多量子比特门用逗号分隔：`CNOT q[0], q[1]`、`TOFFOLI q[0], q[1], q[2]`。

### 参数语法

带参数的门用圆括号包裹参数列表：

```text
RX q[0], (1.57)                     # 单参数
U2 q[0], (1.57, 0.785)              # 双参数
U3 q[0], (1.57, 0.785, 0.392)       # 三参数
```

数值字面量支持：整数（`0`、`-1`）、浮点（`0.5`、`1.57`）、科学计数法（`1.5e-3`）。符号表达式语法见上文 [PARAM 节](originir-ext-param)。

> **矩阵约定。** 下文给出的矩阵采用与 {mod}`uniqc.circuit_builder.matrix` 一致的标准基。1 量子比特门使用基 $|0\rangle, |1\rangle$；2 量子比特门使用基 $|00\rangle, |01\rangle, |10\rangle, |11\rangle$（操作数按 `gate q[a], q[b]` 中 $a$ 为高位、$b$ 为低位的顺序展开）。所有精确实现以该模块为准。

### 单量子比特门

#### 无参数

| 门 | 描述 | 矩阵 |
|----|------|------|
| `H` | Hadamard | $\frac{1}{\sqrt{2}}\begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}$ |
| `X` | Pauli-X（NOT） | $\begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$ |
| `Y` | Pauli-Y | $\begin{pmatrix} 0 & -i \\ i & 0 \end{pmatrix}$ |
| `Z` | Pauli-Z | $\begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$ |
| `S` | 相位门 | $\begin{pmatrix} 1 & 0 \\ 0 & i \end{pmatrix}$ |
| `SX` | $\sqrt{X}$ | $\frac{1}{2}\begin{pmatrix} 1+i & 1-i \\ 1-i & 1+i \end{pmatrix}$ |
| `T` | $\pi/8$ 门 | $\begin{pmatrix} 1 & 0 \\ 0 & e^{i\pi/4} \end{pmatrix}$ |
| `I` | 恒等 | $\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$ |

语法：`<GATE> q[<i>]`

#### 单参数

| 门 | 描述 | 矩阵 |
|----|------|------|
| `RX` | 绕 X 轴旋转 | $e^{-i\theta X/2}=\begin{pmatrix} \cos\frac\theta2 & -i\sin\frac\theta2 \\ -i\sin\frac\theta2 & \cos\frac\theta2 \end{pmatrix}$ |
| `RY` | 绕 Y 轴旋转 | $e^{-i\theta Y/2}=\begin{pmatrix} \cos\frac\theta2 & -\sin\frac\theta2 \\ \sin\frac\theta2 & \cos\frac\theta2 \end{pmatrix}$ |
| `RZ` | 绕 Z 轴旋转 | $e^{-i\theta Z/2}=\begin{pmatrix} e^{-i\theta/2} & 0 \\ 0 & e^{i\theta/2} \end{pmatrix}$ |
| `U1` | 相位旋转 | $\begin{pmatrix} 1 & 0 \\ 0 & e^{i\lambda} \end{pmatrix}$ |
| `RPhi90` | $RPhi(\pi/2,\phi)$ | 见 `RPhi` |
| `RPhi180` | $RPhi(\pi,\phi)$ | 见 `RPhi` |

语法：`<GATE> q[<i>], (<theta>)`

#### 双参数

| 门 | 描述 | 矩阵 |
|----|------|------|
| `RPhi` | 带 Z 旋转包络的 RX | $RPhi(\theta,\phi)=RZ(\phi)\,RX(\theta)\,RZ(-\phi)$ |
| `U2` | 通用 1q 旋转 | $U2(\phi,\lambda)=U3(\tfrac\pi2,\phi,\lambda)$ |

语法：`<GATE> q[<i>], (<p1>, <p2>)`

#### 三参数

| 门 | 矩阵 |
|----|------|
| `U3` | $U3(\theta,\phi,\lambda)=\begin{pmatrix} \cos\frac\theta2 & -e^{i\lambda}\sin\frac\theta2 \\ e^{i\phi}\sin\frac\theta2 & e^{i(\phi+\lambda)}\cos\frac\theta2 \end{pmatrix}$ |

语法：`U3 q[<i>], (<theta>, <phi>, <lambda>)`

### 双量子比特门

#### 无参数

| 门 | 描述 | 矩阵 |
|----|------|------|
| `CNOT` / `CX` | 受控非门 | $\begin{pmatrix} 1&0&0&0 \\ 0&1&0&0 \\ 0&0&0&1 \\ 0&0&1&0 \end{pmatrix}$ |
| `CZ` | 受控 Z | $\begin{pmatrix} 1&0&0&0 \\ 0&1&0&0 \\ 0&0&1&0 \\ 0&0&0&-1 \end{pmatrix}$ |
| `SWAP` | 交换 | $\begin{pmatrix} 1&0&0&0 \\ 0&0&1&0 \\ 0&1&0&0 \\ 0&0&0&1 \end{pmatrix}$ |
| `ISWAP` | i-SWAP（ext 扩展） | $\begin{pmatrix} 1&0&0&0 \\ 0&0&i&0 \\ 0&i&0&0 \\ 0&0&0&1 \end{pmatrix}$ |
| `ECR` | 弹性 Cross-Resonance（ext 扩展） | 见 {func}`uniqc.circuit_builder.matrix._ecr` |

语法：`<GATE> q[<a>], q[<b>]`

> ECR 的精确矩阵在 `uniqc.circuit_builder.matrix._ecr()` 中定义为 $\frac{1}{\sqrt{2}}$ 归一化的固定 4×4 复矩阵；本文档不重抄以免与代码漂移。

#### 单参数

| 门 | 描述 | 矩阵（$c=\cos\frac\theta2,\ s=\sin\frac\theta2$） |
|----|------|------|
| `XX` | XX 交互 | $\begin{pmatrix} c&0&0&-is \\ 0&c&-is&0 \\ 0&-is&c&0 \\ -is&0&0&c \end{pmatrix}$ |
| `YY` | YY 交互 | $\begin{pmatrix} c&0&0&is \\ 0&c&-is&0 \\ 0&-is&c&0 \\ is&0&0&c \end{pmatrix}$ |
| `ZZ` | ZZ 交互 | $\mathrm{diag}(e^{-i\theta/2},\ e^{i\theta/2},\ e^{i\theta/2},\ e^{-i\theta/2})$ |
| `XY` | XY 交互 | $\begin{pmatrix} 1&0&0&0 \\ 0&c&is&0 \\ 0&is&c&0 \\ 0&0&0&1 \end{pmatrix}$ |

语法：`<GATE> q[<a>], q[<b>], (<theta>)`

#### 三参数

| 门 | 矩阵 |
|----|------|
| `PHASE2Q` | $\mathrm{diag}(1,\ e^{it_1},\ e^{it_2},\ e^{i(t_1+t_2+t_{zz})})$ |

语法：`PHASE2Q q[<a>], q[<b>], (<t1>, <t2>, <tzz>)`

#### 十五参数

| 门 | 描述 |
|----|------|
| `UU15` | 最一般的 2q 幺正，Cartan / KAK 分解形式：$(U_3(c)\otimes U_3(d))\cdot RZZ(t_{zz})\cdot RYY(t_{yy})\cdot RXX(t_{xx})\cdot(U_3(b)\otimes U_3(a))$；15 个参数顺序为 $(a_0,a_1,a_2,b_0,b_1,b_2,t_{xx},t_{yy},t_{zz},c_0,c_1,c_2,d_0,d_1,d_2)$，$a$ 为低位比特 |

语法：`UU15 q[<a>], q[<b>], (<p1>, ..., <p15>)`

### 三量子比特门

| 门 | 描述 |
|----|------|
| `TOFFOLI` / `CCX` | 双控制 NOT |
| `CSWAP` | 受控交换（Fredkin） |

语法：`<GATE> q[<a>], q[<b>], q[<c>]`

### BARRIER

`BARRIER` 阻止编译器跨越它对相邻操作做重排或合并。

```text
BARRIER q[<a>], q[<b>], ...
```

**约束**（解析器正则 `originir_line_parser.regexp_barrier_str`）：**至少需要 1 个量子比特**；无操作数的整线 `BARRIER` 不会被接受。

### 官方门与扩展门总览

下表把 30 个本语言接受的门按"官方 OriginIR 也接受"和"仅 OriginIR-ext"两列分开。提交 OriginQ 云时，仅 ext 列的门会被自动分解为官方门。

| 类别 | 官方 OriginIR | 仅 OriginIR-ext |
|------|---------------|-----------------|
| 1q 无参 | `H X Y Z S SX T I` | — |
| 1q 单参 | `RX RY RZ U1` | `RPhi90 RPhi180` |
| 1q 双参 | `U2` | `RPhi` |
| 1q 三参 | `U3` | — |
| 2q 无参 | `CNOT CZ SWAP` | `ISWAP ECR` |
| 2q 单参 | — | `XX YY ZZ XY` |
| 2q 三参 | — | `PHASE2Q` |
| 2q 十五参 | — | `UU15` |
| 3q 无参 | `TOFFOLI CSWAP` | — |
| 特殊 | `BARRIER` | — |

`QRAM`（Quantum RAM）也是 ext 专属，但它不是普通门——见下文 [QRAM 节](originir-ext-qram)。

---

## 扩展语法

### dagger 后缀

任意门可加 `dagger` 后缀取共轭转置：

```text
<GATE> q[<i>] dagger
<GATE> q[<i>], (<params>) dagger
```

- 自伴门（`H`、`X`、`Y`、`Z`、`CNOT`、`CZ`、`SWAP`、`TOFFOLI`、`CSWAP` 等）的 `dagger` 不改变效果
- 旋转门的 `dagger` 相当于角度取负
- `S dagger` 等价于 `Sdg`

### controlled_by 子句

内联指定控制比特，等价于 `CONTROL` 块：

```text
<GATE> q[<target>] controlled_by (q[<c1>], q[<c2>], ...)
<GATE> q[<target>], (<params>) [dagger] controlled_by (q[<c1>], ...)
```

`dagger` 与 `controlled_by` 可组合，顺序为 `dagger` 在前。控制比特必须与目标比特不相交。

### 与块语法的等价关系

```text
X q[2] dagger controlled_by (q[0], q[1])
```

等价于：

```text
CONTROL q[0], q[1]
  DAGGER
    X q[2]
  ENDDAGGER
ENDCONTROL q[0], q[1]
```

> 提交官方 OriginIR 时，inline 语法会经 `opcode_to_line_originir_official()` 自动转换为块语法。

---

## 控制块

### CONTROL / ENDCONTROL

```text
CONTROL q[<c1>], q[<c2>], ...
  <gate_operations>
ENDCONTROL q[<c1>], q[<c2>], ...
```

- `CONTROL` 与 `ENDCONTROL` 必须成对，且控制列表一致
- 块内不能包含 `MEASURE`
- 控制比特不能与目标比特重复

### DAGGER / ENDDAGGER

```text
DAGGER
  <gate_operations>
ENDDAGGER
```

- 块内门序列被逆序执行，每个门取 dagger
- DAGGER 块可嵌套；奇数层取 dagger，偶数层恢复
- 块内不能包含 `MEASURE`

### 嵌套

`CONTROL` 与 `DAGGER` 可相互嵌套，组合出复杂受控-共轭结构。

---

## DEF 块（子程序）

DEF 块定义可复用子程序，仅 OriginIR-ext 支持。形参签名复用 [named register 语法](#qinit)：第一组括号是 `name[size]` 形式的量子寄存器声明，可选的第二组括号是标量参数名列表。

```text
DEF <name>(<reg1>[<s1>], <reg2>[<s2>], ...) [(<p1>, <p2>, ...)]
  <gate_operations>
ENDDEF
```

**约束：**

- 仅支持**标量**形参；数组形参不可调用
- 形参寄存器名作用域限于 DEF 内；调用时被替换为实参物理索引

**调用：** 按位置为每个形参量子比特提供实参（实参总数 = 所有形参寄存器尺寸之和），或直接传入整个 named register；标量实参写在末尾括号中。

```text
DEF bell_pair(q[2])
  H q[0]
  CNOT q[0], q[1]
ENDDEF

DEF rx_gate(q[1]) (theta)
  RX q[0], (theta)
ENDDEF

QINIT 4
CREG 0

bell_pair(q[0], q[1])          # 位置式
bell_pair(q[2], q[3])
rx_gate(q[0]) (1.57)           # 末尾括号传标量
```

**内联展开。** DEF 调用在解析时被就地展开到扁平 opcode 序列（形参→实参物理索引重映射 + 标量参数替换）。因此 `circuit.originir` 输出**不保留** DEF 块——round-trip 是**语义等价**而非文本等价。

DEF 块与 Python 侧的 {func}`uniqc.circuit_builder.named_circuit.circuit_def` 装饰器一一对应；用 `NamedCircuit.to_originir_def()` 可导出 DEF 文本，详见 [构建量子线路](circuit.md)。

---

## 测量与复位

### MEASURE

```text
MEASURE q[<i>], c[<j>]
```

把 qubit `<i>` 的测量结果写入经典比特 `<j>`。

- `<i>` 必须在 QINIT 声明范围内，`<j>` 必须在 CREG 范围内
- `MEASURE` 不能出现在 `CONTROL` / `DAGGER` 块内
- 同一条 `MEASURE q[i], c[j]` 既可用作**末端测量**，也可用作 **mid-circuit 测量**——后者配合下面的动态电路扩展使用

### RESET

```text
RESET q[<i>]
```

把 qubit `<i>` 复位到 $|0\rangle$。仅在**动态电路扩展**语境下有意义（mid-circuit 复位），属于 OriginIR-ext 专属、仅本地模拟的特性。详见 [动态电路扩展](#动态电路扩展originir-ext-only)。

---

(originir-ext-dynamic)=
## 动态电路扩展（OriginIR-ext only）

OriginIR-ext 在 `MEASURE` / `RESET` 之上还提供一套**经典 / 控制流指令**，用于表达动态电路：mid-circuit 测量后用经典逻辑对后续量子操作做实时判断（feed-forward）。

| 语句 | 形式 | 语义 |
|------|------|------|
| 与 / 或 / 异或 | `AND/OR/XOR c[d], A, B` | `c[d] = A ⊙ B` |
| 取反 / 传送 | `NOT c[d], A` · `MOV c[d], A` | `c[d] = ~A` · `c[d] = A` |
| 条件 | `QIF <cond> ... [QELSE ...] ENDQIF` | `cond` 真则执行第一段，否则执行 QELSE |
| 循环 | `QWHILE <cond> ... ENDQWHILE` | `cond` 真则反复执行 |

操作数 `A`、`B` 是 `c[k]` 或立即数 `0` / `1`；`<cond>` 是对 CREG 比特的布尔表达式（`not`/`~`、`and`/`&`、`xor`/`^`、`or`/`|`，可加括号）。

**这是 OriginIR-ext 专属、仅本地模拟的特性**——不能导出为 OpenQASM 或官方 OriginIR，也不能提交云平台（相关导出/提交抛 `CircuitTranslationError`）。

完整语法、CREG 模型、Circuit API、运行细节（含 `QWHILE` 看门狗）见 [动态电路：mid-circuit measurement 与经典控制流](../2_advanced/dynamic_circuits.md)。

---

(originir-ext-qram)=
## QRAM（量子随机存取存储器）

QRAM 是 OriginIR-ext 的**本地模拟扩展**。一条 QRAM 指令把一个只读的经典查找表以可逆 XOR 的方式作用到量子数据寄存器；地址寄存器可以处于叠加态，因此该操作会在每个计算基分量上相干地查询对应条目。QRAM 表的内容不写入 OriginIR-ext 文本，由调用方在执行前通过模拟器 API 装载。

> QRAM 不是官方 OriginIR 指令，也没有 OpenQASM 2.0 等价表示。包含 `QRAMDECL` 的线路只能保留为 OriginIR-ext 并在受支持的本地模拟器中运行；导出官方 OriginIR、导出 QASM、进入 QASM 编译管线或提交云平台都会失败，而不是静默丢弃 QRAM 操作。

### 规范记号

以下规则使用：

- $A$：地址位宽，即 `addr_size`
- $D$：数据位宽，即 `data_size`
- $T$：含 $2^A$ 个条目的经典查找表，且 $0 \le T[a] < 2^D$
- $a_i$、$d_j$、$c_k$：分别为地址、数据和可选控制量子比特

### 声明：`QRAMDECL`

规范写法把所有 QRAM 声明放在 `QINIT` 之前：

```text
QRAMDECL <name> <addr_size>,<data_size>
```

声明必须满足：

- `<name>` 匹配 `[A-Za-z_][A-Za-z0-9_]*`，区分大小写，并且不能与 OriginIR/OriginIR-ext 关键字、门名或同一程序内的其他 QRAM 重名
- `<addr_size>` 和 `<data_size>` 都是正整数；当前本地实现还要求两者之和不超过 30
- 一条声明创建 $2^A$ 个条目，每个条目是 $D$ 位无符号整数，合法范围为 $[0, 2^D-1]$
- 声明只定义名称和形状，不包含表数据；新建的运行时表默认全部为 0
- 调用必须位于对应声明之后。`Circuit.originir` 会把所有声明规范化输出到 `QINIT` 之前

例如，`QRAMDECL lookup 2,3` 声明 4 个条目，每个条目可存储 0 到 7。

### 调用与寄存器位序

无控制调用的语法是：

```text
<name> q[<a_0>], ..., q[<a_(A-1)>], q[<d_0>], ..., q[<d_(D-1)>]
```

调用列表的前 $A$ 个引用构成地址寄存器，后 $D$ 个引用构成数据寄存器。**列表顺序决定有效位，不要求量子比特编号连续**：

$$
a = \sum_{i=0}^{A-1} \operatorname{bit}(q[a_i])2^i,
\qquad
x = \sum_{j=0}^{D-1} \operatorname{bit}(q[d_j])2^j.
$$

也就是说，列表中的第一个地址量子比特和第一个数据量子比特都是各自寄存器的最低有效位（LSB）。例如：

```text
QRAMDECL lookup 2,3
QINIT 5
CREG 0

lookup q[0], q[1], q[2], q[3], q[4]
```

这里地址列表中的 `q[0]`、`q[1]` 依次对应 $2^0$、$2^1$ 位；数据列表中的 `q[2]`、`q[3]`、`q[4]` 依次对应 $2^0$、$2^1$、$2^2$ 位。

每次调用必须满足以下静态约束：

- 目标量子比特恰好有 $A+D$ 个，且每个索引均落在 `QINIT` 声明范围内
- 地址列表和数据列表内部都不能重复，两组列表也必须互不相交
- 控制量子比特不能重复，必须在 `QINIT` 范围内，并与地址/数据量子比特互不相交
- QRAM 调用没有数值参数，也不会修改地址寄存器或经典查找表

### 幺正语义与自逆性

对计算基态，QRAM 调用定义为：

$$
U_T\lvert a\rangle_A\lvert x\rangle_D
= \lvert a\rangle_A\lvert x \mathbin{\operatorname{xor}} T[a]\rangle_D.
$$

该映射按线性方式作用于地址叠加态。它是一个置换幺正操作，并满足 $U_T^\dagger=U_T$ 与 $U_T^2=I$，所以连续调用两次会恢复原态。`dagger` 后缀可以写出，但对单条 QRAM 调用不改变执行结果：

```text
lookup q[0], q[1], q[2], q[3], q[4] dagger
```

### 受控 QRAM

QRAM 支持 OriginIR-ext 的内联 `controlled_by` 子句：

```text
<name> q[<a_0>], ..., q[<d_(D-1)>] controlled_by (q[<c_0>], ..., q[<c_(K-1)>])
```

仅当所有控制位都为 $\lvert1\rangle$ 时执行 XOR 查询；其他分量保持不变：

$$
\lvert c\rangle_C\lvert a\rangle_A\lvert x\rangle_D
\longmapsto
\begin{cases}
\lvert c\rangle_C\lvert a\rangle_A\lvert x \mathbin{\operatorname{xor}} T[a]\rangle_D,
& c=2^K-1,\\
\lvert c\rangle_C\lvert a\rangle_A\lvert x\rangle_D,
& \text{otherwise}.
\end{cases}
$$

QRAM 文本的规范编码使用内联 `controlled_by`。在 Python API 中，`Circuit.control()` 上下文可以与 `qram_call(..., control_qubits=...)` 组合；序列化时两者会合并成同一个内联控制列表。所有控制量子比特仍须互不重复且不与地址/数据寄存器重叠。

```text
QRAMDECL lookup 2,3
QINIT 6
CREG 3

H q[0]
H q[1]
X q[5]
lookup q[0], q[1], q[2], q[3], q[4] controlled_by (q[5])
MEASURE q[2], c[0]
MEASURE q[3], c[1]
MEASURE q[4], c[2]
```

### Python API 与运行时数据

`Circuit.qram_declare()` 对应 `QRAMDECL`，`Circuit.qram_call()` 对应调用语句。要执行非零查找表，先预处理线路以注册 QRAM，再通过 `sim.qram_objects` 写入数据：

```python
from uniqc import Circuit
from uniqc.simulator import Simulator

circuit = Circuit(6)
circuit.qram_declare("lookup", addr_size=2, data_size=3)
circuit.h(0)
circuit.h(1)
circuit.x(5)
circuit.qram_call("lookup", 0, 1, 2, 3, 4, control_qubits=5)
circuit.measure(2, 3, 4)

sim = Simulator(least_qubit_remapping=False)
sim.simulate_preprocess(circuit)

qram = sim.qram_objects["lookup"]
qram.write(0, 1)
qram.write(1, 5)
qram.write(2, 7)
qram.write(3, 2)

statevector = sim.simulate_statevector(circuit)
```

运行时对象提供以下数据操作：

| API | 约束 | 效果 |
|-----|------|------|
| `qram.write(addr, value)` | $0 \le addr < 2^A$，$0 \le value < 2^D$ | 写入一个条目 |
| `qram.read(addr)` | $0 \le addr < 2^A$ | 读取一个条目 |
| `qram.reset(value=0)` | $0 \le value < 2^D$ | 用同一值重置全部条目 |

OriginIR-ext 目前没有写表指令，因此线路执行期间 QRAM 表是只读的。多次使用同一 `<name>` 的调用共享同一个运行时表。

### 解析、导出与执行边界

| 操作 | 包含 QRAM 时的行为 |
|------|-------------------|
| `Circuit.from_originir()` / `from_originir_ext()` | 支持解析声明、调用、`dagger` 和控制子句 |
| `circuit.originir` / `to_extended_originir()` | 支持并保留 QRAM，声明规范化到 `QINIT` 之前 |
| 本地 statevector / density-matrix 模拟 | 支持 QRAM XOR 查询与受控 QRAM |
| `circuit.originir_official` / `convert_originir_ext_to_originir()` | 不支持，抛出 `CircuitTranslationError` |
| `circuit.qasm`、QASM 编译管线和云平台提交 | 不支持，抛出转换或编译错误 |

---

## 错误通道（噪声模拟）

OriginIR-ext 支持以下错误通道。除 `Kraus1Q` 外，所有通道都可从 OriginIR-ext 文本直接解析（解析器把它们当作对应参数数的门处理）。

### 单量子比特错误通道

| 通道 | 参数数 | 描述 |
|------|--------|------|
| `Depolarizing` | 1 | 去极化噪声，概率 $p$ |
| `BitFlip` | 1 | 比特翻转，概率 $p$ |
| `PhaseFlip` | 1 | 相位翻转，概率 $p$ |
| `AmplitudeDamping` | 1 | 振幅阻尼，阻尼率 $\gamma$ |
| `PauliError1Q` | 3 | $(p_x, p_y, p_z)$ X/Y/Z 错误概率 |
| `Kraus1Q` | 变长 | 单比特 Kraus 算符序列，**不能从文本解析**——见下方说明 |

语法示例：

```text
Depolarizing q[0], (0.01)
PauliError1Q q[1], (0.01, 0.01, 0.01)
```

### 双量子比特错误通道

| 通道 | 参数数 | 描述 |
|------|--------|------|
| `TwoQubitDepolarizing` | 1 | 双比特去极化，概率 $p$ |
| `PauliError2Q` | 15 | 双比特 Pauli 错误（15 个非平凡 Pauli 概率） |

语法示例：

```text
TwoQubitDepolarizing q[0], q[1], (0.01)
PauliError2Q q[0], q[1], (p1, p2, ..., p15)
```

```{note}
`Kraus1Q` 在 spec 中以 `param: -1` 作为 sentinel，表示"参数是一组结构化的 2×2 复矩阵"。**它不在 line parser 的指令分派链里**，不能从 OriginIR-ext 文本解析；只能通过 {class}`uniqc.simulator.error_model.Kraus1Q` 等 `ErrorModel` API 构造，再由模拟器在执行期合并到 opcode 流。其他 7 个通道可以文本写出。
```

---

## 完整示例

### 基础电路

```text
QINIT 5
CREG 2

H q[0]
RX q[1], (1.57)
CNOT q[0], q[1]
RY q[2], (0.785)
CZ q[1], q[2]
U3 q[3], (1.57, 0.785, 0.392)
TOFFOLI q[0], q[1], q[3]
BARRIER q[0], q[1], q[2], q[3]

MEASURE q[0], c[0]
MEASURE q[1], c[1]
```

### DEF 与命名寄存器

```text
QINIT data[2], anc[2]
CREG 2

DEF bell(x[2])
  H x[0]
  CNOT x[0], x[1]
ENDDEF

DEF rx_rot(q[1]) (angle)
  RX q[0], (angle)
ENDDEF

bell(data)                   # 等价于 bell(data[0], data[1])
bell(anc)
rx_rot(data[0]) (1.57)

MEASURE data[0], c[0]
MEASURE data[1], c[1]
```

> 序列化输出会把命名寄存器扫平、把 DEF 调用内联展开。`circuit.originir` 给出的是展开后的扁平 `QINIT 4` + 物理 `q[i]` 序列，不保留上面的名字与 DEF 块。

### 含噪声的 Bell 对

```text
QINIT 3
CREG 3

DEF noisy_bell(q[2])
  H q[0]
  CNOT q[0], q[1]
  Depolarizing q[0], (0.01)
  Depolarizing q[1], (0.01)
  TwoQubitDepolarizing q[0], q[1], (0.005)
ENDDEF

noisy_bell(q[0], q[1])
noisy_bell(q[1], q[2])

MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
```

---

## Python API 速查

语言 spec 与 Python API 是两回事。下面只给入口指针，详细用法见对应文档。

| 任务 | API |
|------|-----|
| 导出 OriginIR-ext 文本 | `Circuit.originir` / `Circuit.to_extended_originir()` |
| 从文本解析 | {meth}`uniqc.circuit_builder.Circuit.from_originir` / `from_originir_ext()` |
| 导出官方 OriginIR（已降级） | `Circuit.originir_official` / {func}`uniqc.compile.convert_originir_ext_to_originir` |
| 导出 OpenQASM 2.0 | `Circuit.qasm` |
| 构建线路（H、CNOT、RX…） | 见 [构建量子线路](circuit.md) |
| 命名电路 / `@circuit_def` / `NamedCircuit` | 见 [构建量子线路](circuit.md) |
| 符号参数 `Parameter` / `Parameters` | 见 [构建量子线路](circuit.md) |
| QRAM 运行时 API | 见上文 [QRAM 节](originir-ext-qram) |
| 动态电路（mid-circuit 测量、QIF/QWHILE…） | 见 [动态电路](../2_advanced/dynamic_circuits.md) |
| 用文本直接模拟 | 见 [本地模拟](simulation.md) |
| 提交到云平台 | 见 [提交任务](submit_task.md) |

---

## 解析、导出与执行边界总览

| 操作 | 普通线路 | DEF 块 | QRAM | 动态电路扩展 | 符号 PARAM |
|------|----------|--------|------|--------------|-----------|
| `from_originir` / `from_originir_ext` | ✓ | ✓（内联展开） | ✓ | ✓ | ✓ |
| `circuit.originir` / `to_extended_originir()` | ✓ | 扁平输出 | ✓（声明前置） | ✓ | ✓（未绑定符号原样输出） |
| 本地 statevector / density-matrix 模拟 | ✓ | ✓ | ✓ | ✓（仅 `OriginIR_ext_Simulator`） | 需先 `assign_parameters` |
| 本地 MPS / QuTiP / TorchQuantum 模拟 | ✓ | ✓ | ✗ | ✗ | 需先 `assign_parameters` |
| `circuit.originir_official` | ✓ | ✓ | ✗ | ✗ | 需先 `assign_parameters` |
| `circuit.qasm` / QASM 编译管线 | ✓ | ✓ | ✗ | ✗ | 需先 `assign_parameters` |
| 云平台提交 | ✓ | ✓ | ✗ | ✗ | 需先 `assign_parameters` |

✓ 表示支持；✗ 表示会抛出 `CircuitTranslationError` 或编译错误。

---

## 下一步

- [构建量子线路](circuit.md)——`Circuit` Python API、命名电路、参数化线路
- [OriginIR 官方规范](originir_official.md)——云服务接受的子集
- [语言关系说明](originir_relationship.md)——三种语言的转换路径
- [动态电路](../2_advanced/dynamic_circuits.md)——mid-circuit 测量与经典控制流
- [本地模拟](simulation.md)、[提交任务](submit_task.md)

## 相关测试

- `uniqc/test/core/test_originir_ext.py`——OriginIR-ext 解析与序列化 round-trip
- `uniqc/test/core/test_originir_ext_dynamic.py`——动态电路扩展语法
- `uniqc/test/core/test_classical_program.py`——经典指令与 QIF/QWHILE
- `uniqc/test/circuit_builder/test_circuit_builder_spec.py`——门集与参数数
- `uniqc/test/simulator/test_random_OriginIR.py`——随机 round-trip 回归
- `uniqc/test/simulator/test_gate_oracles.py`——扩展门数值正确性

详见 [测试覆盖说明](../2_advanced/testing.md)。
