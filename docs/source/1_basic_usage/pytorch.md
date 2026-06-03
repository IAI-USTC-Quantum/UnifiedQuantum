# PyTorch 集成 {#guide-pytorch}

## 什么时候进入本页

当你希望将量子电路集成到 PyTorch 模型中进行混合量子-经典训练时，阅读本页。

## 本页解决的问题

- 如何在 PyTorch 模型中使用参数化量子电路
- 如何通过 parameter-shift 规则计算梯度
- 如何构建量子-经典混合神经网络

## 前置条件

阅读本页前，建议你已经：

- 熟悉 PyTorch 基础用法（`nn.Module`、自动微分、优化器）
- 了解 [参数化电路](circuit.md#guide-circuit-parametric) 的概念
- 了解 [Named Circuit](circuit.md#guide-circuit-named-circuit) 的用法

## 安装

PyTorch 集成是可选功能，需要单独安装：

```bash
pip install unified-quantum[pytorch]
```

这会安装 `torch>=2.0` 作为依赖。

## QuantumLayer

`QuantumLayer` 是一个 PyTorch `nn.Module`，用于将参数化量子电路封装为可训练层。

### 基本用法

```python
import torch
from uniqc.torch_adapter import QuantumLayer
from uniqc import Circuit, Parameter
from uniqc.simulator import Simulator

# 构建参数化电路（参数名会自动从 circuit._parameters 中读取）
theta = Parameter("theta")
template = Circuit()
template.rx(0, theta)
template.measure(0)

# 定义期望值函数
def expectation(circuit):
    sim = Simulator()
    result = sim.simulate(circuit.originir, shots=1000)
    # 计算 <Z> 期望值
    return result.get_expectation([0])

# 创建 QuantumLayer（参数名自动从 circuit._parameters 提取，无需再传 param_names）
layer = QuantumLayer(
    circuit=template,
    expectation_fn=expectation,
)
```

> 参数名会自动从 `circuit._parameters` 中读取，因此不再需要显式传入 `param_names`。

### 在模型中使用

```python
import torch.nn as nn

model = nn.Sequential(
    nn.Linear(10, 4),
    nn.ReLU(),
    layer,  # QuantumLayer
    nn.Linear(1, 1)
)
```

### 训练

```python
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

for epoch in range(100):
    optimizer.zero_grad()
    
    # 前向传播
    output = model(torch.randn(1, 10))
    
    # 计算损失
    loss = output.sum()
    
    # 反向传播（自动计算量子梯度）
    loss.backward()
    
    # 更新参数
    optimizer.step()
    
    print(f"Epoch {epoch}: loss = {loss.item():.4f}")
```

## Parameter-Shift 梯度

QuantumLayer 使用 parameter-shift 规则计算量子参数的梯度：

$$\frac{\partial f(\theta)}{\partial \theta} = \frac{f(\theta + s) - f(\theta - s)}{2s}$$

其中 $s$ 是 shift 参数（默认 $\pi/2$）。

### 自定义 shift 值

```python
layer = QuantumLayer(
    circuit=template,
    expectation_fn=expectation,
    shift=0.25  # 自定义 shift 值
)
```

## 多参数电路

对于有多个参数的电路：

```python
theta = Parameter("theta")
phi = Parameter("phi")

multi_template = Circuit()
multi_template.rx(0, theta)
multi_template.ry(1, phi)
multi_template.cnot(0, 1)
multi_template.measure(0, 1)

layer = QuantumLayer(
    circuit=multi_template,
    expectation_fn=expectation,
    n_outputs=1,
)
```

## 完整示例：VQE

以下是一个简单的 VQE（变分量子本征求解器）示例：

```python
import torch
import torch.nn as nn
from uniqc.torch_adapter import QuantumLayer
from uniqc import Circuit, Parameter
from uniqc.simulator import Simulator
import numpy as np

# 定义哈密顿量 H = Z0 + Z1 + X0X1
def hamiltonian_expectation(circuit):
    sim = Simulator()
    result = sim.simulate(circuit.originir, shots=1000)
    
    # 计算 <Z0 + Z1 + X0X1>
    # 这里简化为只计算 Z0 + Z1
    exp_z0 = result.get_expectation([0])
    exp_z1 = result.get_expectation([1])
    
    return exp_z0 + exp_z1

# 定义 ansatz
theta = Parameter("theta")
ansatz_circuit = Circuit()

# 初始化
ansatz_circuit.h(0)
ansatz_circuit.h(1)

# 变分层
ansatz_circuit.cnot(0, 1)
ansatz_circuit.rz(1, theta)

ansatz_circuit.measure(0, 1)

# 创建量子层
vqe_layer = QuantumLayer(
    circuit=ansatz_circuit,
    expectation_fn=hamiltonian_expectation,
)

# 优化（QuantumLayer 自己持有可训练参数 self.params）
optimizer = torch.optim.Adam(vqe_layer.parameters(), lr=0.1)

for epoch in range(50):
    optimizer.zero_grad()
    
    # 前向传播
    energy = vqe_layer()
    
    # 反向传播
    energy.backward()
    
    # 更新参数
    optimizer.step()
    
    print(f"Epoch {epoch}: Energy = {energy.item():.4f}")
```

## 批量执行

当需要并行执行多个电路时，可以使用 `batch_execute` 工具：

```python
from uniqc.torch_adapter import batch_execute, batch_execute_with_params
from uniqc.simulator import Simulator

# 定义执行函数
def simulate(circuit):
    sim = Simulator()
    return sim.simulate(circuit.originir, shots=1000)

# 批量执行多个电路
results = batch_execute(
    circuits=[c1, c2, c3],
    executor=simulate,
    n_workers=4
)

# 对同一模板绑定不同参数后批量执行
param_sets = [{'theta': 0.1}, {'theta': 0.2}, {'theta': 0.3}]
results = batch_execute_with_params(
    circuit_template=parametric_circuit,
    param_values=param_sets,
    executor=simulate,
    n_workers=4
)
```

批量执行使用 `ThreadPoolExecutor` 实现并行，适用于：
- 梯度计算（每个参数需要 2 次电路执行）
- 超参数搜索
- 集成电路评估

## 性能优化建议

1. **减少 shots 数量**：调试时使用较少的 shots，最终训练时再增加。

2. **批量执行**：使用 `batch_execute` 并行化电路评估，充分利用多核 CPU。

3. **缓存中间结果**：对于不变的哈密顿量项，可以预计算并缓存结果。

4. **参数 shift 值**：
   - 默认 $\pi/2$ 适用于大多数旋转门
   - 对于特定门（如 RX、RY），可以根据门特性调整
   - 值过小会放大采样噪声，过大会降低梯度精度

5. **GPU 注意事项**：
   - `QuantumLayer` 的参数存储在 GPU 上（如果可用）
   - 量子电路模拟在 CPU 上执行
   - 数据传输开销可能影响性能，建议批量处理

## 注意事项

1. **期望值函数**：`expectation_fn` 必须返回一个标量值，用于计算梯度。

2. **模拟器开销**：每次梯度计算需要执行 $2n$ 次电路模拟（$n$ 为参数数量），对于复杂电路可能较慢。

3. **数值稳定性**：shift 值的选择会影响梯度计算的精度，通常 0.1 到 0.5 之间效果较好。

4. **GPU 支持**：QuantumLayer 的参数在 GPU 上，但量子计算本身在 CPU 上执行。

## 原生训练（推荐）

> 无需 TorchQuantum 依赖，使用原生 PyTorch 态矢量模拟。

### 快速上手：has_param

```python
import torch
from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.torch_adapter.expectation import expectation

# 构建电路 — has_param=True 自动创建 nn.Parameter
c = Circuit(2)
c.ry(0, has_param=True)      # 自动创建可训练参数
c.ry(1, has_param=True)
c.cnot(0, 1)

# 定义哈密顿量
hamiltonian = [("ZZ", 1.0), ("ZI", -0.5), ("IZ", -0.5)]

# 训练
opt = torch.optim.Adam(c.params, lr=0.05)
for step in range(100):
    opt.zero_grad()
    energy = expectation(c, hamiltonian)  # 可微的 ⟨ψ|H|ψ⟩
    energy.backward()
    opt.step()
```

### 参数风格

UnifiedQuantum 支持三种参数传递方式，与 TorchQuantum API 对齐：

**风格 1：has_param（最简洁）**

```python
c = Circuit(2)
c.ry(0, has_param=True)                          # 可训练，随机初始化
c.ry(1, has_param=True, trainable=False)         # 冻结参数
c.rz(0, has_param=True, init_params=0.5)         # 自定义初始值
c.u3(0, has_param=True, init_params=[0.1, 0.2, 0.3])  # 多参数门

# 访问参数
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

**与旧版 QuantumLayer 的区别：**

| 特性 | QuantumLayer（旧） | expectation()（新） |
|------|-------------------|-------------------|
| 梯度方法 | Parameter-shift（2N 次模拟） | PyTorch autograd（1 次模拟） |
| TorchQuantum 依赖 | 无 | 无 |
| Hamiltonian 支持 | 单一项 | 多项累加 |
| 后端切换 | 不支持 | 支持（virtual / torchquantum） |
| 参数管理 | 手动定义 Parameter | has_param 自动创建 |

### 完整 VQE 示例

```python
import torch
from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.torch_adapter.expectation import expectation

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

# 训练
opt = torch.optim.Adam(c.params, lr=0.05)
for step in range(200):
    opt.zero_grad()
    energy = expectation(c, hamiltonian)
    energy.backward()
    opt.step()
    if step % 50 == 0:
        print(f"Step {step}: E = {energy.item():.4f}")
```

## 相关 API

- {mod}`uniqc.torch_adapter` — PyTorch 集成模块
- {func}`uniqc.torch_adapter.expectation` — 后端无关的可微期望值
- {class}`uniqc.torch_adapter.QuantumLayer` — 量子层封装（旧版）
- {func}`uniqc.torch_adapter.parameter_shift_gradient` — Parameter-shift 梯度计算
- {func}`uniqc.torch_adapter.batch_execute` — 并行电路执行
- {func}`uniqc.torch_adapter.batch_execute_with_params` — 参数化批量执行
- {func}`uniqc.torch_adapter.compute_all_gradients` — 计算所有参数梯度

## 下一步

- 了解 [参数化电路](circuit.md#guide-circuit-parametric) 的更多用法
- 学习 [Named Circuit](circuit.md#guide-circuit-named-circuit) 构建复杂电路
- 探索 [算法示例](../algorithm/vqe.md) 中的 VQE 算法
