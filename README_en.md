<p align="center">
  <img src="https://raw.githubusercontent.com/IAI-USTC-Quantum/UnifiedQuantum/v0.0.5/banner_uniqc.png" alt="UnifiedQuantum Banner" width="100%">
</p>

# UnifiedQuantum

[![PyPI version](https://badge.fury.io/py/unified-quantum.svg?icon=si%3Apython)](https://badge.fury.io/py/unified-quantum)
[![codecov](https://codecov.io/github/IAI-USTC-Quantum/UnifiedQuantum/graph/badge.svg?token=PFQ6F7HQY7)](https://codecov.io/github/IAI-USTC-Quantum/UnifiedQuantum)
[![Build and Test](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions/workflows/build_and_test.yml/badge.svg?branch=main)](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions/workflows/build_and_test.yml)
[![Quantum | AI](https://img.shields.io/badge/Quantum_Computing-AI-00e5ff?style=flat-square)](https://iai-ustc-quantum.github.io/)
[![Skill](https://img.shields.io/badge/Skill-quantum--computing.skill-58a6ff?style=flat-square)](https://github.com/IAI-USTC-Quantum/quantum-computing.skill)

**[中文版](README.md)** | **English**

**UnifiedQuantum** — A unified, non-commercial quantum computing aggregation framework.

UnifiedQuantum is a lightweight Python framework that provides a **unified interface** for quantum circuit construction, simulation, and cloud execution across multiple quantum computing platforms. It aggregates backends including OriginQ, Quafu, and IBM Quantum under one consistent API.

---

## Core Workflow

UnifiedQuantum follows a simple workflow: **build circuits any way you like → execute with `uniqc` CLI**.

### 1. Installation

```bash
# Recommended: install CLI via uv (globally available, no virtual env needed)
uv tool install unified-quantum

# Or install Python package from PyPI (provides Python API)
uv pip install unified-quantum
```

### 2. Build a Circuit (native API or any third-party tool)

```python
from uniqc.circuit_builder import Circuit

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0, 1)

# Output OriginIR format for CLI consumption
open('circuit.ir', 'w').write(c.originir)
```

> You can also build circuits with Qiskit, Cirq, etc. — just output OriginIR or OpenQASM 2.0 in the end.

### 3. Execute via CLI

```bash
# Local simulation
uniqc simulate circuit.ir --shots 1000

# Submit to cloud
uniqc submit circuit.ir --platform originq --shots 1000

# Query result
uniqc result <task_id>
```

---

## Design Philosophy

UnifiedQuantum is a **non-commercial** open-source project built for the **AI era**:

- **AI-native**: Designed for AI workflows, seamlessly integrated into modern development and inference pipelines
- **CLI-first**: Out-of-the-box command-line tool — one command to build, simulate, submit, and analyze
- **Aggregation**: Unified interface across multiple quantum cloud platforms (OriginQ, Quafu, IBM Quantum)
- **Consistency**: One API to rule them all — no per-platform learning curve
- **Transparency**: Explicit circuit assembly, translation, and submission — no hidden magic
- **Lightweight**: Pure Python, easy to install and integrate

> **Companion Skill**: Get the Claude Code integration guide and AI-assisted quantum programming workflow at [IAI-USTC-Quantum/quantum-computing.skill](https://github.com/IAI-USTC-Quantum/quantum-computing.skill).

<p align="center">
  <img src="concept_unified_platforms.png" alt="UnifiedQuantum Platform Unification Concept" width="100%">
</p>

---

## Features

- **Multi-platform submission**: One `submit_task` (or `uniqc submit`) sends the same OriginIR to OriginQ, Quafu, IBM Quantum, or the local dummy simulator.
- **Local simulation**: Built-in OriginIR Simulator and QASM Simulator, supporting statevector / density matrix backends, plus noisy variants.
- **Algorithm components**: Built-in HEA, UCCSD, QAOA ansatz ready for VQE / QAOA research.
- **PyTorch integration**: `QuantumLayer`, parameter-shift gradients, and batched execution for hybrid quantum-classical models.
- **Interoperable**: Circuits from native API, Qiskit, Cirq, etc. — as long as they output OriginIR or OpenQASM 2.0.
- **Sync / async**: `submit_task` returns `task_id` immediately; `wait_for_result` or `--wait` blocks until done.
- **Easily extensible**: Gate sets, noise models, and platform adapters all follow interface contracts — a new backend is one adapter away.

> **Result format differences**: `wait_for_result()` returns different inner structures per platform:
> - OriginQ / Dummy: `{"00": 512, "11": 488}` (flat `{bitstring: shots}` dict)
> - Quafu: `{"counts": {"00": 512, "11": 488}, "probabilities": {...}}` (nested dict)
> - IBM: `[{"00": 512}, {"01": 300}]` (list of counts dicts, one per circuit in batch mode)
> See [platform conventions](docs/source/guide/platform_conventions.md) for details.

---

## Installation

### Supported Platforms

- Windows / Linux / macOS

### Requirements

- Python 3.10 – 3.13

### From PyPI (Recommended)

```bash
# Install CLI tool (globally available, no virtual env needed)
uv tool install unified-quantum

# Install Python package (provides Python API; coexists with uv tool install)
uv pip install unified-quantum
```

### Build from Source

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum

# Install CLI + Python package (editable, all optional deps)
uv tool install -e .[all]

# Python package only (editable, no optional deps)
uv pip install -e . --no-build-isolation
```

**Requirements:**
- CMake >= 3.26
- C++ compiler with C++17 support
- Git submodules (pybind11, fmt)

If your system CMake is too old (< 3.26):

```bash
pip install cmake --upgrade
```

### pip Alternative

```bash
# From PyPI
pip install unified-quantum

# From source
pip install .
pip install -e . --no-build-isolation
```

### Optional Dependencies

Core dependencies (including `scipy`) are included by default.

| Feature | Install command (uv) | pip fallback |
|---------|---------------------|-------------|
| OriginQ cloud | `uv pip install unified-quantum[originq]` | `pip install unified-quantum[originq]` |
| Quafu backend | `uv pip install unified-quantum[quafu]` | `pip install unified-quantum[quafu]` |
| Qiskit backend | `uv pip install unified-quantum[qiskit]` | `pip install unified-quantum[qiskit]` |
| Advanced simulation (QuTiP) | `uv pip install unified-quantum[simulation]` | `pip install unified-quantum[simulation]` |
| Visualization | `uv pip install unified-quantum[visualization]` | `pip install unified-quantum[visualization]` |
| PyTorch integration | `uv pip install unified-quantum[pytorch]` | `pip install unified-quantum[pytorch]` |
| All optional deps | `uv pip install unified-quantum[all]` | `pip install unified-quantum[all]` |

TorchQuantum backend is not in PyPI extras yet — install it manually:

```bash
uv pip install unified-quantum[pytorch]
uv pip install "torchquantum @ git+https://github.com/Agony5757/torchquantum.git@fix/optional-qiskit-deps"
```

---

## CLI Quick Reference

```bash
# Help
uniqc --help

# Local simulation
uniqc simulate circuit.ir --shots 1000

# Submit to cloud (originq / quafu / ibm / dummy)
uniqc submit circuit.ir --platform originq --shots 1000

# Query result
uniqc result <task_id>

# Configure cloud platform token
uniqc config init
uniqc config set originq.token YOUR_TOKEN

# python -m also works (equivalent to uniqc)
python -m uniqc simulate circuit.ir
```

### Backend Information

```bash
# List all available backends
uniqc backend list

# Show all backends (including unavailable/deprecated)
uniqc backend list --all

# Table with fidelity information
uniqc backend list --info

# Single backend detail (fidelity, coherence, topology)
uniqc backend show originq:WK_C180

# Force refresh backend cache
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

- Full changelog: <https://iai-ustc-quantum.github.io/UnifiedQuantum/source/releases/index.html>

---

## About Us

**UnifiedQuantum** is developed and maintained by the [IAI-USTC-Quantum](https://github.com/IAI-USTC-Quantum) team.

- **Institution**: [Institute of Artificial Intelligence, Hefei Comprehensive National Science Center](https://iai-ustc-quantum.github.io/) — Quantum AI Team
- **GitHub**: [github.com/IAI-USTC-Quantum](https://github.com/IAI-USTC-Quantum)
- **Docs**: [iai-ustc-quantum.github.io](https://iai-ustc-quantum.github.io)
- **Contact**: chenzhaoyun@iai.ustc.edu.cn

Issues, pull requests, and emails are all welcome. Interested in quantum computing research? Come join us.

---

## Status

🚧 Actively developing. API may change.
