# 概述

## 核心工作流

UnifiedQuantum 的设计围绕一个简洁的工作流：**任意方式构建线路 → CLI 统一执行**。

```bash
# 步骤 1：安装
pip install unified-quantum
```

```python
# 步骤 2：构建线路（支持 UnifiedQuantum 原生或任意第三方工具）
from uniqc.circuit_builder import Circuit

c = Circuit()
c.h(0)
c.cnot(0, 1)
c.measure(0, 1)

# 输出 OriginIR 格式，可供 CLI 使用
open('circuit.ir', 'w').write(c.originir)
```

```bash
# 步骤 3：CLI 统一执行

# 本地模拟
uniqc simulate circuit.ir --shots 1000

# 提交到云端
uniqc submit circuit.ir --platform originq --shots 1000

# 查询任务结果
uniqc result <task_id>
```

## 设计理念

**线路构建，工具自由**

UnifiedQuantum 提供原生的 Circuit API，但你也可以使用 Qiskit、Cirq 等任何工具构建线路。最终只需输出 OriginIR 或 OpenQASM 2.0 格式即可。

**CLI 执行，接口统一**

无论是本地模拟还是云端真机，CLI 提供一致的命令接口：`simulate`、`submit`、`result`、`config`。

**结果数据，原生结构**

测量结果以 Python 原生 `dict` / `list` / `ndarray` 返回，无需额外解析，便于集成到数据分析流程。

## 快速入口

**首次接触？**

{Installation} → {Quickstart} → {Circuit} → {Simulation} → {Submit Task}

**进阶功能**

{OriginIR} | {OpenQASM 2.0} | {PyTorch} | {Task Manager} | Transpiler | {Circuit Analysis}

**命令行工具**

{CLI Installation} | {Simulate} | {Submit} | {Result} | {Config}

**版本变化**

{Releases}

**算法示例**

**变分算法** {VQE} | {QAOA} | {VQD}

**搜索算法** {Grover} | {Grover Oracle}

**相位估计** {QPE} | {QFT}

**Oracle 算法** {Amplitude Estimation} | {Deutsch-Jozsa}

**态制备** {Entangled States} | {Dicke State} | {Thermal State}

**测量** {Shadow Tomography} | {State Tomography}
