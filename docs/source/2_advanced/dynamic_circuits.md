# 动态电路：Mid-circuit measurement 与经典控制流

UnifiedQuantum 在 OriginIR-ext 之上提供了一套 **classical / control-flow 扩展**，
用于表达 *动态电路 (dynamic circuit)*：电路中途测量、把 outcome 写进一块运行时的
classical register (CREG)，再用经典逻辑对后续量子操作做**实时判断**（feed-forward）。
典型场景包括 teleportation 的 correction、magic-state 注入、measurement-based
computing、重复直到成功 (repeat-until-success) 等。

本页说明这套扩展的**设计逻辑**、**语法**、**Circuit API** 与**可运行案例**。

```{note}
这套扩展是 **OriginIR-ext 专属**、**仅本地模拟**的特性：动态电路不能导出成 OpenQASM
或官方 OriginIR，也不能提交到 cloud backend（相关导出/提交会抛
`CircuitTranslationError`）。
```

## 1. 设计逻辑与分层架构

动态电路里既有量子操作（gate、测量、reset），又有纯经典操作（bit 逻辑、条件跳转、
循环）。UnifiedQuantum 把它们干净地分成三层，各司其职：

```
OriginIR_ext_Simulator        # 控制流解释器（QIF / QWHILE）
  │  ├─ 对条件求值（读 CREG）决定分支 / 是否继续循环
  │  ├─ per-shot 重跑整段程序，统计末态 CREG
  │  └─ 屏蔽 simulate_pmeasure / simulate_stateprob
  ▼ 驱动
OpcodeSimulator               # opcode 执行器，持有 CREG
  ├─ 量子 gate opcode ───────►  C++ backend
  ├─ MEASURE q,c  → measure_qubit(q) 塌缩，写 CREG bit c
  ├─ RESET q      → reset_qubit(q)
  └─ AND/OR/XOR/MOV/NOT → 直接改 CREG
C++ backend (uniqc_cpp)       # 只管量子态（statevector / density matrix）
```

几个关键设计决定：

* **C++ backend 不碰经典部分。** 它只维护量子态并提供 `measure_qubit` /
  `reset_qubit` 原语。CREG 完全活在 Python 侧，因此加这套功能**不需要重新编译**
  C++ 扩展。
* **经典指令按 opcode 处理，放在 `OpcodeSimulator` 里。** CREG 是一块随电路执行
  实时更新的存储区，`MEASURE`、`AND`/`OR`/`XOR`/`MOV`/`NOT` 都在这里落地。
* **控制流是「非 opcode」的结构，放在更高层的 `OriginIR_ext_Simulator`。**
  它遍历程序树，遇到 `QIF`/`QWHILE` 就读 `OpcodeSimulator` 的 CREG 求值，再决定
  走哪个分支或是否继续循环。
* **结果靠 per-shot 采样得到。** mid-circuit measurement 会塌缩量子态、经典反馈会
  改变后续门，因此每个 shot 都是一次随机过程：模拟器从全新的 `|0…0>` 态跑完整段
  程序，读出末态 CREG 的 bitstring 作为该 shot 的结果；多 shot 就是重复 N 次并统计。
* **精确聚合路径被禁用。** 正因为每次运行是随机的，`simulate_pmeasure`（精确概率
  向量）与 `simulate_stateprob` 在动态电路上没有良定义，二者会直接抛
  `NotImplementedError`，引导你改用 per-shot 的 `simulate_shots` /
  `simulate_single_shot`。

## 2. CREG 模型

`CREG n` 声明 `n` 个 classical bit `c[0] … c[n-1]`，**每个地址就是一个 bit**
（取值 0/1），地址与声明一一对应：

* `MEASURE q[i], c[j]` 把 qubit `i` 的测量 outcome 写进 `c[j]`（mid-circuit 与末尾
  测量是**同一条语句**，都写 CREG）；
* `QIF` / `QWHILE` 的条件、以及 `AND`/`OR`/… 指令都直接读写这些 bit；
* 每个 shot 开始时 CREG 清零。

**Endianness：** 结果 bitstring 里 `c[0]` 是**最右**（LSB）。例如两个 bit、
`c[0]=1, c[1]=0`，其整数值为 `1`，字符串写作 `"01"`——与 UnifiedQuantum 全局的
endianness 约定一致。

## 3. 语法参考（OriginIR-ext）

| 语句 | 形式 | 语义 |
|---|---|---|
| Mid-circuit 测量 | `MEASURE q[i], c[j]` | 测 qubit i，写 `c[j]` |
| Reset | `RESET q[i]` | 把 qubit i 复位到 `\|0>` |
| 与 | `AND c[d], A, B` | `c[d] = A & B` |
| 或 | `OR c[d], A, B` | `c[d] = A \| B` |
| 异或 | `XOR c[d], A, B` | `c[d] = A ^ B` |
| 取反 | `NOT c[d], A` | `c[d] = ~A`（即 `1-A`） |
| 传送 | `MOV c[d], A` | `c[d] = A` |
| 条件 | `QIF <cond>` … `[QELSE …]` `ENDQIF` | `QELSE` 分支可选 |
| 循环 | `QWHILE <cond>` … `ENDQWHILE` | 条件为真时反复执行 |

* **instruction 关键词全大写**：`AND` / `OR` / `XOR` / `MOV` / `NOT`；
  block 关键词也全大写：`QIF` / `QELSE` / `ENDQIF` / `QWHILE` / `ENDQWHILE`。
* **operand** `A`、`B` 要么是 CREG bit `c[k]`，要么是 immediate `0` / `1`。
  指令采用现代 RISC 风格：**destination 在前、non-destructive**（`AND`/`OR`/`XOR`
  三操作数，`MOV`/`NOT` 二操作数）。

### 条件 (`<cond>`) 文法

条件是对 CREG bit 的**布尔逻辑**（bit 级），操作数为 `c[i]` 或字面量 `0`/`1`；
裸的 `c[i]` 在为 1 时为真。支持的算子（**小写关键词与符号等价**）：

| 关键词 | 符号 | 含义 | 优先级（高→低） |
|---|---|---|---|
| `not` | `~` | 逻辑非 | 最高 |
| `and` | `&` | 与 | ↑ |
| `xor` | `^` | 异或 | ↓ |
| `or`  | `\|` | 或 | 最低 |

可用括号改变结合。下面两种写法完全等价：

```text
QIF c[0] and (not c[1] or c[2])
QIF c[0] & (~c[1] | c[2])
```

序列化时统一输出**符号形式**并完全加括号，保证 round-trip 无歧义。

### 一段完整的 OriginIR-ext 示例

```text
QINIT 3
CREG 3
H q[0]
MEASURE q[0], c[0]
QIF c[0]
X q[1]
MEASURE q[1], c[1]
QELSE
H q[1]
ENDQIF
QWHILE ~c[2]
H q[2]
MEASURE q[2], c[2]
ENDQWHILE
XOR c[2], c[0], c[1]
```

## 4. Circuit builder API

用 `Circuit` 直接搭建等价的动态电路：

```python
from uniqc import Circuit
from uniqc.circuit_builder import imm  # 显式 immediate

c = Circuit(3)
c.creg(3)                      # 声明 CREG 大小（也会随引用到的 c[j] 自动增长）

c.h(0)
c.measure_to(0, 0)             # mid-circuit MEASURE q[0] -> c[0]

c.qif("c[0]")                  # 条件用字符串（或 Cond 对象）
c.x(1)
c.measure_to(1, 1)
c.qelse()                      # 可选的 QELSE 分支
c.h(1)
c.endqif()

c.qwhile("~c[2]")              # QWHILE：只要 c[2] 为 0 就继续
c.h(2)
c.measure_to(2, 2)
c.endqwhile()

c.c_xor(2, 0, 1)               # c[2] = c[0] ^ c[1]
print(c.originir)              # 序列化回 OriginIR-ext
```

方法速查：

| 方法 | 作用 |
|---|---|
| `creg(size)` | 声明 CREG 大小（floor，引用更大 index 时自动增长） |
| `measure_to(qubit, cbit)` | mid-circuit 测量，写 `c[cbit]`（qubit 保持存活） |
| `reset(qubit)` | mid-circuit 复位 |
| `c_and(d, a, b)` / `c_or` / `c_xor` | `c[d] = a ⊙ b` |
| `c_not(d, a)` / `c_mov(d, a)` | `c[d] = ~a` / `c[d] = a` |
| `qif(cond)` / `qelse()` / `endqif()` | `QIF` / `QELSE` / `ENDQIF` |
| `qwhile(cond, max_iterations=None)` | `QWHILE`（`max_iterations` 是模拟器看门狗，见 §6） |
| `endqwhile()` | `ENDQWHILE` |

```{admonition} operand 约定：裸 int 是 CREG bit index
:class: warning
`c_*` 方法里，**裸 `int` 表示 CREG bit 下标 `c[int]`**（feed-forward 最常见的用法），
`"c[k]"` 字符串同理；要写 immediate `0`/`1` 请用 `imm(0)` / `imm(1)`（或字符串
`"0"` / `"1"`）。例如：

- `c.c_mov(0, 1)` → `MOV c[0], c[1]`（把 bit 1 拷到 bit 0）
- `c.c_mov(0, imm(1))` → `MOV c[0], 1`（把 bit 0 置 1）
```

## 5. 运行动态电路

### 5.1 直接用 `OriginIR_ext_Simulator`

```python
from uniqc.simulator import OriginIR_ext_Simulator

sim = OriginIR_ext_Simulator("statevector", seed=2024)
counts = sim.simulate_shots(c, shots=2000)   # {int(CREG值): 次数}，c[0] 为 LSB
one   = sim.simulate_single_shot(c)           # 单个 shot 的 CREG 整数值
```

* 接受 `Circuit` 或 OriginIR-ext 字符串；也支持 `"density_matrix"` backend。
* `seed` 固定后整轮采样可复现；`sim.n_cbit` 给出最近一次程序的 CREG 宽度。
* `simulate_pmeasure` / `simulate_stateprob` 在动态电路上会抛 `NotImplementedError`。
* `simulate_statevector` / `simulate_density_matrix` 返回**单个 shot** 的末态
  （随机样本，供调试用），而非确定性对象。

### 5.2 通过统一任务接口（dummy backend）

`submit_task` / `wait_for_result` 会自动识别动态电路并路由到 CREG 模拟器：

```python
from uniqc.backend_adapter.task_manager import submit_task, wait_for_result

task = submit_task(c, backend="dummy:local:simulator", shots=2000)
print(wait_for_result(task, timeout=60).counts)   # {'...': n, ...}
```

### 5.3 命令行

```bash
uniqc simulate circuit.originir --backend statevector --shots 2000
```

含 `QIF`/`QWHILE`/经典指令的 OriginIR 会被 CLI 自动走 per-shot 采样。

## 6. `QWHILE` 看门狗

`QWHILE` 的表层语法不带迭代上限。为避免写错条件导致的死循环，模拟器内置一个
**iteration watchdog**：单次循环超过上限即抛 `LoopWatchdogError`。

* 逐个 `QWHILE` 覆盖：`c.qwhile("~c[0]", max_iterations=1000)`；
* 全局覆盖：`OriginIR_ext_Simulator(max_while_iterations=10_000)`；
* 默认上限很大（见 `classical_program.DEFAULT_MAX_WHILE_ITERATIONS`）。

## 7. 一个可验证的反馈例子

`H` 之后测 `q0`；若 `c0=1` 则对 `q1` 施加 `X` correction，再测 `q1`。于是 `c1` 恒
等于 `c0`——结果只会出现 `'00'` 与 `'11'`，各约一半：

```python
from uniqc import Circuit
from uniqc.simulator import OriginIR_ext_Simulator

c = Circuit(2); c.creg(2)
c.h(0); c.measure_to(0, 0)
c.qif("c[0]"); c.x(1); c.endqif()
c.measure_to(1, 1)

counts = OriginIR_ext_Simulator("statevector", seed=123).simulate_shots(c, 4000)
# 例如 {0: ~2000, 3: ~2000}；0 -> '00'，3 -> '11'，绝不会出现 '01'/'10'
```

完整、可直接运行的脚本见
[`examples/2_advanced/08_mid_circuit_measurement.py`](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/blob/main/examples/2_advanced/08_mid_circuit_measurement.py)，
其中演示了反馈电路、经典指令与 `QWHILE`「抛硬币直到 1」的写法。

## 8. 作用域与限制

* **仅本地模拟**：C++ 驱动的 `statevector` 与 `density_matrix` 两种 backend。
  MPS / QuTiP / TorchQuantum 暂不支持动态电路。
* **不可导出/提交**：动态电路不能转 OpenQASM、不能转官方 OriginIR、不能提交 cloud。
* **CREG 是 bit 级**：每个 `c[i]` 是单个 bit；经典逻辑都是 bitwise。
* **无噪声反馈**：当前动态执行走 noiseless 路径；把 noise model 注入动态程序尚未支持。
