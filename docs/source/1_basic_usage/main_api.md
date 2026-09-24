(guide-main-api)=
# 主要 API

本页是 **基本用法（Basic Usage）章节** 的 API 速查入口：每一行同时给出函数 / 类的 API 参考链接（左列）和它在用户文档中实际出现的章节（右列）。当你只记得函数名、想直接跳到使用说明时，从本页进入比从 [API 参考](../6_api/index.md) 树进入更快。

> 完整、按模块组织的自动生成 API 树见 [API 参考](../6_api/index.md)。

## 线路构建

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`Circuit <uniqc.circuit_builder.qcircuit.Circuit>` | [主路径走读 · 1. 构造电路](circuit-basics) · [构造电路 · 基本用法](circuit.md) |
| {py:meth}`Circuit.h <uniqc.circuit_builder.qcircuit.Circuit.h>` / {py:meth}`Circuit.x <uniqc.circuit_builder.qcircuit.Circuit.x>` / {py:meth}`Circuit.cnot <uniqc.circuit_builder.qcircuit.Circuit.cnot>` … | [构造电路 · 量子门](circuit.md) |
| {py:meth}`Circuit.measure <uniqc.circuit_builder.qcircuit.Circuit.measure>` | [构造电路 · 基本用法](circuit.md) |
| {py:meth}`Circuit.control <uniqc.circuit_builder.qcircuit.Circuit.control>` / {py:meth}`Circuit.dagger <uniqc.circuit_builder.qcircuit.Circuit.dagger>` | [构造电路 · 控制结构](circuit.md) |
| {py:attr}`Circuit.originir <uniqc.circuit_builder.qcircuit.Circuit.originir>` / {py:attr}`Circuit.qasm <uniqc.circuit_builder.qcircuit.Circuit.qasm>` | [构造电路 · 格式互转](guide-circuit-format-conversion) |
| {py:meth}`Circuit.to_matrix <uniqc.circuit_builder.qcircuit.Circuit.to_matrix>` | [构造电路 · 提取酉矩阵](guide-circuit-unitary-matrix) |
| {py:class}`QReg <uniqc.circuit_builder.qubit.QReg>` / {py:class}`QRegSlice <uniqc.circuit_builder.qubit.QRegSlice>` | [构造电路 · 命名量子寄存器](guide-circuit-named-qreg) |
| {py:class}`Parameter <uniqc.circuit_builder.parameter.Parameter>` / {py:class}`Parameters <uniqc.circuit_builder.parameter.Parameters>` | [构造电路 · 参数化电路](guide-circuit-parametric) |
| {py:class}`NamedCircuit <uniqc.circuit_builder.named_circuit.NamedCircuit>` / {py:func}`circuit_def() <uniqc.circuit_builder.named_circuit.circuit_def>` | [构造电路 · Named Circuit](guide-circuit-named-circuit) |

## 本地模拟

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`Simulator <uniqc.simulator.simulator.Simulator>` | [本地模拟 · OriginIR 模拟器](guide-simulation-originir) · [主路径走读 · 2. 本地模拟](local-simulation) |
| {py:class}`Simulator <uniqc.simulator.simulator.Simulator>` | [本地模拟 · QASM 模拟器](simulation.md) |
| {py:class}`OpcodeSimulator <uniqc.simulator.opcode_simulator.OpcodeSimulator>` | [本地模拟 · Opcode 模拟器](guide-simulation-opcode) · [Opcode（进阶）](../2_advanced/opcode.md) |
| {py:class}`NoisySimulator <uniqc.simulator.simulator.NoisySimulator>` | [本地模拟 · 带噪声的本地模拟](guide-simulation-noisy) · [噪声模拟（进阶）](../2_advanced/noise_simulation.md) |
| {py:meth}`simulate_pmeasure() <uniqc.simulator.base_simulator.BaseSimulator.simulate_pmeasure>` / {py:meth}`simulate_statevector() <uniqc.simulator.base_simulator.BaseSimulator.simulate_statevector>` / {py:meth}`simulate_shots() <uniqc.simulator.base_simulator.BaseSimulator.simulate_shots>` | [本地模拟 · OriginIR 模拟器](guide-simulation-originir) |
| {py:func}`create_simulator() <uniqc.simulator.get_backend.create_simulator>` | [本地模拟 · 入口总览](guide-simulation-entry-overview) |
| {py:func}`backend_alias() <uniqc.simulator.opcode_simulator.backend_alias>` | [本地模拟 · 入口总览](guide-simulation-entry-overview) |
| {py:class}`MPSSimulator <uniqc.simulator.mps_simulator.MPSSimulator>` / {py:class}`MPSConfig <uniqc.simulator.mps_simulator.MPSConfig>` | [MPS 模拟器（进阶）](../2_advanced/mps_simulator.md) |
| {py:class}`TorchQuantumSimulator <uniqc.simulator.torchquantum_simulator.TorchQuantumSimulator>` | [PyTorch 集成](pytorch.md) |

## 提交任务到云平台

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`submit_task() <uniqc.backend_adapter.task_manager.submit_task>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) · [提交任务 · 通用流程](guide-submit-task-flow) · [提交任务 · 完整 API 参考](guide-submit-task-api-reference) |
| {py:func}`submit_batch() <uniqc.backend_adapter.task_manager.submit_batch>` | [提交任务 · 批量提交](submit_task.md) |
| {py:func}`dry_run_task() <uniqc.backend_adapter.task_manager.dry_run_task>` | [主路径走读 · 真机提交模板](walkthrough.md) · [提交任务 · 通用流程](guide-submit-task-flow) |
| {py:func}`wait_for_result() <uniqc.backend_adapter.task_manager.wait_for_result>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) · [提交任务 · 通用流程](guide-submit-task-flow) |
| {py:func}`query_task() <uniqc.backend_adapter.task_manager.query_task>` | [提交任务 · 通用流程](guide-submit-task-flow) |
| {py:class}`OriginQOptions <uniqc.backend_adapter.task.options.OriginQOptions>` / {py:class}`IBMOptions <uniqc.backend_adapter.task.options.IBMOptions>` / {py:class}`QuarkOptions <uniqc.backend_adapter.task.options.QuarkOptions>` / {py:class}`DummyOptions <uniqc.backend_adapter.task.options.DummyOptions>` | [提交任务 · 完整 API 参考](guide-submit-task-api-reference) · [编译选项 · 类型化后端选项](../2_advanced/compiler_options_region.md) |
| {py:class}`BackendOptions <uniqc.backend_adapter.task.options.BackendOptions>` / {py:class}`BackendOptionsFactory <uniqc.backend_adapter.task.options.BackendOptionsFactory>` | [编译选项 · 类型化后端选项](../2_advanced/compiler_options_region.md) |
| {py:class}`UnifiedResult <uniqc.backend_adapter.task.result_types.UnifiedResult>` | [提交任务 · 结果处理](submit_task.md) |
| {py:class}`TaskInfo <uniqc.backend_adapter.task.store.TaskInfo>` / {py:class}`TaskStatus <uniqc.backend_adapter.task.store.TaskStatus>` | [提交任务 · 结果处理](submit_task.md) |

## 任务管理与本地缓存

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`TaskManager <uniqc.backend_adapter.task_manager.TaskManager>` | [任务管理器 · 概述](guide-task-manager-overview) |
| {py:func}`list_tasks() <uniqc.backend_adapter.task_manager.list_tasks>` / {py:func}`get_task() <uniqc.backend_adapter.task_manager.get_task>` | [任务管理器 · 任务管理](guide-task-manager-core-api) |
| {py:func}`clear_completed_tasks() <uniqc.backend_adapter.task_manager.clear_completed_tasks>` / {py:func}`clear_cache() <uniqc.backend_adapter.task_manager.clear_cache>` | [任务管理器 · 任务管理](guide-task-manager-core-api) |

## 后端发现

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`list_backends() <uniqc.backend_adapter.backend.list_backends>` / {py:func}`find_backend() <uniqc.backend_adapter.backend_registry.find_backend>` / {py:func}`fetch_all_backends() <uniqc.backend_adapter.backend_registry.fetch_all_backends>` | [`uniqc backend`](../4_cli/backend.md) · [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:func}`get_backend() <uniqc.backend_adapter.backend.get_backend>` | [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:class}`BackendInfo <uniqc.backend_adapter.backend_info.BackendInfo>` | [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:class}`DummyBackend <uniqc.backend_adapter.backend.DummyBackend>` | [平台约定 · DummyBackend](platform-dummy-backend) · [Dummy 系统（进阶）](../2_advanced/index.md) |
| {py:class}`OriginQBackend <uniqc.backend_adapter.backend.OriginQBackend>` / {py:class}`IBMBackend <uniqc.backend_adapter.backend.IBMBackend>` / {py:class}`QuarkBackend <uniqc.backend_adapter.backend.QuarkBackend>` | [平台约定 · 统一后端工厂](platform-get-backend) |

## 编译与区域选择

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`compile() <uniqc.compile.compiler.compile>` / {py:func}`compile_for_backend() <uniqc.compile.policy.compile_for_backend>` | [编译选项（进阶）](../2_advanced/compiler_options_region.md) · [编译强度](../2_advanced/compile_levels.md) |
| `local_compile` / `cloud_compile`（提交时 kwarg） | [编译强度](../2_advanced/compile_levels.md) |
| {py:class}`RegionSelector <uniqc.backend_adapter.region_selector.RegionSelector>` / {py:class}`RegionSearchResult <uniqc.backend_adapter.region_selector.RegionSearchResult>` / {py:class}`ChainSearchResult <uniqc.backend_adapter.region_selector.ChainSearchResult>` | [编译选项 · 区域选择器](../2_advanced/compiler_options_region.md) |
| {py:class}`TranspilerConfig <uniqc.compile.compiler.TranspilerConfig>` | [编译选项（进阶）](../2_advanced/compiler_options_region.md) |
| {py:class}`QubitTopology <uniqc.backend_adapter.backend_info.QubitTopology>` / {py:class}`Qubit <uniqc.circuit_builder.qubit.Qubit>` | [构造电路 · 命名量子寄存器](guide-circuit-named-qreg) · [平台约定 · DummyBackend](platform-dummy-backend) |

## 后处理 / 结果分析

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`calculate_expectation() <uniqc.utils.expectation.calculate_expectation>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) |
| {py:func}`shots2prob() <uniqc.utils.result_adapter.shots2prob>` / {py:func}`kv2list() <uniqc.utils.result_adapter.kv2list>` | [主路径走读 · 3. 提交与后处理](submit-postprocess) |

## 校准与读出误差缓解

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`ReadoutEM <uniqc.qem.readout_em.ReadoutEM>` | [校准（进阶） · 统一读出误差缓解 ReadoutEM](../2_advanced/calibration.md) |
| {py:class}`M3Mitigator <uniqc.qem.m3.M3Mitigator>` | [校准（进阶） · M3 读出误差缓解](../2_advanced/calibration.md) |
| {py:class}`ReadoutCalibrationResult <uniqc.calibration.results.ReadoutCalibrationResult>` | [校准（进阶） · 读出误差校准](../2_advanced/calibration.md) |
| {py:class}`XEBResult <uniqc.calibration.results.XEBResult>` | [校准（进阶） · XEB 交叉熵基准测试](../2_advanced/calibration.md) |

## PyTorch 集成

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:mod}`uniqc.torch_adapter` | [PyTorch 集成](pytorch.md) |
| {py:class}`QuantumLayer <uniqc.torch_adapter.quantum_layer.QuantumLayer>` / {py:class}`TorchQuantumLayer <uniqc.torch_adapter.tq_quantum_layer.TorchQuantumLayer>` | [PyTorch · QuantumLayer](pytorch.md) |
| {py:func}`parameter_shift_gradient() <uniqc.torch_adapter.gradient.parameter_shift_gradient>` | [PyTorch · Parameter-Shift 梯度](pytorch.md) |
| {py:func}`batch_execute() <uniqc.torch_adapter.batch_executor.batch_execute>` / {py:func}`batch_execute_with_params() <uniqc.torch_adapter.batch_executor.batch_execute_with_params>` | [PyTorch · 批量执行](pytorch.md) |
| {py:func}`compute_all_gradients() <uniqc.torch_adapter.gradient.compute_all_gradients>` | [PyTorch · 多参数电路](pytorch.md) |

## 格式互转与解析

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:mod}`uniqc.compile.originir` | [OriginIR · Python API 参考](originir.md) |
| {py:class}`OriginIR_BaseParser <uniqc.compile.originir.originir_base_parser.OriginIR_BaseParser>` | [OriginIR · Python API 参考](originir.md) |
| {py:class}`OpenQASM2_BaseParser <uniqc.compile.qasm.qasm_base_parser.OpenQASM2_BaseParser>` / {py:mod}`uniqc.compile.qasm` | [QASM · 格式互转操作](qasm.md) |
| {py:meth}`Circuit.from_originir() <uniqc.circuit_builder.qcircuit.Circuit.from_originir>` / {py:meth}`Circuit.from_qasm() <uniqc.circuit_builder.qcircuit.Circuit.from_qasm>` | [构造电路 · 格式互转](guide-circuit-format-conversion) · [QASM · 格式互转操作](qasm.md) |

## 可视化

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`plot_time_line() <uniqc.visualization.timeline.plot_time_line>` | [主路径走读 · 5. 可视化](visualize) · [编译选项 · API 速查](../2_advanced/compiler_options_region.md) |
| {py:func}`circuit_to_html() <uniqc.visualization.timeline.circuit_to_html>` | [主路径走读 · 5. 可视化](visualize) |
| {py:meth}`Circuit.draw() <uniqc.circuit_builder.qcircuit.Circuit.draw>` / {py:func}`render() <uniqc.visualization.circuit_render.render>` | [构造电路 · 可视化](circuit.md) · [线路分析](../2_advanced/circuit_analysis.md) |
| {py:func}`compute_gate_depth() <uniqc.compile.validation.compute_gate_depth>` | [构造电路 · 线路信息](circuit.md) |

## 异常类型

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`UnifiedQuantumError <uniqc.exceptions.UnifiedQuantumError>`（基类，其余异常见 {py:mod}`uniqc.exceptions`） | [提交任务 · 平台边界与限制](submit_task.md) |
| {py:class}`AuthenticationError <uniqc.exceptions.AuthenticationError>` / {py:class}`NetworkError <uniqc.exceptions.NetworkError>` / {py:class}`QuotaExceededError <uniqc.exceptions.QuotaExceededError>` / {py:class}`InsufficientCreditsError <uniqc.exceptions.InsufficientCreditsError>` | [任务管理器 · 错误处理](guide-task-manager-error-handling) |
| {py:class}`TaskFailedError <uniqc.exceptions.TaskFailedError>` / {py:class}`TaskNotFoundError <uniqc.exceptions.TaskNotFoundError>` / {py:class}`TaskTimeoutError <uniqc.exceptions.TaskTimeoutError>` | [任务管理器 · 错误处理](guide-task-manager-error-handling) |
| {py:class}`BackendError <uniqc.exceptions.BackendError>` / {py:class}`BackendNotFoundError <uniqc.exceptions.BackendNotFoundError>` / {py:class}`BackendNotAvailableError <uniqc.exceptions.BackendNotAvailableError>` / {py:class}`BackendOptionsError <uniqc.exceptions.BackendOptionsError>` | [平台约定 · 统一后端工厂](platform-get-backend) |
| {py:class}`CircuitError <uniqc.exceptions.CircuitError>` / {py:class}`NotSupportedGateError <uniqc.exceptions.NotSupportedGateError>` / {py:class}`UnsupportedGateError <uniqc.exceptions.UnsupportedGateError>` / {py:class}`CircuitTranslationError <uniqc.exceptions.CircuitTranslationError>` | [构造电路 · 量子门](circuit.md) · [QASM · 格式互转](qasm.md) |
| {py:class}`CompilationFailedError <uniqc.exceptions.CompilationFailedError>` / {py:class}`CompilationResult <uniqc.compile.compiler.CompilationResult>` / {py:class}`CompatibilityReport <uniqc.compile.validation.CompatibilityReport>` | [编译选项（进阶）](../2_advanced/compiler_options_region.md) · [编译强度](../2_advanced/compile_levels.md) |
| {py:class}`ConfigError <uniqc.exceptions.ConfigError>` / {py:class}`ConfigValidationError <uniqc.exceptions.ConfigValidationError>` / {py:class}`ProfileNotFoundError <uniqc.exceptions.ProfileNotFoundError>` / {py:class}`PlatformNotFoundError <uniqc.exceptions.PlatformNotFoundError>` | [平台约定 · 配置约定](platform-configuration) |
| {py:class}`RegisterDefinitionError <uniqc.exceptions.RegisterDefinitionError>` / {py:class}`RegisterNotFoundError <uniqc.exceptions.RegisterNotFoundError>` / {py:class}`RegisterOutOfRangeError <uniqc.exceptions.RegisterOutOfRangeError>` | [构造电路 · 命名量子寄存器](guide-circuit-named-qreg) |
| {py:class}`StaleCalibrationError <uniqc.exceptions.StaleCalibrationError>` | [校准（进阶） · 缓存管理](../2_advanced/calibration.md) |
| {py:class}`TopologyError <uniqc.exceptions.TopologyError>` / {py:class}`TimelineDurationError <uniqc.exceptions.TimelineDurationError>` / {py:class}`NotMatrixableError <uniqc.exceptions.NotMatrixableError>` / {py:class}`MissingDependencyError <uniqc.exceptions.MissingDependencyError>` | [构造电路 · 提取酉矩阵](guide-circuit-unitary-matrix) · [平台约定 · DummyBackend](platform-dummy-backend) |
