# OriginIR-ext 规范

> **本文档描述的是 OriginIR-ext**——UnifiedQuantum 的默认本地量子线路描述语言。它是官方 OriginIR 的超集，额外支持 ECR/ISWAP/XX/YY/ZZ/XY/PHASE2Q/UU15/RPhi/RPhi90/RPhi180 等扩展门、named register（命名量子/经典寄存器）、DEF/ENDDEF 子程序、QRAM、error channels 以及 inline dagger/controlled_by 语法。
>
> 官方 OriginIR（本源量子云服务接受的子集）规范见 [OriginIR 官方规范](originir_official.md)。
> 三种语言的完整关系说明见 [OriginIR、OriginIR-ext 与 OpenQASM 2.0 的关系](originir_relationship.md)。

## 什么时候进入本页

当你需要理解 `circuit.originir` 输出的文本格式，或者想知道 OriginIR-ext 在 {mod}`uniqc.compile.originir` 中扮演什么角色时，看本页。

## 本页解决的问题

- `circuit.originir` 输出的文本是什么格式、怎么读
- 想手写 OriginIR 文本再交给模拟器运行
- 需要理解向 OriginQ 平台提交任务时的线路格式
- 想查阅 OriginIR 支持的完整门列表与语法规则
- 想了解 named register、DEF 块、Named Circuit、参数化量子线路的完整规范
- 想确认 QRAM 的声明、位序、受控调用、运行时数据和格式兼容边界

> 如果你还不知道如何构建线路，请先阅读 [构建量子线路](circuit.md)。

## 什么是 OriginIR

OriginIR 是本源量子体系下的量子线路描述语言，源自 [pyqpanda3](https://github.com/OriginQ/pyqpanda-3)（[PyPI](https://pypi.org/project/pyqpanda3/)）/ OriginQ 生态。

在 UnifiedQuantum 中，线路的**内部表示**是 `Circuit` 对象及其 `opcode_list`（由 {class}`uniqc.circuit_builder.OpcodeType` 元组组成，定义在 `uniqc.circuit_builder.opcode` 模块中）。当你调用 `circuit.originir` 时，是把内部的 opcode 序列序列化为 OriginIR-ext 文本——它是一种**导出与交换格式**，而非内部存储格式。提交 OriginQ 平台前，可转换的扩展会被降级为官方 OriginIR；QRAM 等不可转换扩展则会被明确拒绝。

> **内部表示 vs 导出格式**：`Circuit` 对象在内存中以 `opcode_list: list[OpcodeType]` 存储门操作序列。`.originir` 和 `.qasm` 是将 opcode 序列序列化为文本的属性。模拟器在底层也直接消费 opcode，不需要先序列化为 OriginIR 再解析。

如果你需要跨平台交互（例如提交到 IBM），则需要导出为 OpenQASM 2.0 格式，详见 [QASM](qasm.md)。

## 在 UnifiedQuantum 中使用 OriginIR

### 从 Circuit 导出

构建完线路后，直接获取 OriginIR 文本（触发序列化，不是读取存储的文本）：

```python
from uniqc import Circuit

circuit = Circuit()
circuit.h(0)
circuit.cnot(0, 1)
circuit.measure(0, 1)

originir_str = circuit.originir
print(originir_str)
```

> 关于线路构建的完整 API，见 [构建量子线路](circuit.md)。

### 用 OriginIR 文本直接模拟

你可以将 OriginIR 文本直接传给模拟器，无需先构建 Circuit 对象：

```python
from uniqc.simulator import Simulator

sim = Simulator()
prob = sim.simulate_pmeasure(originir_str)
```

> 关于模拟器的完整用法，见 [本地模拟](simulation.md)。

### 作为 OriginQ 平台提交格式

提交到 OriginQ 平台时，直接使用 `Circuit` 对象：

```python
from uniqc import submit_task

task_id = submit_task(
    circuit=circuit,
    backend='originq:WK_C180',
    shots=1000
)
```

> 关于任务提交的完整流程，见 [提交任务](submit_task.md)。

---

## OriginIR-ext 语言规范

> 以下是 OriginIR-ext 的完整语言规范。日常使用中，你通常不需要手写 OriginIR-ext——通过 `Circuit` API 构建线路后调用 `.originir` 即可自动生成。本节供需要直接读写文本或排查格式问题的用户参考。

### 程序结构

一个完整的 OriginIR 程序由以下部分组成：

```
[QRAMDECL 声明...]        # 可选（OriginIR-ext）：声明 QRAM，规范输出位于 QINIT 之前
QINIT <n_qubits>          # 必需：声明量子比特数
CREG <n_cbits>            # 必需：声明经典比特数

[DEF 块定义...]           # 可选：子程序定义

[量子门操作...]           # 主程序体

[MEASURE 语句...]         # 测量语句
```

### QINIT 语句

声明量子比特寄存器。除可选的 `QRAMDECL` 等 OriginIR-ext 声明外，它必须是程序的第一条核心语句。

OriginIR-ext 支持 **named register（命名寄存器）**。QINIT 有两种等价的写法：

**语法：**
```
QINIT <n_qubits>              # 裸整数形式（向后兼容）
QINIT <name>[<size>]          # 命名寄存器形式
QINIT <n1>[<s1>], <n2>[<s2>]  # 单行声明多个命名寄存器
```

- 裸整数形式 `QINIT 6` **等价于** `QINIT q[6]`（默认寄存器名为 `q`）。
- 可以声明多个命名寄存器，既可以写成**多行**，也可以写成**单行逗号分隔**。
- 所有寄存器会按声明顺序被扫平（flatten）到**同一个物理索引空间**。例如
  `QINIT q[6]` 后接 `QINIT q1[6]` 等价于 `QINIT 12`，其中 `q` 占物理比特
  0–5，`q1` 占物理比特 6–11。

**参数：**
- `<n_qubits>`：非负整数，表示量子比特总数
- `<name>`：寄存器名，由字母、数字、下划线组成，且以字母或下划线开头
- `<size>`：该寄存器的量子比特数量

**示例：**
```
QINIT 5                  # 等价于 QINIT q[5]
QINIT q[6]
QINIT q1[6]              # 追加一个寄存器，物理索引接续（6–11）
QINIT data[4], anc[2]    # 单行声明两个寄存器
```

> **导出始终扫平**：命名寄存器只存在于源文本与构建期。解析后所有引用会被立即映射为
> 物理索引；`circuit.originir` / `to_extended_originir()` 始终输出单一
> `QINIT <total>` 头部与物理 `q[i]` 操作数，**不保留**寄存器名。

### CREG 语句

声明经典比特寄存器，用于存储测量结果，必须在 QINIT 之后。CREG 与 QINIT 对称，同样支持 named register。

**语法：**
```
CREG <n_cbits>                # 裸整数形式（向后兼容）
CREG <name>[<size>]           # 命名寄存器形式
CREG <n1>[<s1>], <n2>[<s2>]   # 单行声明多个命名寄存器
```

- 裸整数形式 `CREG 6` **等价于** `CREG c[6]`（默认寄存器名为 `c`）。
- 多个经典寄存器同样会被扫平到同一个经典索引空间。
- 量子寄存器与经典寄存器的名字空间相互独立，但同一个名字不能同时用于量子和经典寄存器。

**参数：**
- `<n_cbits>`：非负整数，表示经典比特总数
- `<name>` / `<size>`：寄存器名与大小

**示例：**
```
CREG 2                   # 等价于 CREG c[2]
CREG c[3]
CREG c1[4]               # 追加经典寄存器
```

---

## 量子门操作

OriginIR 支持多种量子逻辑门，根据门的操作对象（量子比特数）和参数数量分类。

### 量子比特引用语法

量子门操作使用 `<register>[<index>]` 格式引用量子比特。默认物理寄存器名为 `q`：

```
q[0]      # 第 0 号（物理）量子比特
q[1]      # 第 1 号（物理）量子比特
```

若声明了 named register，也可以用寄存器名限定引用，它会在解析时被映射到物理索引：

```
QINIT data[4], anc[2]
H data[0]        # -> 物理 q[0]
X anc[1]         # -> 物理 q[5]
```

经典比特引用同理使用 `c[<index>]` 或 `<creg_name>[<index>]`。

多量子比特门使用逗号分隔：

```
CNOT q[0], q[1]
TOFFOLI q[0], q[1], q[2]
```

### 参数语法

带参数的门使用圆括号包裹参数值：

```
RX q[0], (1.57)           # 单参数
U2 q[0], (1.57, 0.785)    # 双参数
U3 q[0], (1.57, 0.785, 0.392)  # 三参数
```

参数值支持：
- 整数：`0`, `1`, `-1`
- 浮点数：`0.5`, `1.57`, `-0.785`
- 科学计数法：`1.5e-3`, `2.0e+5`

### 单量子比特门

#### 无参数单量子比特门

| 门名称 | 描述 | 矩阵表示 |
|--------|------|----------|
| `H` | Hadamard 门 | $\frac{1}{\sqrt{2}}\begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}$ |
| `X` | Pauli-X 门（NOT 门） | $\begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$ |
| `Y` | Pauli-Y 门 | $\begin{pmatrix} 0 & -i \\ i & 0 \end{pmatrix}$ |
| `Z` | Pauli-Z 门 | $\begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$ |
| `S` | S 门（相位门） | $\begin{pmatrix} 1 & 0 \\ 0 & i \end{pmatrix}$ |
| `SX` | Sqrt(X) 门 | $\frac{1}{2}\begin{pmatrix} 1+i & 1-i \\ 1-i & 1+i \end{pmatrix}$ |
| `T` | T 门（π/8 门） | $\begin{pmatrix} 1 & 0 \\ 0 & e^{i\pi/4} \end{pmatrix}$ |
| `I` | 恒等门 | $\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$ |

**语法：**
```
<GATE_NAME> q[<qubit_index>]
```

**示例：**
```text
H q[0]
X q[1]
Y q[2]
Z q[3]
S q[0]
SX q[1]
T q[2]
I q[3]
```

#### 单参数单量子比特门

| 门名称 | 描述 | 矩阵表示 |
|--------|------|----------|
| `RX` | 绕 X 轴旋转 | $e^{-i\theta X/2} = \begin{pmatrix} \cos\frac{\theta}{2} & -i\sin\frac{\theta}{2} \\ -i\sin\frac{\theta}{2} & \cos\frac{\theta}{2} \end{pmatrix}$ |
| `RY` | 绕 Y 轴旋转 | $e^{-i\theta Y/2} = \begin{pmatrix} \cos\frac{\theta}{2} & -\sin\frac{\theta}{2} \\ \sin\frac{\theta}{2} & \cos\frac{\theta}{2} \end{pmatrix}$ |
| `RZ` | 绕 Z 轴旋转 | $e^{-i\theta Z/2} = \begin{pmatrix} e^{-i\theta/2} & 0 \\ 0 & e^{i\theta/2} \end{pmatrix}$ |
| `U1` | 相位旋转门 | $\begin{pmatrix} 1 & 0 \\ 0 & e^{i\lambda} \end{pmatrix}$ |
| `RPhi90` | 带相位的 90° 旋转 | 特定参数旋转 |
| `RPhi180` | 带相位的 180° 旋转 | 特定参数旋转 |

**语法：**
```
<GATE_NAME> q[<qubit_index>], (<parameter>)
```

**示例：**
```text
RX q[0], (1.57)
RY q[1], (0.785)
RZ q[2], (0.5)
U1 q[3], (3.14)
RPhi90 q[0], (0.5)
RPhi180 q[1], (1.0)
```

#### 双参数单量子比特门

| 门名称 | 描述 | 参数 |
|--------|------|------|
| `RPhi` | 带相位的任意角度旋转 | $(\phi, \theta)$ |
| `U2` | 单量子比特旋转门 | $(\phi, \lambda)$ |

**语法：**
```
<GATE_NAME> q[<qubit_index>], (<param1>, <param2>)
```

**示例：**
```text
RPhi q[0], (0.5, 1.57)
U2 q[1], (0.785, 1.57)
```

#### 三参数单量子比特门

| 门名称 | 描述 | 矩阵表示 |
|--------|------|----------|
| `U3` | 通用单量子比特门 | $U3(\theta, \phi, \lambda) = \begin{pmatrix} \cos\frac{\theta}{2} & -e^{i\lambda}\sin\frac{\theta}{2} \\ e^{i\phi}\sin\frac{\theta}{2} & e^{i(\phi+\lambda)}\cos\frac{\theta}{2} \end{pmatrix}$ |

**语法：**
```
U3 q[<qubit_index>], (<theta>, <phi>, <lambda>)
```

**示例：**
```text
U3 q[0], (1.57, 0.785, 0.392)
```

### 双量子比特门

#### 无参数双量子比特门

| 门名称 | 描述 | 矩阵表示 |
|--------|------|----------|
| `CNOT` | 受控非门（CX） | $\begin{pmatrix} 1&0&0&0 \\ 0&1&0&0 \\ 0&0&0&1 \\ 0&0&1&0 \end{pmatrix}$ |
| `CZ` | 受控 Z 门 | $\begin{pmatrix} 1&0&0&0 \\ 0&1&0&0 \\ 0&0&1&0 \\ 0&0&0&-1 \end{pmatrix}$ |
| `ISWAP` | 交换门变体 | $\begin{pmatrix} 1&0&0&0 \\ 0&0&i&0 \\ 0&i&0&0 \\ 0&0&0&1 \end{pmatrix}$ |
| `ECR` | 弹性 Cross-Resonance 门 | $\frac{1}{\sqrt{2}}\begin{pmatrix} 0&1&0&-i \\ 1&0&-i&0 \\ 0&-i&0&1 \\ -i&0&1&0 \end{pmatrix}$ |

**语法：**
```
<GATE_NAME> q[<control>], q[<target>]
```

**示例：**
```text
CNOT q[0], q[1]
CZ q[1], q[2]
ISWAP q[0], q[1]
ECR q[0], q[1]
```

#### 单参数双量子比特门

| 门名称 | 描述 |
|--------|------|
| `XX` | XX 交互门 |
| `YY` | YY 交互门 |
| `ZZ` | ZZ 交互门 |
| `XY` | XY 交互门 |

**语法：**
```
<GATE_NAME> q[<qubit1>], q[<qubit2>], (<parameter>)
```

**示例：**
```text
XX q[0], q[1], (0.5)
YY q[0], q[1], (0.5)
ZZ q[0], q[1], (0.5)
XY q[0], q[1], (0.5)
```

#### 三参数双量子比特门

| 门名称 | 描述 |
|--------|------|
| `PHASE2Q` | 双量子比特相位门 |

**语法：**
```
PHASE2Q q[<qubit1>], q[<qubit2>], (<param1>, <param2>, <param3>)
```

**示例：**
```text
PHASE2Q q[0], q[1], (0.5, 1.0, 1.5)
```

#### 十五参数双量子比特门

| 门名称 | 描述 |
|--------|------|
| `UU15` | 通用双量子比特门 |

**语法：**
```
UU15 q[<qubit1>], q[<qubit2>], (<p1>, <p2>, ..., <p15>)
```

**示例：**
```text
UU15 q[0], q[1], (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
```

### 三量子比特门

#### 无参数三量子比特门

| 门名称 | 描述 | 功能 |
|--------|------|------|
| `TOFFOLI` | Toffoli 门（CCX） | 两个控制比特的受控非门 |
| `CSWAP` | 受控交换门（Fredkin 门） | 一个控制比特的交换门 |

**语法：**
```
<GATE_NAME> q[<qubit1>], q[<qubit2>], q[<qubit3>]
```

**示例：**
```text
TOFFOLI q[0], q[1], q[2]
CSWAP q[0], q[1], q[2]
```

(originir-ext-qram)=
### QRAM（量子随机存取存储器）

QRAM 是 OriginIR-ext 的**本地模拟扩展**。一条 QRAM 指令把一个只读的经典查找表以可逆 XOR 的方式作用到量子数据寄存器；地址寄存器可以处于叠加态，因此该操作会在每个计算基分量上相干地查询对应条目。QRAM 表的内容不写入 OriginIR-ext 文本，由调用方在执行前通过模拟器 API 装载。

> QRAM 不是官方 OriginIR 指令，也没有 OpenQASM 2.0 等价表示。包含 `QRAMDECL` 的线路只能保留为 OriginIR-ext 并在受支持的本地模拟器中运行；导出官方 OriginIR、导出 QASM、进入 QASM 编译管线或提交云平台都会失败，而不是静默丢弃 QRAM 操作。

#### 规范记号

以下规则使用：

- $A$：地址位宽，即 `addr_size`
- $D$：数据位宽，即 `data_size`
- $T$：含 $2^A$ 个条目的经典查找表，且 $0 \le T[a] < 2^D$
- $a_i$、$d_j$、$c_k$：分别为地址、数据和可选控制量子比特

#### 声明：`QRAMDECL`

规范写法把所有 QRAM 声明放在 `QINIT` 之前：

```text
QRAMDECL <name> <addr_size>,<data_size>
```

声明必须满足：

- `<name>` 匹配 `[A-Za-z_][A-Za-z0-9_]*`，区分大小写，并且不能与 OriginIR/OriginIR-ext 关键字、门名或同一程序内的其他 QRAM 重名。
- `<addr_size>` 和 `<data_size>` 都是正整数；当前本地实现还要求两者之和不超过 30。
- 一条声明创建 $2^A$ 个条目，每个条目是 $D$ 位无符号整数，合法范围为 $[0, 2^D-1]$。
- 声明只定义名称和形状，不包含表数据；新建的运行时表默认全部为 0。
- 调用必须位于对应声明之后。`Circuit.originir` 会把所有声明规范化输出到 `QINIT` 之前。

例如，`QRAMDECL lookup 2,3` 声明 4 个条目，每个条目可存储 0 到 7。

#### 调用与寄存器位序

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

- 目标量子比特恰好有 $A+D$ 个，且每个索引均落在 `QINIT` 声明范围内。
- 地址列表和数据列表内部都不能重复，两组列表也必须互不相交。
- 控制量子比特不能重复，必须在 `QINIT` 范围内，并与地址/数据量子比特互不相交。
- QRAM 调用没有数值参数，也不会修改地址寄存器或经典查找表。

#### 幺正语义与自逆性

对计算基态，QRAM 调用定义为：

$$
U_T\lvert a\rangle_A\lvert x\rangle_D
= \lvert a\rangle_A\lvert x \mathbin{\operatorname{xor}} T[a]\rangle_D.
$$

该映射按线性方式作用于地址叠加态。它是一个置换幺正操作，并满足 $U_T^\dagger=U_T$ 与 $U_T^2=I$，所以连续调用两次会恢复原态。`dagger` 后缀可以写出，但对单条 QRAM 调用不改变执行结果：

```text
lookup q[0], q[1], q[2], q[3], q[4] dagger
```

#### 受控 QRAM

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

#### Python API 与运行时数据

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

#### 解析、导出与执行边界

| 操作 | 包含 QRAM 时的行为 |
|------|-------------------|
| `Circuit.from_originir()` / `from_originir_ext()` | 支持解析声明、调用、`dagger` 和控制子句 |
| `circuit.originir` / `to_extended_originir()` | 支持并保留 QRAM，声明规范化到 `QINIT` 之前 |
| 本地 statevector / density-matrix 模拟 | 支持 QRAM XOR 查询与受控 QRAM |
| `circuit.originir_official` / `convert_originir_ext_to_originir()` | 不支持，抛出 `CircuitTranslationError` |
| `circuit.qasm`、QASM 编译管线和云平台提交 | 不支持，抛出转换或编译错误 |

### BARRIER

BARRIER 用于在量子比特之间插入屏障，防止编译器对屏障前后的操作进行重排或优化。

**语法：**
```
BARRIER q[<qubit1>], q[<qubit2>], ...
```

**示例：**
```text
BARRIER q[0], q[1], q[2]
BARRIER q[0], q[1], q[2], q[3], q[4]
```

---

## 扩展语法

OriginIR 支持两种扩展语法，用于更灵活地表达量子操作。

### dagger 后缀

对任意门操作，可以添加 `dagger` 后缀表示取共轭转置（Hermitian 伴随）。

**语法：**
```
<GATE_NAME> q[<qubit>] dagger
<GATE_NAME> q[<qubit>], (<params>) dagger
```

**示例：**
```text
H q[0] dagger
RX q[1], (1.57) dagger
U3 q[2], (1.57, 0.785, 0.392) dagger
CNOT q[0], q[1] dagger
```

**说明：**
- 对于自伴门（如 H、X、Y、Z），`dagger` 后缀等同于原门
- 对于旋转门，`dagger` 相当于角度取负
- 对于 S 门，`S dagger` 等价于 `S† = S†`

### controlled_by 子句

使用 `controlled_by` 子句可以内联指定控制量子比特，等价于 CONTROL 块的效果。

**语法：**
```
<GATE_NAME> q[<target>] controlled_by (q[<ctrl1>], q[<ctrl2>], ...)
<GATE_NAME> q[<target>], (<params>) controlled_by (q[<ctrl1>], q[<ctrl2>], ...)
```

**示例：**
```text
X q[2] controlled_by (q[0])
X q[3] controlled_by (q[0], q[1])
RX q[2], (1.57) dagger controlled_by (q[0], q[1])
```

**等价关系：**
```text
# controlled_by 写法
X q[2] controlled_by (q[0], q[1])

# 等价的 CONTROL 块写法
CONTROL q[0], q[1]
  X q[2]
ENDCONTROL q[0], q[1]
```

---

## 控制结构

### CONTROL / ENDCONTROL

CONTROL 块定义多控制量子比特门，块内的所有门操作都受指定控制比特控制。

**语法：**
```
CONTROL q[<ctrl1>], q[<ctrl2>], ...
  <gate_operations>
ENDCONTROL q[<ctrl1>], q[<ctrl2>], ...
```

**规则：**
- `CONTROL` 和 `ENDCONTROL` 必须成对出现
- 控制量子比特列表必须一致
- 块内不能包含 `MEASURE` 语句
- 控制量子比特不能与目标量子比特重复

**示例：**
```text
QINIT 4
CREG 1

CONTROL q[0], q[1]
  X q[2]
  Y q[3]
ENDCONTROL q[0], q[1]
```

### DAGGER / ENDDAGGER

DAGGER 块对其内部的门操作序列取共轭转置。块内的操作会被逆序执行，每个门取其 dagger。

**语法：**
```
DAGGER
  <gate_operations>
ENDDAGGER
```

**规则：**
- `DAGGER` 和 `ENDDAGGER` 必须成对出现
- DAGGER 块可以嵌套
- 块内不能包含 `MEASURE` 语句
- 嵌套时，奇数次嵌套会取 dagger，偶数次嵌套恢复原操作

**示例：**
```text
QINIT 3
CREG 1

DAGGER
  H q[0]
  CNOT q[0], q[1]
  RX q[2], (1.57)
ENDDAGGER
```

上述 DAGGER 块等价于：
```text
RX q[2], (1.57) dagger
CNOT q[0], q[1]
H q[0]
```

### 控制结构嵌套

CONTROL 和 DAGGER 可以相互嵌套：

```text
QINIT 4
CREG 1

CONTROL q[0]
  DAGGER
    H q[1]
    CNOT q[1], q[2]
  ENDDAGGER
ENDCONTROL q[0]
```

---

## MEASURE 语句

测量语句将量子比特的测量结果存储到经典比特。

**语法：**
```
MEASURE q[<qubit_index>], c[<cbit_index>]
```

**规则：**
- `<qubit_index>` 必须小于 QINIT 声明的量子比特数
- `<cbit_index>` 必须小于 CREG 声明的经典比特数
- MEASURE 不能出现在 CONTROL 或 DAGGER 块内

**示例：**
```text
QINIT 3
CREG 2

H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
```

---

## DEF 块（子程序定义）

DEF 块用于定义可复用的量子子程序，类似于函数定义。这在构建复杂电路时可以避免重复代码，提高可读性和可维护性。

### DEF 块语法

**基本语法：**
```
DEF <name>(<qubit_list>)
  <gate_operations>
ENDDEF
```

### DEF 块语法

DEF 的形参签名复用 **named register 声明语法**：括号内是一组 `name[size]` 寄存器声明；可选的第二个括号是一组**标量**参数名（只支持标量参数，不支持数组/向量参数）。

**基本语法：**
```
DEF <name>(<reg1>[<size1>], <reg2>[<size2>], ...)
  <gate_operations>
ENDDEF
```

**带参数的语法：**
```
DEF <name>(<reg1>[<size1>], ...) (<param1>, <param2>, ...)
  <gate_operations>
ENDDEF
```

**语法元素：**
- `<name>`：子程序名称，由字母、数字、下划线组成，必须以字母或下划线开头
- `<regN>[<sizeN>]`：形参量子寄存器声明，函数体内用 `regN[0]`、`regN[1]` 等引用
- `<paramK>`：可选的**标量**参数名，函数体内在参数位置引用（如 `RX q[0], (theta)`）
- `<gate_operations>`：量子门操作序列

### 无参数 DEF

定义一个 Bell 对制备子程序（形参寄存器 `q` 含 2 个量子比特）：

```text
DEF bell_pair(q[2])
  H q[0]
  CNOT q[0], q[1]
ENDDEF
```

### 带参数 DEF

定义带一个标量参数的旋转门：

```text
DEF rx_gate(q[1]) (theta)
  RX q[0], (theta)
ENDDEF
```

定义多参数门：

```text
DEF u3_gate(q[1]) (theta, phi, lambda)
  U3 q[0], (theta, phi, lambda)
ENDDEF
```

使用多个形参寄存器：

```text
DEF entangle(a[2], b[1]) (t1, t2)
  RX a[0], (t1)
  RY b[0], (t2)
  CNOT a[1], b[0]
ENDDEF
```

### 调用 DEF

在主程序中调用已定义的 DEF：调用时按声明顺序为形参寄存器的每个量子比特提供**位置式**实参，实参总数等于所有形参寄存器尺寸之和；也可以直接传入整个寄存器名。标量参数值写在末尾的括号中，个数须与形参一致。

```text
QINIT 4
CREG 2

DEF bell_pair(q[2])
  H q[0]
  CNOT q[0], q[1]
ENDDEF

DEF rx_gate(q[1]) (theta)
  RX q[0], (theta)
ENDDEF

// 调用子程序（位置式比特列表）
bell_pair(q[0], q[1])
bell_pair(q[2], q[3])
rx_gate(q[0]) (1.57)
```

也可以传入整个 named register：

```text
QINIT data[2], anc[2]
CREG 0

DEF bell(x[2])
  H x[0]
  CNOT x[0], x[1]
ENDDEF

bell(data)     // 等价于 bell(data[0], data[1])
bell(anc)
```

> **调用被内联展开**：DEF 调用在解析时会被就地展开到扁平线路中（形参→实参物理索引重映射 +
> 标量参数替换）。因此导出时 DEF 块不会保留，`circuit.originir` 输出的是展开后的扁平线路——
> round-trip 是**语义等价**而非文本等价。

### DEF 与 Python API 对应

DEF 块与 Python 中的 `@circuit_def` 装饰器完全对应：

**OriginIR 定义：**
```text
DEF bell_pair(q[2])
  H q[0]
  CNOT q[0], q[1]
ENDDEF
```

**Python 等价定义：**
```python
from uniqc import circuit_def

@circuit_def(name="bell_pair", qregs={"q": 2})
def bell_pair(circ, q):
    circ.h(q[0])
    circ.cnot(q[0], q[1])
    return circ
```

**带参数的对应：**

```text
DEF rx_gate(q[1]) (theta)
  RX q[0], (theta)
ENDDEF
```

```python
@circuit_def(name="rx_gate", qregs={"q": 1}, params=["theta"])
def rx_gate(circ, q, theta):
    circ.rx(q[0], theta)
    return circ
```

**导出 DEF 块：**

```python
# 从 NamedCircuit 导出 OriginIR DEF 格式
def_str = bell_pair.to_originir_def()
print(def_str)
# DEF bell_pair(q[2])
#   H q[0]
#   CNOT q[0], q[1]
# ENDDEF
```

---

## Named Circuit

Named Circuit 是 Python API 中定义可复用量子子程序的高级抽象，与 OriginIR 的 DEF 块一一对应。

### @circuit_def 装饰器

使用 `@circuit_def` 装饰器创建命名电路定义：

```python
from uniqc import circuit_def, Circuit

@circuit_def(name="bell_pair", qregs={"q": 2})
def bell_pair(circ, q):
    circ.h(q[0])
    circ.cnot(q[0], q[1])
    return circ
```

**装饰器参数：**
- `name`：电路定义名称
- `qregs`：量子寄存器规格
  - 字典形式：`{"q": 2}` 表示名为 "q" 的 2 量子比特寄存器
  - 列表形式：`["q", "r"]` 表示两个各 1 比特的寄存器
- `params`：参数名称列表（可选）

### NamedCircuit 属性

装饰器返回的 `NamedCircuit` 对象具有以下属性：

```python
bell_pair.name           # "bell_pair"
bell_pair.qregs          # {"q": 2}
bell_pair.params         # []
bell_pair.num_qubits     # 2
bell_pair.num_parameters # 0
```

### qreg 映射

将 Named Circuit 应用到父电路时，通过 `qreg_mapping` 指定量子比特映射：

```python
c = Circuit(qregs={"data": 4})
data = c.get_qreg("data")

# 将 bell_pair 的 q[0] 映射到 data[0]，q[1] 映射到 data[1]
bell_pair(c, qreg_mapping={"q": [data[0], data[1]]})

# 或使用整数索引
bell_pair(c, qreg_mapping={"q": [0, 1]})

# 或使用 QRegSlice
bell_pair(c, qreg_mapping={"q": data[0:2]})
```

### 参数绑定

带参数的 Named Circuit 通过 `param_values` 绑定参数值：

```python
@circuit_def(name="rx_gate", qregs={"q": 1}, params=["theta"])
def rx_gate(circ, q, theta):
    circ.rx(q[0], theta)
    return circ

c = Circuit(1)

# 字典形式绑定
rx_gate(c, qreg_mapping={"q": [0]}, param_values={"theta": 1.57})

# 列表形式绑定（按参数顺序）
rx_gate(c, qreg_mapping={"q": [0]}, param_values=[1.57])
```

### 多参数示例

```python
@circuit_def(name="rot", qregs={"q": 1}, params=["theta", "phi"])
def rot_circ(circ, q, theta, phi):
    circ.rx(q[0], theta)
    circ.ry(q[0], phi)
    return circ

c = Circuit(1)
rot_circ(c, qreg_mapping={"q": [0]}, param_values=[0.5, 1.0])
```

### 嵌套 Named Circuit

Named Circuit 可以调用其他 Named Circuit：

```python
@circuit_def(name="h_gate", qregs={"q": 1})
def h_gate(circ, q):
    circ.h(q[0])
    return circ

@circuit_def(name="h_on_two", qregs={"q": 2})
def h_on_two(circ, q):
    h_gate(circ, qreg_mapping={"q": [q[0]]})
    h_gate(circ, qreg_mapping={"q": [q[1]]})
    return circ

c = Circuit(2)
h_on_two(c, qreg_mapping={"q": [0, 1]})
```

### 构建独立电路

使用 `build_standalone()` 创建独立的 Circuit 对象：

```python
@circuit_def(name="bell_pair", qregs={"q": 2})
def bell_pair(circ, q):
    circ.h(q[0])
    circ.cnot(q[0], q[1])
    return circ

# 构建独立的 2 比特电路
c = bell_pair.build_standalone()
print(c.originir)
# QINIT 2
# CREG 0
# H q[0]
# CNOT q[0], q[1]
```

带参数的独立构建：

```python
@circuit_def(name="rot", qregs={"q": 1}, params=["theta"])
def rot_circ(circ, q, theta):
    circ.rx(q[0], theta)
    return circ

c = rot_circ.build_standalone(param_values={"theta": 0.5})
```

### 导出为 DEF 块

```python
@circuit_def(name="rx_gate", qregs={"q": 1}, params=["theta"])
def rx_gate(circ, q, theta):
    circ.rx(q[0], theta)
    return circ

print(rx_gate.to_originir_def())
# DEF rx_gate(q[1]) (theta)
#   RX q[0], (theta)
# ENDDEF
```

---

## 参数化量子线路

UnifiedQuantum 提供了符号参数系统，支持构建参数化量子线路，常用于变分量子算法（VQA）。

### Parameter 类

`Parameter` 是一个命名符号参数，支持绑定具体值和符号表达式运算。

```python
from uniqc import Parameter

theta = Parameter("theta")
phi = Parameter("phi")
```

#### 参数绑定

```python
theta = Parameter("theta")
theta.bind(1.57)           # 绑定具体值
value = theta.evaluate()   # 求值：1.57

# 检查是否已绑定
theta.is_bound  # True
```

#### 符号表达式

Parameter 支持算术运算，创建符号表达式：

```python
theta = Parameter("theta")
phi = Parameter("phi")

# 算术运算
expr1 = theta + 0.5
expr2 = theta * 2
expr3 = theta - phi
expr4 = theta / 2
expr5 = -theta

# 复合表达式
expr = theta * 2 + phi / 3
```

表达式使用 SymPy 底层实现，支持完整的符号计算能力。

#### 在电路中使用

```python
from uniqc import Circuit
from uniqc import Parameter

theta = Parameter("theta")
theta.bind(1.57)

c = Circuit(2)
c.h(0)
c.rx(0, theta.evaluate())  # 使用绑定值
c.cnot(0, 1)
```

### Parameters 类

`Parameters` 是参数数组，用于批量管理多个相关参数。

```python
from uniqc import Parameters

# 创建 4 个参数：theta_0, theta_1, theta_2, theta_3
angles = Parameters("theta", size=4)

# 访问单个参数
angles[0]  # Parameter('theta_0')
angles[1]  # Parameter('theta_1')

# 获取所有名称
angles.names  # ['theta_0', 'theta_1', 'theta_2', 'theta_3']
```

#### 批量绑定

```python
angles = Parameters("theta", size=4)
angles.bind([0.1, 0.2, 0.3, 0.4])

# 逐个求值
angles[0].evaluate()  # 0.1
angles[1].evaluate()  # 0.2
```

#### 在电路中使用

```python
from uniqc import Circuit
from uniqc import Parameters

angles = Parameters("theta", size=4)
angles.bind([0.1, 0.2, 0.3, 0.4])

c = Circuit(4)
for i in range(4):
    c.ry(i, angles[i].evaluate())
```

### 完整参数化示例

以下示例展示了参数化线路的完整工作流：

```python
import math
from uniqc import Circuit, circuit_def
from uniqc import Parameter, Parameters

# 定义参数化子程序
@circuit_def(name="ansatz_layer", qregs={"q": 4}, params=["theta"])
def ansatz_layer(circ, q, theta):
    for i in range(4):
        circ.ry(q[i], theta)
    for i in range(3):
        circ.cnot(q[i], q[i+1])
    return circ

# 创建主电路
c = Circuit(qregs={"q": 4})

# 使用参数数组
angles = Parameters("alpha", size=3)
angles.bind([0.1, 0.2, 0.3])

# 应用多层参数化子程序
for i in range(3):
    ansatz_layer(c, qreg_mapping={"q": [0, 1, 2, 3]}, param_values={"theta": angles[i].evaluate()})

# 测量
for i in range(4):
    c.measure(i)

print(c.originir)
```

---

## 错误通道（噪声模拟）

OriginIR 支持定义量子错误通道，用于模拟量子计算中的噪声和错误。

### 单量子比特错误通道

#### 单参数错误通道

| 通道名称 | 描述 | 参数 |
|----------|------|------|
| `Depolarizing` | 去极化噪声 | 概率 $p$ |
| `BitFlip` | 比特翻转噪声 | 翻转概率 $p$ |
| `PhaseFlip` | 相位翻转噪声 | 翻转概率 $p$ |
| `AmplitudeDamping` | 振幅阻尼噪声 | 阻尼率 $\gamma$ |

**语法：**
```
<CHANNEL_NAME> q[<qubit_index>], (<probability>)
```

**示例：**
```text
Depolarizing q[0], (0.01)
BitFlip q[1], (0.001)
PhaseFlip q[2], (0.001)
AmplitudeDamping q[3], (0.1)
```

#### 三参数错误通道

| 通道名称 | 描述 | 参数 |
|----------|------|------|
| `PauliError1Q` | 单量子比特 Pauli 错误 | $(p_x, p_y, p_z)$：X、Y、Z 错误概率 |

**语法：**
```
PauliError1Q q[<qubit_index>], (<px>, <py>, <pz>)
```

**示例：**
```text
PauliError1Q q[0], (0.01, 0.01, 0.01)
```

#### 变参数错误通道

| 通道名称 | 描述 |
|----------|------|
| `Kraus1Q` | 单量子比特 Kraus 算符表示 |

### 双量子比特错误通道

#### 单参数错误通道

| 通道名称 | 描述 | 参数 |
|----------|------|------|
| `TwoQubitDepolarizing` | 双量子比特去极化噪声 | 概率 $p$ |

**语法：**
```
TwoQubitDepolarizing q[<qubit1>], q[<qubit2>], (<probability>)
```

**示例：**
```text
TwoQubitDepolarizing q[0], q[1], (0.01)
```

#### 十五参数错误通道

| 通道名称 | 描述 |
|----------|------|
| `PauliError2Q` | 双量子比特 Pauli 错误 |

**语法：**
```
PauliError2Q q[<qubit1>], q[<qubit2>], (<p1>, <p2>, ..., <p15>)
```

### 噪声模拟示例

```text
QINIT 3
CREG 3

// 初始化
H q[0]
CNOT q[0], q[1]

// 应用噪声
Depolarizing q[0], (0.01)
BitFlip q[1], (0.001)
TwoQubitDepolarizing q[0], q[1], (0.005)

// 继续电路
CNOT q[1], q[2]
Depolarizing q[2], (0.01)

// 测量
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
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

### 带控制结构的电路

```text
QINIT 5
CREG 2

CONTROL q[0], q[1]
  X q[2]
  Y q[3]
ENDCONTROL q[0], q[1]

DAGGER
  H q[4]
  CNOT q[4], q[0]
ENDDAGGER

MEASURE q[0], c[0]
MEASURE q[1], c[1]
```

### 带 DEF 块的电路

```text
QINIT 6
CREG 4

// 定义 Bell 对制备子程序
DEF bell_pair(q[2])
  H q[0]
  CNOT q[0], q[1]
ENDDEF

// 定义参数化旋转
DEF rx_rot(q[1]) (angle)
  RX q[0], (angle)
ENDDEF

// 调用子程序
bell_pair(q[0], q[1])
bell_pair(q[2], q[3])
rx_rot(q[4]) (1.57)
rx_rot(q[5]) (0.785)

// 测量
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
MEASURE q[3], c[3]
```

### 参数化量子线路

```python
# Python 代码
from uniqc import Circuit, circuit_def
from uniqc import Parameters

@circuit_def(name="qaoa_layer", qregs={"q": 4}, params=["gamma", "beta"])
def qaoa_layer(circ, q, gamma, beta):
    # 问题哈密顿量（示例：全连接 ZZ）
    for i in range(4):
        for j in range(i+1, 4):
            circ.cnot(q[i], q[j])
            circ.rz(q[j], gamma)
            circ.cnot(q[i], q[j])
    # 混合哈密顿量
    for i in range(4):
        circ.rx(q[i], beta)
    return circ

# 创建电路
c = Circuit(qregs={"q": 4})

# 初始 Hadamard 层
for i in range(4):
    c.h(i)

# 参数数组
gammas = Parameters("gamma", size=2)
betas = Parameters("beta", size=2)
gammas.bind([0.5, 0.3])
betas.bind([0.4, 0.2])

# 应用 QAOA 层
for i in range(2):
    qaoa_layer(c, qreg_mapping={"q": [0, 1, 2, 3]},
               param_values=[gammas[i].evaluate(), betas[i].evaluate()])

# 测量
for i in range(4):
    c.measure(i)

print(c.originir)
```

### 噪声模拟电路

```text
QINIT 3
CREG 3

// 定义含噪声的 Bell 对
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

## Python API 参考

### 相关模块

- {mod}`uniqc.compile.originir` — OriginIR 解析器
  - {class}`uniqc.compile.originir.originir_line_parser.OriginIR_LineParser` — 行解析器
  - {class}`uniqc.compile.originir.originir_base_parser.OriginIR_BaseParser` — 完整程序解析器

- {mod}`uniqc.circuit_builder` — 电路构建
  - {class}`uniqc.circuit_builder.qcircuit.Circuit` — 电路类
  - {func}`uniqc.circuit_builder.named_circuit.circuit_def` — 命名电路装饰器
  - {class}`uniqc.circuit_builder.named_circuit.NamedCircuit` — 命名电路类
  - {class}`uniqc.circuit_builder.parameter.Parameter` — 符号参数
  - {class}`uniqc.circuit_builder.parameter.Parameters` — 参数数组

---

## 下一步

- 如果你还不知道如何构建线路，先阅读 [构建量子线路](circuit.md)
- 如果你想用 OriginIR 文本直接模拟，见 [本地模拟](simulation.md)
- 如果你想提交到 OriginQ 平台，见 [提交任务](submit_task.md)
- 如果你需要导出为 QASM 格式或做格式互转，见 [QASM](qasm.md)

## 相关测试

- `test_originir_parser.py`：OriginIR 解析器 round-trip 测试
- `test_originir_def.py`：DEF 块导出/导入测试
- `test_named_circuit.py`：Named Circuit 测试
- `test_parametric_circuits.py`：参数化线路集成测试
- `test_random_OriginIR.py`：随机回归 + QuTip 对比

详见 [测试覆盖说明](testing.md)。
