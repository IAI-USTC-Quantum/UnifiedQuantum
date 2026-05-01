<p align="center">
  <img src="https://raw.githubusercontent.com/IAI-USTC-Quantum/UnifiedQuantum/v0.0.5/banner_uniqc.png" alt="UnifiedQuantum Banner" width="100%">
</p>

# UnifiedQuantum

[![PyPI version](https://badge.fury.io/py/unified-quantum.svg?icon=si%3Apython)](https://badge.fury.io/py/unified-quantum)
[![codecov](https://codecov.io/github/IAI-USTC-Quantum/UnifiedQuantum/graph/badge.svg?token=PFQ6F7HQY7)](https://codecov.io/github/IAI-USTC-Quantum/UnifiedQuantum)
[![Build and Test](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions/workflows/build_and_test.yml/badge.svg?branch=main)](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions/workflows/build_and_test.yml)
[![Quantum | AI](https://img.shields.io/badge/Quantum_Computing-AI-00e5ff?style=flat-square)](https://iai-ustc-quantum.github.io/)

**UnifiedQuantum** — A unified, non-commercial quantum computing aggregation framework.

UnifiedQuantum is a lightweight Python framework that provides a **unified interface** for quantum circuit construction, simulation, and cloud execution across multiple quantum computing platforms. It aggregates backends including OriginQ, Quafu, and IBM Quantum under one consistent API.

---

## 核心工作流

UnifiedQuantum 围绕一个简洁的工作流设计：**任意方式构建线路 → `uniqc` CLI 统一执行**。

### 1. 安装

```bash
# 推荐：通过 uv 安装 CLI 工具（全局可用，无需虚拟环境）
uv tool install unified-quantum

# 或从 PyPI 安装 Python 包（提供 Python API）
uv pip install unified-quantum
```

### 2. 构建线路（支持原生 API 或任意第三方工具）

```python
from uniqc.circuit_builder import Circuit

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
- **轻量**：依赖少、安装快、易于嵌入现有项目。

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

> **结果格式差异**：各平台 `wait_for_result()` 返回的 `result` 内层结构不同：
> - OriginQ / Dummy：`{"00": 512, "11": 488}`（扁平 `{bitstring: shots}` dict）
> - Quafu：`{"counts": {"00": 512, "11": 488}, "probabilities": {...}}`（嵌套 dict）
> - IBM：`[{"00": 512}, {"01": 300}]`（counts dict 的列表，批量时每个电路一个元素）
> 详见[平台约定文档](docs/source/guide/platform_conventions.md)。

---

## Installation

### Supported Platforms

- Windows / Linux / macOS

### Requirements

- Python 3.10 – 3.13

### 从 PyPI 安装（推荐）

```bash
# 安装 CLI 工具（全局可用，无需虚拟环境）
uv tool install unified-quantum

# 安装 Python 包（提供 Python API，可与 uv tool 安装共存）
uv pip install unified-quantum
```

> **中国大陆用户推荐配置清华源**，可大幅提升下载速度：
> ```bash
> # 临时使用（仅本次）
> uv pip install unified-quantum --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
> # 永久生效
> uv pip install --python-preference managed --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
> ```

### 从源码构建

如果你需要开发新版、安装开发版本或启用 C++ 模拟器：

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum

# 安装 CLI + Python 包（开发模式，源码可编辑，含全部可选依赖）
uv tool install -e .[all]

# 仅安装 Python 包（开发模式，不含可选依赖）
uv pip install -e . --no-build-isolation
```

**Requirements:**
- CMake >= 3.26
- C++ compiler with C++17 support
- Git submodules (pybind11, fmt)

如果系统 CMake 版本过低（< 3.26），先升级：

```bash
pip install cmake --upgrade
```

### pip 备选方案

> pip 不支持 `uv tool install` 的 CLI 全局安装方式（无需虚拟环境即可全局调用 `uniqc` 命令）。如无特殊需求，推荐使用上面的 `uv` 安装方式。

```bash
# 从 PyPI 安装
pip install unified-quantum

# 从源码安装
pip install .
pip install -e . --no-build-isolation
```

### 可选依赖

核心依赖（包括 `scipy`）在默认安装中已包含。以下为可选功能依赖：

| 功能 | 安装命令（uv） | pip 备选 |
|------|----------------|---------|
| OriginQ 云平台 | `uv pip install unified-quantum[originq]` | `pip install unified-quantum[originq]` |
| Quafu 执行后端 | `uv pip install unified-quantum[quafu]` | `pip install unified-quantum[quafu]` |
| Qiskit 执行后端 | `uv pip install unified-quantum[qiskit]` | `pip install unified-quantum[qiskit]` |
| 高级模拟 (QuTiP) | `uv pip install unified-quantum[simulation]` | `pip install unified-quantum[simulation]` |
| 可视化 | `uv pip install unified-quantum[visualization]` | `pip install unified-quantum[visualization]` |
| PyTorch 集成 | `uv pip install unified-quantum[pytorch]` | `pip install unified-quantum[pytorch]` |
| 安装所有可选依赖 | `uv pip install unified-quantum[all]` | `pip install unified-quantum[all]` |

TorchQuantum 后端当前不包含在 PyPI extras 中，需要手动安装：

```bash
uv pip install unified-quantum[pytorch]
uv pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"
```

不安装 TorchQuantum 不会影响核心功能、QuTiP 模拟、云平台适配器或常规 `uniqc.pytorch` 功能；只有 TorchQuantum 专用后端与示例会在实际使用时提示缺少该依赖。

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
python -m uniqc simulate circuit.ir
```

### 后端信息查询

```bash
# 列出所有可用后端（默认隐藏 unavailable/deprecated）
uniqc backend list

# 显示所有后端（包括 unavailable/deprecated）
uniqc backend list --all

# 显示带保真度信息的表格
uniqc backend list --info

# 查看单个后端详情（含保真度、相干时间、拓扑）
uniqc backend show originq:WK_C180

# 强制刷新后端缓存（update 始终全量拉取最新数据）
uniqc backend update
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

### Release Notes

- 版本变化总览：<https://iai-ustc-quantum.github.io/UnifiedQuantum/source/releases/index.html>

---

## 关于我们

**UnifiedQuantum** 由 [IAI-USTC-Quantum](https://github.com/IAI-USTC-Quantum) 团队开发和维护。

- **机构**：[合肥综合性国家科学中心人工智能研究院](https://iai-ustc-quantum.github.io) · 量子人工智能团队
- **GitHub 组织**：[github.com/IAI-USTC-Quantum](https://github.com/IAI-USTC-Quantum)
- **文档站点**：[iai-ustc-quantum.github.io](https://iai-ustc-quantum.github.io)
- **联系我们**：chenzhaoyun@iai.ustc.edu.cn

欢迎提交 Issues、Pull Request，或通过邮件联系我们。如果您对量子计算研究感兴趣，欢迎加入我们。

---

## Status

🚧 Actively developing. API may change.
