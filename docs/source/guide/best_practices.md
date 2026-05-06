# 推荐使用路径

UnifiedQuantum 现在按功能边界组织模块，日常代码优先从 `uniqc` 直接导入常用对象。新代码不应继续依赖 `uniqc.transpiler`、`uniqc.task`、`uniqc.qasm`、`uniqc.originir`、`uniqc.pytorch`、`uniqc.analyzer` 等旧入口。

如果你需要发布前的端到端可验证案例，请阅读 [最佳实践](../best_practices/index.md)。该章节由已执行 notebooks 组成，覆盖配置、后端缓存、线路构建、CLI/API 提交、变分线路、Torch 集成、Calibration 与 QEM。

## Maintainer 开发环境

仓库由 `uv` 管理。维护者做全量开发和全量测试时，应使用完整 extras 和 dev 依赖：

```bash
uv sync --extra all --group dev --group docs --upgrade
uv run pytest uniqc/test
uv run pytest uniqc/test --real-cloud-test  # 周期性执行真实量子线路提交
```

`qiskit`、`qutip`、`torch`、`sphinx` 等当前维护的模块缺失表示开发环境不完整，不应作为跳过全量测试或文档构建的常规理由。`pyproject.toml` 中的第三方依赖不钉版本，主分支不提交 `uv.lock`；如当前最新依赖之间出现上游兼容性冲突，应更新适配代码并记录兼容性问题，而不是在项目依赖声明中写死旧版本。Quafu/`pyquafu` 是例外：`pyquafu` 依赖 `numpy<2` 且平台 SDK 已 deprecated，因此不包含在 `[all]` 中，后续不保证相关代码一致性和完整性。不要用 `uv sync --all-extras` 作为默认维护者命令；只有明确测试 Quafu 时才单独安装 `[quafu]`。

AI agent 运行 CLI 时推荐先打开渐进式提示：

```bash
uniqc config always-ai-hint on
```

也可以在单条命令上使用 `--ai-hints` / `--ai-hint`，或用 `UNIQC_AI_HINTS=1` 临时开启。`workflow` 是文档工作流说明页，不是 `uniqc workflow` 子命令。

真实云平台测试分为两类：读取后端列表、验证 token、查询 status/API 的测试默认执行；会实际提交量子线路的测试标记为 `real_cloud_execution`，默认跳过，只有运行 `uv run pytest uniqc/test --real-cloud-test` 时执行。不要把普通 backend discovery 测试放进 `real_cloud_execution`，core developer 环境必须让这些测试默认通过。

## 路径一：构建线路并本地模拟

```python
from uniqc import Circuit
from uniqc.simulator import OriginIR_Simulator

circuit = Circuit()
circuit.h(0)
circuit.cnot(0, 1)
circuit.measure(0)
circuit.measure(1)

sim = OriginIR_Simulator()
probabilities = sim.simulate_pmeasure(circuit.originir)
```

## 路径二：编译到目标后端

```python
from uniqc import BackendInfo, Circuit, Platform, QubitTopology, compile

backend = BackendInfo(
    platform=Platform.DUMMY,
    name="line-2",
    num_qubits=2,
    topology=(QubitTopology(0, 1),),
    is_simulator=True,
)

circuit = Circuit()
circuit.h(0)
circuit.cnot(0, 1)

compiled = compile(circuit, backend_info=backend, output_format="originir")
```

## 路径三：提交到后端或 dummy 后端

```python
from uniqc import Circuit, submit_task, wait_for_result

circuit = Circuit()
circuit.h(0)
circuit.measure(0)

# 无约束、无噪声的本地虚拟机
task_id = submit_task(circuit, backend="dummy", shots=1000)
result = wait_for_result(task_id)

# 有拓扑约束但无噪声的本地虚拟芯片
line_task = submit_task(circuit, backend="dummy:virtual-line-3", shots=1000)

# 针对真实 backend 标定数据的本地含噪仿真
noisy_task = submit_task(circuit, backend="dummy:originq:WK_C180", shots=1000)
```

dummy backend 的编号语义固定为：

- `dummy`：无约束、无噪声虚拟机，适合快速功能测试。
- `dummy:virtual-line-N`：`N` 比特线性拓扑，无噪声，例如 `dummy:virtual-line-3`。
- `dummy:virtual-grid-RxC`：`R*C` 比特网格拓扑，无噪声，例如 `dummy:virtual-grid-2x2`。
- `dummy:<platform>:<backend>`：复用指定真实 backend 的芯片拓扑和标定数据做本地含噪仿真，例如 `dummy:originq:WK_C180`。使用前需要已有 chip characterization 缓存，或在可访问云平台时由适配器拉取。

`dummy:<platform>:<backend>` 是提交规则，不是一个需要预先注册或枚举出来的 backend；它不会作为独立卡片出现在 `uniqc backend list` 或 Gateway WebUI 的 backend 列表里。提交时 UnifiedQuantum 会先按真实 backend 的拓扑和门集执行 compile/transpile，保存编译后线路，再交给本地 dummy 含噪模拟器执行。

真实后端的账号、网络、区域选择、任务缓存和结果归一化都属于 `uniqc.backend_adapter`。具体设备示例，例如 WK180，应放在 `examples/`，不应进入 `uniqc` 通用包。

## 路径四：校准、QEM 与后端格式审查

校准数据属于 `uniqc.calibration`，error mitigation 属于 `uniqc.qem`。当需要检查云平台返回的后端格式是否满足 UnifiedQuantum 的最小约定时，使用 registry audit：

```python
from uniqc import audit_backends, fetch_all_backends

backends = fetch_all_backends()
issues = audit_backends(backends)
```

`error` 表示字段不满足内部契约，`warning` 表示数据缺失或不规范但仍可能可用。

## 路径五：提交前格式校验与 gate depth 估计

任何会真正发请求的提交（`submit_task` / `submit_batch`）都先经过一次 **离线** 校验，避免无效线路打到云端再被拒：

```python
from uniqc import (
    Circuit,
    compatibility_report,
    is_compatible,
    compile_for_backend,
    compute_gate_depth,
    submit_task,
)
from uniqc.backend_adapter import find_backend

backend_info = find_backend("originq:WK_C180")  # 走本地缓存（TTL 24h）
circuit = Circuit()
circuit.h(0); circuit.cnot(0, 1)
circuit.measure(0); circuit.measure(1)

# 1) 仅查报告，不发任何请求
report = compatibility_report(circuit, backend_info)
print(report)            # CompatibilityReport(FAIL/OK) ...
report.errors            # list[str]
report.warnings          # list[str]
report.gate_depth        # int，按 virtual-Z 折算
report.used_gates        # set[str]
report.submit_language   # 'originir' / 'qasm2'

# 2) Boolean 简写
if not is_compatible(circuit, backend_info):
    raise SystemExit("circuit 与该 backend 不兼容")

# 3) 按 backend 政策自动编译后再提交
task_id = submit_task(circuit, backend="originq:WK_C180", auto_compile=True)
```

**Gate depth** 不要再用 `len(circuit.opcode_list)`：

```python
# ❌ 旧的实验代码常见错误：把 gate 数当成 depth，且没有 virtual-Z 概念
depth_wrong = len(circuit.opcode_list)

# ✅ 推荐
depth = compute_gate_depth(circuit)                  # 默认 virtual_z=True
depth_no_vz = compute_gate_depth(circuit, virtual_z=False)
```

`compute_gate_depth` 严格按物理执行 layer 计数：单/双比特门并行折叠；`Z/RZ/S/T/U1` 视为 frame change 不占深度（`virtual_z=True`）；`BARRIER` 同步不计入；`MEASURE` 不计入。详细约定见 [平台约定 §2.8](platform_conventions.md#platform-gate-depth)。

**何时绕过校验**：

- 一次性绕过：`submit_task(..., auto_compile=False)`（仍校验，失败抛 `UnsupportedGateError`）
- 完全跳过：环境变量 `UNIQC_SKIP_VALIDATION=1`（仅在你确信前端已经做过等价校验时使用，例如自定义 transpiler 已经把电路降到 backend 原生门集，再用 `uniqc` 仅作 IR adapter）
- 没有 backend 缓存时：`compatibility_report` 会以 warning 形式提示，并继续执行；建议先 `uniqc backend refresh --platform <name>` 把后端拓扑拉到本地缓存

**多平台编译政策**（由 `compile_for_backend` 与 `submit_task(..., auto_compile=True)` 自动处理）：

| 平台 | basis gate set | 提交语言 |
|------|----------------|----------|
| `originq` | `cz + sx + rz` | OriginIR |
| `quafu` | `cz + sx + rz` | QASM 2.0 |
| `quark` | `cz + sx + rz` | QASM 2.0 |
| `ibm` | `BackendInfo.extra["basis_gates"]`（来自 IBM backend） | QASM 2.0 |

如果你需要自定义 basis 进行调研：

```python
report = compatibility_report(circuit, backend_info, basis_gates=("h", "cz", "rx", "rz"))
```

## 模块边界

- `uniqc.circuit_builder`：线路构建。
- `uniqc.compile`：compile/transpile、OriginIR/OpenQASM 解析与互转。
- `uniqc.config`：项目级配置，包括 profile、云平台 token、IBM proxy、AI workflow hints 等；`uniqc.backend_adapter.config` 仅作为兼容入口保留。
- `uniqc.simulator`：本地 C++ 模拟器，无噪声和含噪声模拟。
- `uniqc.backend_adapter`：后端 adapter、配置、网络、区域选择、任务管理、dummy 后端。
- `uniqc.visualization`：线路可视化、结果可视化、timeline。
- `uniqc.utils`：期望值、结果转换等公共函数。
- `uniqc.algorithms`：通用算法组件与工作流。
- `uniqc.calibration`：从后端取得和保存校准数据。
- `uniqc.qem`：从 calibration 数据构建 error mitigator。
- `uniqc.torch_adapter`：变分量子算法与 PyTorch 的连接层。
