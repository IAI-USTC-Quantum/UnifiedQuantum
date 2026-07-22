(guide-pytorch)=
# PyTorch 集成

## 什么时候进入本页

当你有一个 **参数化量子电路** 需要优化——无论是用 PyTorch 做端到端可微训练、用
经典优化器扫描参数，还是把量子层嵌入混合神经网络——阅读本页。

## 本页解决的问题

本页按 **从简单到复杂** 的顺序组织：

1. [快速优化参数化电路](#guide-pytorch-has-param)：用 `has_param` 最佳实践，几行代码
   完成一次可微的变分优化（推荐入门方式）。
2. [手动定义 Parameters](#guide-pytorch-manual-params)：用符号 `Parameter`/`Parameters`
   显式管理命名参数、绑定数值，并序列化 / 往返 OriginIR-ext。
3. [PyTorch 集成](#guide-pytorch-torch)：把量子电路嵌入 `nn.Module`、parameter-shift
   梯度、批量执行等进阶用法。

## 前置条件

阅读本页前，建议你已经：

- 熟悉 PyTorch 基础用法（`nn.Module`、自动微分、优化器）
- 了解 [参数化电路](guide-circuit-parametric) 的概念

## 安装

PyTorch 集成是可选功能，需要单独安装：

```bash
pip install unified-quantum[pytorch]
```

这会安装 `torch>=2.0` 作为依赖。本页第 2 节（符号参数）不依赖 PyTorch。

(guide-pytorch-has-param)=
## 1. 快速优化参数化电路（has_param）

> **推荐方式**：无需 TorchQuantum 依赖，梯度通过纯 PyTorch 态矢量模拟自动传播。

给旋转门传入 `has_param=True`，UnifiedQuantum 会自动为它创建一个可训练的
`nn.Parameter`。配合后端无关的 `expectation()` 函数，几行代码即可完成一次变分优化：

```python
import torch
from uniqc import Circuit
from uniqc.torch_adapter import expectation

# 构建电路 —— has_param=True 自动创建可训练参数
c = Circuit(2)
c.ry(0, has_param=True)
c.ry(1, has_param=True)
c.cnot(0, 1)

# 定义哈密顿量 H = Z0Z1 - 0.5 Z0 - 0.5 Z1
hamiltonian = [("ZZ", 1.0), ("ZI", -0.5), ("IZ", -0.5)]

# 训练：c.params 是所有自动创建的 nn.Parameter，可直接交给优化器
opt = torch.optim.Adam(c.params, lr=0.05)
for step in range(100):
    opt.zero_grad()
    energy = expectation(c, hamiltonian)  # 可微的 ⟨ψ|H|ψ⟩
    energy.backward()
    opt.step()
```

### 参数风格

UnifiedQuantum 支持三种向门传参的方式，与 TorchQuantum API 对齐。

**风格 1：has_param（最简洁）**

```python
c = Circuit(2)
c.ry(0, has_param=True)                          # 可训练，随机初始化
c.ry(1, has_param=True, trainable=False)         # 冻结参数
c.rz(0, has_param=True, init_params=0.5)         # 自定义初始值
c.u3(0, has_param=True, init_params=[0.1, 0.2, 0.3])  # 多参数门

c.params                    # 所有 nn.Parameter（可直接传给优化器）
c.get_params_by_gate("RY")  # 按门类型筛选
```

**风格 2：param_dict（命名引用）**

```python
params = {
    "theta": torch.nn.Parameter(torch.tensor(0.5)),
    "phi":   torch.nn.Parameter(torch.tensor(0.3)),
}
c = Circuit(2, param_dict=params)
c.ry(0, "theta")
c.u3(0, "theta", "phi", 0.0)
```

**风格 3：直接传入 tensor**

```python
theta = torch.tensor(0.5, requires_grad=True)
c = Circuit(1)
c.ry(0, theta)  # tensor 自动注册到 param_map
```

### expectation() 函数

`expectation()` 是后端无关的可微期望值计算函数：

```python
from uniqc.torch_adapter import expectation

# 默认使用 virtual 后端（原生 PyTorch 态矢量模拟）
energy = expectation(c, [("ZZ", 1.0), ("ZI", -0.5)])

# 可切换后端
energy = expectation(c, [("Z", 1.0)], backend="torchquantum")
```

它通过 PyTorch autograd 一次前向即可反向传播，无需 parameter-shift 的多次电路求值。

### 完整示例：VQE

```python
import torch
from uniqc import Circuit
from uniqc.torch_adapter import expectation

# HEA ansatz
n_qubits, depth = 2, 2
c = Circuit(n_qubits)
for _ in range(depth):
    for q in range(n_qubits):
        c.rz(q, has_param=True)
        c.ry(q, has_param=True)
    for q in range(n_qubits):
        c.cnot(q, (q + 1) % n_qubits)

# H₂ 哈密顿量
hamiltonian = [("ZZ", 0.5), ("ZI", 0.5), ("IZ", 0.5), ("XX", -0.25)]

opt = torch.optim.Adam(c.params, lr=0.05)
for step in range(200):
    opt.zero_grad()
    energy = expectation(c, hamiltonian)
    energy.backward()
    opt.step()
    if step % 50 == 0:
        print(f"Step {step}: E = {energy.item():.4f}")
```

> 完整可运行示例见 `examples/3_best_practices/11_native_torch_training.py`。

(guide-pytorch-manual-params)=
## 2. 手动定义 Parameters（符号参数）

当你需要 **显式命名的参数**——例如用经典优化器（`scipy.optimize`）扫描、复用同一
模板绑定不同数值，或把参数化电路 **序列化 / 共享** 为 OriginIR-ext 文本——使用符号
`Parameter` / `Parameters`。它们基于 sympy，与上一节的 `has_param`（自动、面向
autograd）互补。

### 创建、运算与绑定

```python
from uniqc import Circuit, Parameter, Parameters

theta = Parameter("theta")
phi = Parameter("phi")

# 算术运算自动生成 sympy 符号表达式
expr = theta * 2 + phi / 3

# 绑定 / 求值 / 解绑
theta.bind(1.0)
theta.evaluate()               # 1.0（绑定值优先）
theta.unbind()                 # 恢复为符号状态
theta.evaluate({"theta": 2.0}) # 2.0（未绑定时查字典）

# 参数数组：alpha_0 ... alpha_3
alphas = Parameters("alpha", size=4)
alphas.bind([0.1, 0.2, 0.3, 0.4])
```

### 构建电路并绑定数值

把符号参数传给门即可构建 **未绑定** 的参数化电路，随后用
`Circuit.assign_parameters`（别名 `bind_parameters`）绑定为具体数值。默认返回
新电路（不修改原电路），并支持部分绑定：

```python
c = Circuit(2)
c.rx(0, theta)
c.ry(1, theta * 2 + phi / 3)   # 符号表达式
c.rz(0, alphas[0])
c.measure(0, 1)

print(c.free_parameters)       # ['alpha_0', 'phi', 'theta']

bound = c.assign_parameters({"theta": 0.5, phi: 1.0, alphas: [0.1, 0.2, 0.3, 0.4]})
print(bound.is_parametric)     # False —— 可直接模拟 / 提交
```

### 序列化与 OriginIR-ext 往返

符号电路会序列化为带 `PARAM` 头的 OriginIR-ext，并能无损往返解析
（`from_originir(c.originir).originir == c.originir`）：

```python
print(c.originir)
# QINIT 2
# CREG 2
# PARAM alpha[4]
# PARAM phi
# PARAM theta
# RX q[0], (theta)
# RY q[1], (phi/3 + 2*theta)
# RZ q[0], (alpha[0])
# MEASURE q[0], c[0]
# MEASURE q[1], c[1]

c2 = Circuit.from_originir(c.originir)   # 保留参数名与数组结构
```

细节（`PARAM` 语法、表达式限制、必须先绑定才能模拟 / 提交云端）见
[参数化电路 · 序列化为 OriginIR-ext](circuit.md)。

> **has_param 还是符号 Parameters？** `has_param` 面向 PyTorch autograd、参数匿名、
> 最适合训练；符号 `Parameters` 面向命名与序列化，可配任意（经典）优化器，并能
> 往返 OriginIR-ext。两者互不排斥，可按需选用。

(guide-pytorch-torch)=
## 3. PyTorch 集成（nn.Module 与进阶用法）

### 推荐：用 expectation() 嵌入 nn.Module

把 `expectation()` 包进一个自定义 `nn.Module`，即可将量子层接入任意经典网络，
梯度自动通过 autograd 传播：

```python
import torch
import torch.nn as nn
from uniqc import Circuit
from uniqc.torch_adapter import expectation

class QuantumHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.c = Circuit(2)
        self.c.ry(0, has_param=True)
        self.c.ry(1, has_param=True)
        self.c.cnot(0, 1)
        # 注册可训练量子参数，让 .parameters() 能发现它们
        self.q_params = nn.ParameterList(self.c.params)
        self.h = [("ZZ", 1.0)]

    def forward(self, x):
        return expectation(self.c, self.h).reshape(1)

model = nn.Sequential(nn.Linear(4, 4), nn.ReLU(), QuantumHead())
```

### QuantumLayer（旧版 / parameter-shift）

> `QuantumLayer` 是较早的封装，使用 parameter-shift 规则（每个参数 2 次电路求值）。
> 新代码建议优先使用上面的 `expectation()` 方案；此处保留用于兼容与硬件后端场景。

```python
import torch
from uniqc.torch_adapter import QuantumLayer
from uniqc import Circuit, Parameter
from uniqc.simulator import Simulator

theta = Parameter("theta")
template = Circuit()
template.rx(0, theta)
template.measure(0)

def expectation_fn(circuit):
    result = Simulator().simulate(circuit.originir, shots=1000)
    return result.get_expectation([0])

# 参数名自动从 circuit._parameters 提取，无需再传 param_names
layer = QuantumLayer(circuit=template, expectation_fn=expectation_fn)

optimizer = torch.optim.Adam(layer.parameters(), lr=0.1)
for epoch in range(50):
    optimizer.zero_grad()
    energy = layer()
    energy.backward()
    optimizer.step()
```

`QuantumLayer` 与 `expectation()` 的对比：

| 特性 | QuantumLayer（旧） | expectation()（新） |
|------|-------------------|-------------------|
| 梯度方法 | Parameter-shift（2N 次模拟） | PyTorch autograd（1 次模拟） |
| TorchQuantum 依赖 | 无 | 无 |
| Hamiltonian 支持 | 单一项 | 多项累加 |
| 后端切换 | 不支持 | 支持（virtual / torchquantum） |
| 参数管理 | 手动定义 Parameter | has_param 自动创建 |

#### Parameter-Shift 梯度

`QuantumLayer` 使用 parameter-shift 规则：

$$\frac{\partial f(\theta)}{\partial \theta} = \frac{f(\theta + s) - f(\theta - s)}{2s}$$

其中 $s$ 是 shift 参数（默认 $\pi/2$），可通过 `QuantumLayer(..., shift=0.25)` 自定义。

### 批量执行

需要并行评估多个电路时（梯度计算、超参数搜索、集成评估），使用 `batch_execute`：

```python
from uniqc.torch_adapter import batch_execute, batch_execute_with_params
from uniqc.simulator import Simulator

def simulate(circuit):
    return Simulator().simulate(circuit.originir, shots=1000)

# 批量执行多个电路
results = batch_execute(circuits=[c1, c2, c3], executor=simulate, n_workers=4)

# 对同一模板绑定不同参数后批量执行
param_sets = [{"theta": 0.1}, {"theta": 0.2}, {"theta": 0.3}]
results = batch_execute_with_params(
    circuit_template=parametric_circuit,
    param_values=param_sets,
    executor=simulate,
    n_workers=4,
)
```

批量执行基于 `ThreadPoolExecutor`，充分利用多核 CPU。

### 性能与注意事项

1. **优先 `expectation()`**：autograd 单次前向即可反传，比 parameter-shift 的 2N 次
   电路求值快得多。
2. **调试时减少 shots**：最终训练时再增大。
3. **批量执行**：用 `batch_execute` 并行化电路评估。
4. **shift 值（parameter-shift）**：默认 $\pi/2$ 适用于大多数旋转门；过小会放大采样
   噪声，过大会降低梯度精度。
5. **GPU**：量子参数可存于 GPU，但态矢量模拟在 CPU 执行，注意数据传输开销。

## 相关 API

- {mod}`uniqc.torch_adapter` — PyTorch 集成模块
- {func}`uniqc.torch_adapter.expectation` — 后端无关的可微期望值（推荐）
- {class}`uniqc.torch_adapter.QuantumLayer` — 量子层封装（旧版，parameter-shift）
- {func}`uniqc.torch_adapter.batch_execute` — 并行电路执行
- {func}`uniqc.torch_adapter.batch_execute_with_params` — 参数化批量执行
- {class}`uniqc.circuit_builder.Parameter` — 符号参数
- {class}`uniqc.circuit_builder.Parameters` — 符号参数数组

## 下一步

- 了解 [参数化电路](guide-circuit-parametric) 与
  [OriginIR-ext 参数序列化](circuit.md)
- 学习 [Named Circuit](guide-circuit-named-circuit) 构建复杂电路
- 探索 [变分与混合算法示例](../8_algorithms_examples/variational_hybrid.md)
