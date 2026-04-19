<p align="center">
  <img src="banner_uniq.png" alt="UnifiedQuantum Banner" width="100%">
</p>

# UnifiedQuantum

[![PyPI version](https://badge.fury.io/py/unified-quantum.svg?icon=si%3Apython)](https://badge.fury.io/py/unified-quantum)
[![codecov](https://codecov.io/github/IAI-USTC-Quantum/UnifiedQuantum/graph/badge.svg?token=PFQ6F7HQY7)](https://codecov.io/github/IAI-USTC-Quantum/UnifiedQuantum)
[![Build and Test](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions/workflows/build_and_test.yml/badge.svg?branch=main)](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions/workflows/build_and_test.yml)

**UnifiedQuantum** — A unified, non-commercial quantum computing aggregation framework.

UnifiedQuantum is a lightweight Python framework that provides a **unified interface** for quantum circuit construction, simulation, and cloud execution across multiple quantum computing platforms. It aggregates backends including OriginQ, Quafu, and IBM Quantum under one consistent API.

---

## 核心工作流

UnifiedQuantum 围绕一个简洁的工作流设计：**任意方式构建线路 → `uniqc` CLI 统一执行**。

### 1. 安装

```bash
pip install unified-quantum
```

### 2. 构建线路（支持原生 API 或任意第三方工具）

```python
from uniq.circuit_builder import Circuit

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0, 1)

# 输出 OriginIR 格式，可供 CLI 使用
open('circuit.ir', 'w').write(c.originir)
```

> 你也可以使用 Qiskit、Cirq 等工具构建线路，只需最终输出 OriginIR 或 OpenQASM 2.0 格式。

### 3. CLI 统一执行

```bash
# 本地模拟
uniqc simulate circuit.ir --shots 1000

# 提交到云端
uniqc submit circuit.ir --platform originq --shots 1000

# 查询任务结果
uniqc result <task_id>
```

---

## 设计理念

UnifiedQuantum 是一个**非商业性**的开源项目，四条基本立场贯穿整个设计：

- **聚合**：把分散的量子云平台（OriginQ、Quafu、IBM Quantum 等）收拢到同一套接口下。
- **统一**：从线路构建、模拟执行到任务管理，对外呈现一致的 API 与 CLI，不让用户为每家平台单独学一套。
- **透明**：线路如何组装、如何被翻译、如何提交到后端，全部显式可见，没有隐藏的 magic。
- **轻量**：纯 Python 实现（C++ 加速模拟器为可选项），依赖少、安装快、易于嵌入现有项目。

抽象上，UnifiedQuantum 的三个核心对象覆盖了完整的量子程序生命周期：

- **Circuit** — 量子线路构建器，原生支持 OriginIR / OpenQASM 2.0 双格式输出。
- **Backend** — 本地模拟器或真实量子硬件的统一句柄。
- **Result** — 测量结果以原生 Python 结构返回（`dict` / `list` / `ndarray`），便于后处理。

---

## Features

- **多平台提交**：一个 `submit_task`（或 `uniqc submit`）即可将同一份 OriginIR 发往 OriginQ、Quafu、IBM Quantum，或本地 dummy 模拟器。
- **本地模拟**：自带 OriginIR Simulator、QASM Simulator，支持 statevector / density matrix 两种后端，以及带噪声的变体。
- **算法组件**：内置 HEA、UCCSD、QAOA 等常用 ansatz，可直接用于 VQE / QAOA 研究。
- **PyTorch 集成**：提供 `QuantumLayer`、参数偏移梯度、批处理执行，便于构建混合量子—经典模型。
- **可互操作**：线路既可用原生 API 构建，也可来自 Qiskit、Cirq 等第三方工具，只要最终产出 OriginIR 或 OpenQASM 2.0。
- **同步 / 异步并存**：`submit_task` 立即返回 `task_id`；`wait_for_result` 或 `--wait` 可阻塞至完成。
- **易扩展**：门集、错误模型、平台适配器都按接口组织，添加新后端只需实现一个 adapter。

---

## Installation

### Supported Platforms

- Windows / Linux / macOS

### Requirements

- Python 3.10 – 3.13

### pip（推荐）

```bash
pip install unified-quantum
```

### uv tool（作为独立 CLI 工具安装）

如果只想在命令行用 `uniqc` 而不污染全局环境：

```bash
# 现代 uv（>= 0.5）用 `add`，老版本用 `install`
uv tool install unified-quantum

# 带可选依赖
uv tool install "unified-quantum[simulation]"

# 升级 / 卸载
uv tool upgrade unified-quantum
uv tool uninstall unified-quantum
```

`uv tool` 会为 `uniqc` 创建一个独立的虚拟环境并把可执行文件链接到 `~/.local/bin/uniqc`。

### Build from Source

**纯 Python（无 C++ 依赖）：**

```bash
git clone https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum
pip install . --no-cpp
```

**开发模式：**

```bash
pip install -e .
```

**含 C++ 模拟器（需 CMake）：**

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum
pip install .
```

### Optional Dependencies

核心依赖（包括 `scipy`）在默认安装中已包含。以下为可选功能依赖：

| 功能 | 安装命令 |
|------|---------|
| OriginQ 云平台 | `pip install unified-quantum[originq]` |
| Quafu 执行后端 | `pip install unified-quantum[quafu]` |
| Qiskit 执行后端 | `pip install unified-quantum[qiskit]` |
| 高级模拟 (QuTiP) | `pip install unified-quantum[simulation]` |
| 可视化 | `pip install unified-quantum[visualization]` |
| PyTorch 集成 | `pip install unified-quantum[pytorch]` |
| 安装所有可选依赖 | `pip install unified-quantum[all]` |

---

## CLI Quick Reference

```bash
# 查看帮助
uniqc --help

# 本地模拟
uniqc simulate circuit.ir --shots 1000

# 提交到云端（支持 originq / quafu / ibm / dummy）
uniqc submit circuit.ir --platform originq --shots 1000

# 查询任务结果
uniqc result <task_id>

# 配置云平台 Token
uniqc config init
uniqc config set originq.token YOUR_TOKEN

# 也可以用 python -m 调用（等价于 uniqc）
python -m uniq simulate circuit.ir
```

---

## Examples

📁 [examples/](examples/README.md) — Runnable demonstrations

### Getting Started

| Example | Description |
|---------|-------------|
| [Circuit Remapping](examples/getting-started/1_circuit_remap.py) | Build a circuit and remap qubits for real hardware |
| [Dummy Server](examples/getting-started/2_dummy_server.py) | Submit tasks to the local dummy simulator |
| [Result Post-Processing](examples/getting-started/3_result_postprocess.py) | Convert and analyze results |

### Algorithms

| Example | Description |
|---------|-------------|
| [Grover Search](examples/algorithms/grover.md) | Unstructured search with quadratic speedup |
| [Quantum Phase Estimation](examples/algorithms/qpe.md) | Eigenvalue phase estimation |

---

## Documentation

📖 [GitHub Pages](https://iai-ustc-quantum.github.io/UnifiedQuantum/)

---

## Status

🚧 Actively developing. API may change.
