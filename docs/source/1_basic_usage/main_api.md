(guide-main-api)=
# 主要 API

本页是 **基本用法（Basic Usage）章节** 的 API 速查入口：每一行同时给出函数 / 类的 API 参考链接（左列）和它在用户文档中实际出现的章节（右列）。当你只记得函数名、想直接跳到使用说明时，从本页进入比从 [API 参考](../6_api/index.md) 树进入更快。

> 完整、按模块组织的自动生成 API 树见 [API 参考](../6_api/index.md)。

## 线路构建

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.Circuit <uniqc.circuit_builder.qcircuit.Circuit>` | [主路径走读 · 1. 构造电路](circuit-basics) · [构造电路 · 基本用法](circuit.md) |
| {py:meth}`Circuit.h <uniqc.circuit_builder.qcircuit.Circuit.h>` / {py:meth}`Circuit.x <uniqc.circuit_builder.qcircuit.Circuit.x>` / {py:meth}`Circuit.cnot <uniqc.circuit_builder.qcircuit.Circuit.cnot>` … | [构造电路 · 量子门](circuit.md) |
| {py:meth}`Circuit.measure <uniqc.circuit_builder.qcircuit.Circuit.measure>` | [构造电路 · 基本用法](circuit.md) |
| {py:meth}`Circuit.control <uniqc.circuit_builder.qcircuit.Circuit.control>` / {py:meth}`Circuit.dagger <uniqc.circuit_builder.qcircuit.Circuit.dagger>` | [构造电路 · 控制结构](circuit.md) |
| {py:meth}`Circuit.originir <uniqc.circuit_builder.qcircuit.Circuit.originir>` / {py:meth}`Circuit.qasm <uniqc.circuit_builder.qcircuit.Circuit.qasm>` | [构造电路 · 格式互转](guide-circuit-format-conversion) |
| {py:meth}`Circuit.get_matrix <uniqc.circuit_builder.qcircuit.Circuit.get_matrix>` | [构造电路 · 提取酉矩阵](guide-circuit-unitary-matrix) |
| {py:class}`uniqc.QReg <uniqc.circuit_builder.qubit.QReg>` / {py:class}`uniqc.QRegSlice <uniqc.circuit_builder.qubit.QRegSlice>` | [构造电路 · 命名量子寄存器](guide-circuit-named-qreg) |
| {py:class}`uniqc.Parameter <uniqc.circuit_builder.parameter.Parameter>` / {py:class}`uniqc.Parameters <uniqc.circuit_builder.parameter.Parameters>` | [构造电路 · 参数化电路](guide-circuit-parametric) |
| {py:class}`uniqc.NamedCircuit <uniqc.circuit_builder.named_circuit.NamedCircuit>` / {py:func}`uniqc.circuit_def <uniqc.circuit_builder.named_circuit.circuit_def>` | [构造电路 · Named Circuit](guide-circuit-named-circuit) |

## 本地模拟

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.simulator.Simulator <uniqc.simulator.simulator.Simulator>` | [本地模拟 · OriginIR 模拟器](guide-simulation-originir) · [主路径走读 · 2. 本地模拟](local-simulation) |
| {py:class}`uniqc.simulator.Simulator <uniqc.simulator.simulator.Simulator>` | [本地模拟 · QASM 模拟器](simulation.md) |
| {py:class}`uniqc.simulator.OpcodeSimulator <uniqc.simulator.opcode_simulator.OpcodeSimulator>` | [本地模拟 · Opcode 模拟器](guide-simulation-opcode) · [Opcode（进阶）](../2_advanced/opcode.md) |
| {py:class}`uniqc.simulator.NoisySimulator <uniqc.simulator.simulator.NoisySimulator>` | [本地模拟 · 带噪声的本地模拟](guide-simulation-noisy) · [噪声模拟（进阶）](../2_advanced/noise_simulation.md) |
| {py:meth}`simulate_pmeasure <uniqc.simulator.base_simulator.BaseSimulator.simulate_pmeasure>` / {py:meth}`simulate_statevector <uniqc.simulator.base_simulator.BaseSimulator.simulate_statevector>` / {py:meth}`simulate_shots <uniqc.simulator.base_simulator.BaseSimulator.simulate_shots>` | [本地模拟 · OriginIR 模拟器](guide-simulation-originir) |
| {py:func}`uniqc.simulator.create_simulator <uniqc.simulator.get_backend.create_simulator>` | [本地模拟 · 入口总览](guide-simulation-entry-overview) |
| {py:func}`uniqc.simulator.backend_alias <uniqc.simulator.opcode_simulator.backend_alias>` | [本地模拟 · 入口总览](guide-simulation-entry-overview) |
| {py:class}`MPSSimulator <uniqc.simulator.mps_simulator.MPSSimulator>` / {py:class}`MPSConfig <uniqc.simulator.mps_simulator.MPSConfig>` | [MPS 模拟器（进阶）](../2_advanced/mps_simulator.md) |
| {py:class}`TorchQuantumSimulator <uniqc.simulator.torchquantum_simulator.TorchQuantumSimulator>` | [PyTorch 集成](pytorch.md) |

## 提交任务到云平台

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.submit_task <uniqc.backend_adapter.task_manager.submit_task>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) · [提交任务 · 通用流程](guide-submit-task-flow) · [提交任务 · 完整 API 参考](guide-submit-task-api-reference) |
| {py:func}`uniqc.submit_batch <uniqc.backend_adapter.task_manager.submit_batch>` | [提交任务 · 批量提交](submit_task.md) |
| {py:func}`uniqc.dry_run_task <uniqc.backend_adapter.task_manager.dry_run_task>` | [主路径走读 · 真机提交模板](walkthrough.md) · [提交任务 · 通用流程](guide-submit-task-flow) |
| {py:func}`uniqc.wait_for_result <uniqc.backend_adapter.task_manager.wait_for_result>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) · [提交任务 · 通用流程](guide-submit-task-flow) |
| {py:func}`uniqc.query_task <uniqc.backend_adapter.task_manager.query_task>` | [提交任务 · 通用流程](guide-submit-task-flow) |
| {py:class}`uniqc.OriginQOptions <uniqc.backend_adapter.task.options.OriginQOptions>` / {py:class}`uniqc.IBMOptions <uniqc.backend_adapter.task.options.IBMOptions>` / {py:class}`uniqc.QuarkOptions <uniqc.backend_adapter.task.options.QuarkOptions>` / {py:class}`uniqc.DummyOptions <uniqc.backend_adapter.task.options.DummyOptions>` | [提交任务 · 完整 API 参考](guide-submit-task-api-reference) · [编译选项 · 类型化后端选项](../2_advanced/compiler_options_region.md) |
| {py:class}`uniqc.BackendOptions <uniqc.backend_adapter.task.options.BackendOptions>` / {py:class}`uniqc.BackendOptionsFactory <uniqc.backend_adapter.task.options.BackendOptionsFactory>` | [编译选项 · 类型化后端选项](../2_advanced/compiler_options_region.md) |
| {py:class}`uniqc.UnifiedResult <uniqc.backend_adapter.task.result_types.UnifiedResult>` | [提交任务 · 结果处理](submit_task.md) |
| {py:class}`uniqc.TaskInfo <uniqc.backend_adapter.task.store.TaskInfo>` / {py:class}`uniqc.TaskStatus <uniqc.backend_adapter.task.store.TaskStatus>` | [提交任务 · 结果处理](submit_task.md) |

## 任务管理与本地缓存

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.TaskManager <uniqc.backend_adapter.task_manager.TaskManager>` | [任务管理器 · 概述](guide-task-manager-overview) |
| {py:func}`uniqc.list_tasks <uniqc.backend_adapter.task_manager.list_tasks>` / {py:func}`uniqc.get_task <uniqc.backend_adapter.task_manager.get_task>` | [任务管理器 · 任务管理](guide-task-manager-core-api) |
| {py:func}`uniqc.clear_completed_tasks <uniqc.backend_adapter.task_manager.clear_completed_tasks>` / {py:func}`uniqc.clear_cache <uniqc.backend_adapter.task_manager.clear_cache>` | [任务管理器 · 任务管理](guide-task-manager-core-api) |

## 后端发现

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.list_backends <uniqc.backend_adapter.backend.list_backends>` / {py:func}`uniqc.find_backend <uniqc.backend_adapter.backend_registry.find_backend>` / {py:func}`uniqc.fetch_all_backends <uniqc.backend_adapter.backend_registry.fetch_all_backends>` | [`uniqc backend`](../4_cli/backend.md) · [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:func}`uniqc.get_backend <uniqc.backend_adapter.backend.get_backend>` | [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:class}`uniqc.BackendInfo <uniqc.backend_adapter.backend_info.BackendInfo>` | [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:class}`uniqc.DummyBackend <uniqc.backend_adapter.backend.DummyBackend>` | [平台约定 · DummyBackend](platform-dummy-backend) · [Dummy 系统（进阶）](../2_advanced/index.md) |
| {py:class}`uniqc.OriginQBackend <uniqc.backend_adapter.backend.OriginQBackend>` / {py:class}`uniqc.IBMBackend <uniqc.backend_adapter.backend.IBMBackend>` / {py:class}`uniqc.QuarkBackend <uniqc.backend_adapter.backend.QuarkBackend>` | [平台约定 · 统一后端工厂](platform-get-backend) |

## 编译与区域选择

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.compile` / {py:func}`uniqc.compile_for_backend <uniqc.compile.policy.compile_for_backend>` | [编译选项（进阶）](../2_advanced/compiler_options_region.md) · [编译强度](../2_advanced/compile_levels.md) |
| `local_compile` / `cloud_compile`（提交时 kwarg） | [编译强度](../2_advanced/compile_levels.md) |
| {py:class}`uniqc.RegionSelector <uniqc.backend_adapter.region_selector.RegionSelector>` / {py:class}`uniqc.RegionSearchResult <uniqc.backend_adapter.region_selector.RegionSearchResult>` / {py:class}`uniqc.ChainSearchResult <uniqc.backend_adapter.region_selector.ChainSearchResult>` | [编译选项 · 区域选择器](../2_advanced/compiler_options_region.md) |
| {py:class}`uniqc.TranspilerConfig <uniqc.compile.compiler.TranspilerConfig>` | [编译选项（进阶）](../2_advanced/compiler_options_region.md) |
| {py:class}`uniqc.QubitTopology <uniqc.backend_adapter.backend_info.QubitTopology>` / {py:class}`uniqc.Qubit <uniqc.circuit_builder.qubit.Qubit>` | [构造电路 · 命名量子寄存器](guide-circuit-named-qreg) · [平台约定 · DummyBackend](platform-dummy-backend) |

## 后处理 / 结果分析

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.calculate_expectation <uniqc.utils.expectation.calculate_expectation>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) |
| {py:func}`uniqc.shots2prob <uniqc.utils.result_adapter.shots2prob>` / {py:func}`uniqc.kv2list <uniqc.utils.result_adapter.kv2list>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) |

## 校准与读出误差缓解

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.ReadoutEM <uniqc.qem.readout_em.ReadoutEM>` | [校准（进阶） · 统一读出误差缓解 ReadoutEM](../2_advanced/calibration.md) |
| {py:class}`uniqc.M3Mitigator <uniqc.qem.m3.M3Mitigator>` | [校准（进阶） · M3 读出误差缓解](../2_advanced/calibration.md) |
| {py:class}`uniqc.ReadoutCalibrationResult <uniqc.calibration.results.ReadoutCalibrationResult>` | [校准（进阶） · 读出误差校准](../2_advanced/calibration.md) |
| {py:class}`uniqc.XEBResult <uniqc.calibration.results.XEBResult>` | [校准（进阶） · XEB 交叉熵基准测试](../2_advanced/calibration.md) |

## PyTorch 集成

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:mod}`uniqc.torch_adapter` | [PyTorch 集成](pytorch.md) |
| {py:class}`uniqc.QuantumLayer <uniqc.torch_adapter.quantum_layer.QuantumLayer>` / {py:class}`uniqc.TorchQuantumLayer <uniqc.torch_adapter.tq_quantum_layer.TorchQuantumLayer>` | [PyTorch · QuantumLayer](pytorch.md) |
| {py:func}`uniqc.torch_adapter.parameter_shift_gradient <uniqc.torch_adapter.gradient.parameter_shift_gradient>` | [PyTorch · Parameter-Shift 梯度](pytorch.md) |
| {py:func}`uniqc.torch_adapter.batch_execute <uniqc.torch_adapter.batch_executor.batch_execute>` / {py:func}`uniqc.torch_adapter.batch_execute_with_params <uniqc.torch_adapter.batch_executor.batch_execute_with_params>` | [PyTorch · 批量执行](pytorch.md) |
| {py:func}`uniqc.torch_adapter.compute_all_gradients <uniqc.torch_adapter.gradient.compute_all_gradients>` | [PyTorch · 多参数电路](pytorch.md) |

## 格式互转与解析

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:mod}`uniqc.compile.originir` | [OriginIR · Python API 参考](originir.md) |
| {py:class}`uniqc.OriginIR_BaseParser <uniqc.compile.originir.originir_base_parser.OriginIR_BaseParser>` | [OriginIR · Python API 参考](originir.md) |
| {py:class}`uniqc.OpenQASM2_BaseParser <uniqc.compile.qasm.qasm_base_parser.OpenQASM2_BaseParser>` / {py:mod}`uniqc.compile.qasm` | [QASM · 格式互转操作](qasm.md) |
| {py:meth}`Circuit.from_originir <uniqc.circuit_builder.qcircuit.Circuit.from_originir>` / {py:meth}`Circuit.from_qasm <uniqc.circuit_builder.qcircuit.Circuit.from_qasm>` | [构造电路 · 格式互转](guide-circuit-format-conversion) · [QASM · 格式互转操作](qasm.md) |

## 可视化

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.plot_time_line <uniqc.visualization.timeline.plot_time_line>` | [主路径走读 · 5. 可视化](visualize) · [编译选项 · API 速查](../2_advanced/compiler_options_region.md) |
| {py:func}`uniqc.circuit_to_html <uniqc.visualization.timeline.circuit_to_html>` | [主路径走读 · 5. 可视化](visualize) |
| {py:meth}`Circuit.draw <uniqc.circuit_builder.qcircuit.Circuit.draw>` / {py:func}`uniqc.visualization.render <uniqc.visualization.circuit_render.render>` | [构造电路 · 可视化](circuit.md) · [线路分析](../2_advanced/circuit_analysis.md) |
| {py:func}`uniqc.compile.compute_gate_depth <uniqc.compile.validation.compute_gate_depth>` | [构造电路 · 线路信息](circuit.md) |

## 异常类型

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.UnifiedQuantumError <uniqc.exceptions.UnifiedQuantumError>`（基类） | [提交任务 · 平台边界与限制](submit_task.md) |
| {py:class}`uniqc.AuthenticationError <uniqc.exceptions.AuthenticationError>` / {py:class}`uniqc.NetworkError <uniqc.exceptions.NetworkError>` / {py:class}`uniqc.QuotaExceededError <uniqc.exceptions.QuotaExceededError>` / {py:class}`uniqc.InsufficientCreditsError <uniqc.exceptions.InsufficientCreditsError>` | [任务管理器 · 错误处理](guide-task-manager-error-handling) |
| {py:class}`uniqc.TaskFailedError <uniqc.exceptions.TaskFailedError>` / {py:class}`uniqc.TaskNotFoundError <uniqc.exceptions.TaskNotFoundError>` / {py:class}`uniqc.TaskTimeoutError <uniqc.exceptions.TaskTimeoutError>` | [任务管理器 · 错误处理](guide-task-manager-error-handling) |
| {py:class}`uniqc.BackendError <uniqc.exceptions.BackendError>` / {py:class}`uniqc.BackendNotFoundError <uniqc.exceptions.BackendNotFoundError>` / {py:class}`uniqc.BackendNotAvailableError <uniqc.exceptions.BackendNotAvailableError>` / {py:class}`uniqc.BackendOptionsError <uniqc.exceptions.BackendOptionsError>` | [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:class}`uniqc.CircuitError <uniqc.exceptions.CircuitError>` / {py:class}`uniqc.NotSupportedGateError <uniqc.exceptions.NotSupportedGateError>` / {py:class}`uniqc.UnsupportedGateError <uniqc.exceptions.UnsupportedGateError>` / {py:class}`uniqc.CircuitTranslationError <uniqc.exceptions.CircuitTranslationError>` | [构造电路 · 量子门](circuit.md) · [QASM · 格式互转](qasm.md) |
| {py:class}`uniqc.CompilationFailedError <uniqc.exceptions.CompilationFailedError>` / {py:class}`uniqc.CompilationResult <uniqc.compile.compiler.CompilationResult>` / {py:class}`uniqc.CompatibilityReport <uniqc.compile.validation.CompatibilityReport>` | [编译选项（进阶）](../2_advanced/compiler_options_region.md) · [编译强度](../2_advanced/compile_levels.md) |
| {py:class}`uniqc.ConfigError <uniqc.exceptions.ConfigError>` / {py:class}`uniqc.ConfigValidationError <uniqc.exceptions.ConfigValidationError>` / {py:class}`uniqc.ProfileNotFoundError <uniqc.exceptions.ProfileNotFoundError>` / {py:class}`uniqc.PlatformNotFoundError <uniqc.exceptions.PlatformNotFoundError>` | [平台约定 · 配置约定](platform-configuration) |
| {py:class}`uniqc.RegisterDefinitionError <uniqc.exceptions.RegisterDefinitionError>` / {py:class}`uniqc.RegisterNotFoundError <uniqc.exceptions.RegisterNotFoundError>` / {py:class}`uniqc.RegisterOutOfRangeError <uniqc.exceptions.RegisterOutOfRangeError>` | [构造电路 · 命名量子寄存器](guide-circuit-named-qreg) |
| {py:class}`uniqc.StaleCalibrationError <uniqc.exceptions.StaleCalibrationError>` | [校准（进阶） · 缓存管理](../2_advanced/calibration.md) |
| {py:class}`uniqc.TopologyError <uniqc.exceptions.TopologyError>` / {py:class}`uniqc.TimelineDurationError <uniqc.exceptions.TimelineDurationError>` / {py:class}`uniqc.NotMatrixableError <uniqc.exceptions.NotMatrixableError>` / {py:class}`uniqc.MissingDependencyError <uniqc.exceptions.MissingDependencyError>` | [构造电路 · 提取酉矩阵](guide-circuit-unitary-matrix) · [平台约定 · DummyBackend](platform-dummy-backend) |
