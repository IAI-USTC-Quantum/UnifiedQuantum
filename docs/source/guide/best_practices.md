# 推荐使用路径

UnifiedQuantum 现在按功能边界组织模块，日常代码优先从 `uniqc` 直接导入常用对象。新代码不应继续依赖 `uniqc.transpiler`、`uniqc.task`、`uniqc.qasm`、`uniqc.originir`、`uniqc.pytorch`、`uniqc.analyzer` 等旧入口。

## Maintainer 开发环境

仓库由 `uv` 管理。维护者做全量开发和全量测试时，应使用完整 extras 和 dev 依赖：

```bash
uv sync --all-extras --group dev
uv run pytest uniqc/test
```

`qiskit`、`qutip`、`pyquafu`、`torch` 等模块缺失表示开发环境不完整，不应作为跳过全量测试的常规理由。`pyproject.toml` 中的第三方依赖不钉版本；如当前最新依赖之间出现上游兼容性冲突，应更新锁文件并记录兼容性问题，而不是在项目依赖声明中写死旧版本。

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

task_id = submit_task(circuit, backend="dummy", shots=1000)
result = wait_for_result(task_id)
```

真实后端的账号、网络、区域选择、任务缓存和结果归一化都属于 `uniqc.backend_adapter`。具体设备示例，例如 WK180，应放在 `examples/`，不应进入 `uniqc` 通用包。

## 路径四：校准、QEM 与后端格式审查

校准数据属于 `uniqc.calibration`，error mitigation 属于 `uniqc.qem`。当需要检查云平台返回的后端格式是否满足 UnifiedQuantum 的最小约定时，使用 registry audit：

```python
from uniqc import audit_backends, fetch_all_backends

backends = fetch_all_backends()
issues = audit_backends(backends)
```

`error` 表示字段不满足内部契约，`warning` 表示数据缺失或不规范但仍可能可用。

## 模块边界

- `uniqc.circuit_builder`：线路构建。
- `uniqc.compile`：compile/transpile、OriginIR/OpenQASM 解析与互转。
- `uniqc.simulator`：本地 C++ 模拟器，无噪声和含噪声模拟。
- `uniqc.backend_adapter`：后端 adapter、配置、网络、区域选择、任务管理、dummy 后端。
- `uniqc.visualization`：线路可视化、结果可视化、timeline。
- `uniqc.utils`：期望值、结果转换等公共函数。
- `uniqc.algorithms`：通用算法组件与工作流。
- `uniqc.calibration`：从后端取得和保存校准数据。
- `uniqc.qem`：从 calibration 数据构建 error mitigator。
- `uniqc.torch_adapter`：变分量子算法与 PyTorch 的连接层。
