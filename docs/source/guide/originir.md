# OriginIR

## 什么时候进入本页

当你需要理解 `circuit.originir` 输出的文本格式，或者想知道 OriginIR 在 {mod}`uniqc.originir` 中扮演什么角色时，看本页。

## 本页解决的问题

- `circuit.originir` 输出的文本是什么格式、怎么读
- 想手写 OriginIR 文本再交给模拟器运行
- 需要理解向 OriginQ 平台提交任务时的线路格式
- 想查阅 OriginIR 支持的完整门列表与语法规则
- 想了解 DEF 块、Named Circuit、参数化量子线路的完整规范

> 如果你还不知道如何构建线路，请先阅读 [构建量子线路](circuit.md)。

## 什么是 OriginIR

OriginIR 是本源量子体系下的量子线路描述语言。在 UnifiedQuantum 中，它是线路的**首选内部表示格式**——当你调用 `circuit.originir` 时，输出的就是这种格式。OriginQ 平台的任务提交也使用该格式。

如果你需要跨平台交互（例如提交到 Quafu 或 IBM），则需要导出为 OpenQASM 2.0 格式，详见 [QASM](qasm.md)。

## 在 UnifiedQuantum 中使用 OriginIR

### 从 Circuit 导出

构建完线路后，直接获取 OriginIR 文本：

```python
from uniqc.circuit_builder import Circuit

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
from uniqc.simulator import OriginIR_Simulator

sim = OriginIR_Simulator()
prob = sim.simulate_pmeasure(originir_str)
```

> 关于模拟器的完整用法，见 [本地模拟](simulation.md)。

### 作为 OriginQ 平台提交格式

提交到 OriginQ 平台时，直接使用 `Circuit` 对象：

```python
from uniqc import submit_task

task_id = submit_task(
    circuit=circuit,
    backend='originq',
    shots=1000
)
```

> 关于任务提交的完整流程，见 [提交任务](submit_task.md)。

---

## OriginIR 语言规范

> 以下是 OriginIR 的完整语言规范。日常使用中，你通常不需要手写 OriginIR——通过 `Circuit` API 构建线路后调用 `.originir` 即可自动生成。本节供需要直接读写 OriginIR 文本或排查格式问题的用户参考。

### 程序结构

一个完整的 OriginIR 程序由以下部分组成：

```
QINIT <n_qubits>          # 必需：声明量子比特数
CREG <n_cbits>            # 必需：声明经典比特数

[DEF 块定义...]           # 可选：子程序定义

[量子门操作...]           # 主程序体

[MEASURE 语句...]         # 测量语句
```

### QINIT 语句

声明量子比特数量，必须是程序的第一条语句。

**语法：**
```
QINIT <n_qubits>
```

**参数：**
- `<n_qubits>`：非负整数，表示量子比特总数

**示例：**
```
QINIT 5
```

### CREG 语句

声明经典比特数量，用于存储测量结果，必须在 QINIT 之后。

**语法：**
```
CREG <n_cbits>
```

**参数：**
- `<n_cbits>`：非负整数，表示经典比特总数

**示例：**
```
CREG 2
```

---

## 量子门操作

OriginIR 支持多种量子逻辑门，根据门的操作对象（量子比特数）和参数数量分类。

### 量子比特引用语法

所有量子门操作使用 `q[<index>]` 格式引用量子比特：

```
q[0]      # 第 0 号量子比特
q[1]      # 第 1 号量子比特
```

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
```originir
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
```originir
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
```originir
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
```originir
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
```originir
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
```originir
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
```originir
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
```originir
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
```originir
TOFFOLI q[0], q[1], q[2]
CSWAP q[0], q[1], q[2]
```

### BARRIER

BARRIER 用于在量子比特之间插入屏障，防止编译器对屏障前后的操作进行重排或优化。

**语法：**
```
BARRIER q[<qubit1>], q[<qubit2>], ...
```

**示例：**
```originir
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
```originir
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
```originir
X q[2] controlled_by (q[0])
X q[3] controlled_by (q[0], q[1])
RX q[2], (1.57) dagger controlled_by (q[0], q[1])
```

**等价关系：**
```originir
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
```originir
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
```originir
QINIT 3
CREG 1

DAGGER
  H q[0]
  CNOT q[0], q[1]
  RX q[2], (1.57)
ENDDAGGER
```

上述 DAGGER 块等价于：
```originir
RX q[2], (1.57) dagger
CNOT q[0], q[1]
H q[0]
```

### 控制结构嵌套

CONTROL 和 DAGGER 可以相互嵌套：

```originir
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
```originir
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

**带参数的语法：**
```
DEF <name>(<qubit_list>) (<param_list>)
  <gate_operations>
ENDDEF
```

**语法元素：**
- `<name>`：子程序名称，由字母、数字、下划线组成，必须以字母或下划线开头
- `<qubit_list>`：量子比特参数列表，格式为 `q[0], q[1], ...`
- `<param_list>`：可选的数值参数列表，格式为 `param1, param2, ...`
- `<gate_operations>`：量子门操作序列

### 无参数 DEF

定义一个 Bell 对制备子程序：

```originir
DEF bell_pair(q[0], q[1])
  H q[0]
  CNOT q[0], q[1]
ENDDEF
```

### 带参数 DEF

定义带参数的旋转门：

```originir
DEF rx_gate(q[0]) (theta)
  RX q[0], (theta)
ENDDEF
```

定义多参数门：

```originir
DEF u3_gate(q[0]) (theta, phi, lambda)
  U3 q[0], (theta, phi, lambda)
ENDDEF
```

### 调用 DEF

在主程序中调用已定义的 DEF：

```originir
QINIT 4
CREG 2

DEF bell_pair(q[0], q[1])
  H q[0]
  CNOT q[0], q[1]
ENDDEF

DEF rx_gate(q[0]) (theta)
  RX q[0], (theta)
ENDDEF

// 调用子程序
bell_pair(q[0], q[1])
bell_pair(q[2], q[3])
rx_gate(q[0]) (1.57)
```

### DEF 与 Python API 对应

DEF 块与 Python 中的 `@circuit_def` 装饰器完全对应：

**OriginIR 定义：**
```originir
DEF bell_pair(q[0], q[1])
  H q[0]
  CNOT q[0], q[1]
ENDDEF
```

**Python 等价定义：**
```python
from uniqc.circuit_builder import circuit_def

@circuit_def(name="bell_pair", qregs={"q": 2})
def bell_pair(circ, q):
    circ.h(q[0])
    circ.cnot(q[0], q[1])
    return circ
```

**带参数的对应：**

```originir
DEF rx_gate(q[0]) (theta)
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
# DEF bell_pair(q[0], q[1])
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
from uniqc.circuit_builder import circuit_def, Circuit

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
# DEF rx_gate(q[0]) (theta)
#   RX q[0], (theta)
# ENDDEF
```

---

## 参数化量子线路

UnifiedQuantum 提供了符号参数系统，支持构建参数化量子线路，常用于变分量子算法（VQA）。

### Parameter 类

`Parameter` 是一个命名符号参数，支持绑定具体值和符号表达式运算。

```python
from uniqc.circuit_builder.parameter import Parameter

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
from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.parameter import Parameter

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
from uniqc.circuit_builder.parameter import Parameters

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
from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.parameter import Parameters

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
from uniqc.circuit_builder import Circuit, circuit_def
from uniqc.circuit_builder.parameter import Parameter, Parameters

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
```originir
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
```originir
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
```originir
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

```originir
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

```originir
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

```originir
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

```originir
QINIT 6
CREG 4

// 定义 Bell 对制备子程序
DEF bell_pair(q[0], q[1])
  H q[0]
  CNOT q[0], q[1]
ENDDEF

// 定义参数化旋转
DEF rx_rot(q[0]) (angle)
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
from uniqc.circuit_builder import Circuit, circuit_def
from uniqc.circuit_builder.parameter import Parameters

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

```originir
QINIT 3
CREG 3

// 定义含噪声的 Bell 对
DEF noisy_bell(q[0], q[1])
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

- {mod}`uniqc.originir` — OriginIR 解析器
  - {class}`uniqc.originir.originir_line_parser.OriginIR_LineParser` — 行解析器
  - {class}`uniqc.originir.originir_base_parser.OriginIR_BaseParser` — 完整程序解析器

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
