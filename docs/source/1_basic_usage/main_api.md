# 主要 API {#guide-main-api}

本页是 **基本用法（Basic Usage）章节** 的 API 速查入口：每一行同时给出函数 / 类的 API 参考链接（左列）和它在用户文档中实际出现的章节（右列）。当你只记得函数名、想直接跳到使用说明时，从本页进入比从 [API 参考](../6_api/index.md) 树进入更快。

> 完整、按模块组织的自动生成 API 树见 [API 参考](../6_api/index.md)。

## 线路构建

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.Circuit` | [主路径走读 · 1. 构造电路](walkthrough.md#circuit-basics) · [构造电路 · 基本用法](circuit.md#基本用法) |
| `Circuit.h` / `Circuit.x` / `Circuit.cnot` … | [构造电路 · 量子门](circuit.md#量子门) |
| `Circuit.measure` | [构造电路 · 基本用法](circuit.md#基本用法) |
| `Circuit.control` / `Circuit.dagger` | [构造电路 · 控制结构](circuit.md#控制结构) |
| `Circuit.originir` / `Circuit.qasm` | [构造电路 · 格式互转](circuit.md#guide-circuit-format-conversion) |
| `Circuit.unitary` | [构造电路 · 提取酉矩阵](circuit.md#guide-circuit-unitary-matrix) |
| {py:class}`uniqc.QReg` / {py:class}`uniqc.QRegSlice` | [构造电路 · 命名量子寄存器](circuit.md#guide-circuit-named-qreg) |
| {py:class}`uniqc.Parameter` / {py:class}`uniqc.Parameters` | [构造电路 · 参数化电路](circuit.md#guide-circuit-parametric) |
| {py:class}`uniqc.NamedCircuit` / {py:func}`uniqc.circuit_def` | [构造电路 · Named Circuit](circuit.md#guide-circuit-named-circuit) |

## 本地模拟

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.simulator.OriginIR_Simulator` | [本地模拟 · OriginIR 模拟器](simulation.md#guide-simulation-originir) · [主路径走读 · 2. 本地模拟](walkthrough.md#local-simulation) |
| {py:class}`uniqc.simulator.QASM_Simulator` | [本地模拟 · QASM 模拟器](simulation.md#guide-simulation-qasm) |
| {py:class}`uniqc.simulator.OpcodeSimulator` | [本地模拟 · Opcode 模拟器](simulation.md#guide-simulation-opcode) · [Opcode（进阶）](../2_advanced/opcode.md) |
| {py:class}`uniqc.simulator.OriginIR_NoisySimulator` | [本地模拟 · 带噪声的本地模拟](simulation.md#guide-simulation-noisy) · [噪声模拟（进阶）](../2_advanced/noise_simulation.md) |
| `simulate_pmeasure` / `simulate_statevector` / `simulate_shots` | [本地模拟 · OriginIR 模拟器](simulation.md#guide-simulation-originir) |
| {py:func}`uniqc.simulator.create_simulator` | [本地模拟 · 入口总览](simulation.md#guide-simulation-entry-overview) |
| {py:func}`uniqc.simulator.backend_alias` | [本地模拟 · 入口总览](simulation.md#guide-simulation-entry-overview) |
| `MPSSimulator` / `MPSConfig` | [MPS 模拟器（进阶）](../2_advanced/mps_simulator.md) |
| `TorchQuantumSimulator` | [PyTorch 集成](pytorch.md) |

## 提交任务到云平台

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.submit_task` | [主路径走读 · 3. 提交与后处理](walkthrough.md#submit-postprocess) · [提交任务 · 通用流程](submit_task.md#guide-submit-task-flow) · [提交任务 · 完整 API 参考](submit_task.md#guide-submit-task-api-reference) |
| {py:func}`uniqc.submit_batch` | [提交任务 · 批量提交](submit_task.md#批量提交) |
| {py:func}`uniqc.dry_run_task` | [主路径走读 · 真机提交模板](walkthrough.md#真机提交模板) · [提交任务 · 通用流程](submit_task.md#guide-submit-task-flow) |
| {py:func}`uniqc.wait_for_result` | [主路径走读 · 3. 提交与后处理](walkthrough.md#submit-postprocess) · [提交任务 · 通用流程](submit_task.md#guide-submit-task-flow) |
| {py:func}`uniqc.query_task` | [提交任务 · 通用流程](submit_task.md#guide-submit-task-flow) |
| {py:class}`uniqc.OriginQOptions` / {py:class}`uniqc.QuafuOptions` / {py:class}`uniqc.IBMOptions` / {py:class}`uniqc.QuarkOptions` / {py:class}`uniqc.DummyOptions` | [提交任务 · 完整 API 参考](submit_task.md#guide-submit-task-api-reference) · [编译选项 · 类型化后端选项](../2_advanced/compiler_options_region.md#2-类型化后端选项-backendoptions) |
| {py:class}`uniqc.BackendOptions` / {py:class}`uniqc.BackendOptionsFactory` | [编译选项 · 类型化后端选项](../2_advanced/compiler_options_region.md#2-类型化后端选项-backendoptions) |
| {py:class}`uniqc.UnifiedResult` | [提交任务 · 结果处理](submit_task.md#结果处理) |
| {py:class}`uniqc.TaskInfo` / {py:class}`uniqc.TaskStatus` | [提交任务 · 结果处理](submit_task.md#结果处理) |

## 任务管理与本地缓存

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.TaskManager` | [任务管理器 · 概述](task_manager.md#guide-task-manager-overview) |
| {py:func}`uniqc.list_tasks` / {py:func}`uniqc.get_task` | [任务管理器 · 任务管理](task_manager.md#guide-task-manager-core-api) |
| {py:func}`uniqc.clear_completed_tasks` / {py:func}`uniqc.clear_cache` | [任务管理器 · 任务管理](task_manager.md#guide-task-manager-core-api) |

## 后端发现

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.list_backends` / {py:func}`uniqc.find_backend` / {py:func}`uniqc.fetch_all_backends` | [`uniqc backend`](../4_cli/backend.md) · [平台约定 · 统一后端工厂](platform_conventions.md#platform-get-backend) |
| {py:func}`uniqc.get_backend` | [平台约定 · 统一后端工厂](platform_conventions.md#platform-get-backend) |
| {py:class}`uniqc.BackendInfo` | [平台约定 · 统一后端工厂](platform_conventions.md#platform-get-backend) |
| {py:class}`uniqc.DummyBackend` | [平台约定 · DummyBackend](platform_conventions.md#platform-dummy-backend) · [Dummy 系统（进阶）](../2_advanced/index.md#_4-dummy-_-noiseless-_-virtual-topology-_-chip-noise) |
| {py:class}`uniqc.OriginQBackend` / {py:class}`uniqc.QuafuBackend` / {py:class}`uniqc.IBMBackend` / {py:class}`uniqc.QuarkBackend` | [平台约定 · 统一后端工厂](platform_conventions.md#platform-get-backend) |

## 编译与区域选择

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.compile` / {py:func}`uniqc.compile_for_backend` | [编译选项（进阶）](../2_advanced/compiler_options_region.md#1-增强编译compile-函数) · [编译强度](../2_advanced/compile_levels.md) |
| `local_compile` / `cloud_compile`（提交时 kwarg） | [编译强度](../2_advanced/compile_levels.md) |
| {py:class}`uniqc.RegionSelector` / {py:class}`uniqc.RegionSearchResult` / {py:class}`uniqc.ChainSearchResult` | [编译选项 · 区域选择器](../2_advanced/compiler_options_region.md#3-区域选择器regionselector) |
| {py:class}`uniqc.TranspilerConfig` | [编译选项（进阶）](../2_advanced/compiler_options_region.md#1-增强编译compile-函数) |
| {py:class}`uniqc.QubitTopology` / {py:class}`uniqc.Qubit` | [构造电路 · 命名量子寄存器](circuit.md#guide-circuit-named-qreg) · [平台约定 · DummyBackend](platform_conventions.md#platform-dummy-backend) |

## 后处理 / 结果分析

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.calculate_expectation` | [主路径走读 · 3. 提交与后处理](walkthrough.md#submit-postprocess) |
| {py:func}`uniqc.shots2prob` / {py:func}`uniqc.kv2list` | [主路径走读 · 3. 提交与后处理](walkthrough.md#submit-postprocess) |

## 校准与读出误差缓解

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.ReadoutEM` | [校准（进阶） · 统一读出误差缓解 ReadoutEM](../2_advanced/calibration.md#3-统一读出误差缓解readoutem) |
| {py:class}`uniqc.M3Mitigator` | [校准（进阶） · M3 读出误差缓解](../2_advanced/calibration.md#2-m3-读出误差缓解m3-mitigator) |
| {py:class}`uniqc.ReadoutCalibrationResult` | [校准（进阶） · 读出误差校准](../2_advanced/calibration.md#1-读出误差校准readout-calibration) |
| {py:class}`uniqc.XEBResult` | [校准（进阶） · XEB 交叉熵基准测试](../2_advanced/calibration.md#4-xeb-交叉熵基准测试) |

## PyTorch 集成

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:mod}`uniqc.torch_adapter` | [PyTorch 集成](pytorch.md) |
| {py:class}`uniqc.QuantumLayer` / {py:class}`uniqc.TorchQuantumLayer` | [PyTorch · QuantumLayer](pytorch.md#quantumlayer) |
| {py:func}`uniqc.torch_adapter.parameter_shift_gradient` | [PyTorch · Parameter-Shift 梯度](pytorch.md#parameter-shift-梯度) |
| {py:func}`uniqc.torch_adapter.batch_execute` / {py:func}`uniqc.torch_adapter.batch_execute_with_params` | [PyTorch · 批量执行](pytorch.md#批量执行) |
| {py:func}`uniqc.torch_adapter.compute_all_gradients` | [PyTorch · 多参数电路](pytorch.md#多参数电路) |

## 格式互转与解析

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:mod}`uniqc.compile.originir` | [OriginIR · Python API 参考](originir.md#python-api-参考) |
| {py:class}`uniqc.OriginIR_BaseParser` | [OriginIR · Python API 参考](originir.md#python-api-参考) |
| {py:class}`uniqc.OpenQASM2_BaseParser` / {py:mod}`uniqc.compile.qasm` | [QASM · 格式互转操作](qasm.md#格式互转操作) |
| `Circuit.from_originir` / `Circuit.from_qasm` | [构造电路 · 格式互转](circuit.md#guide-circuit-format-conversion) · [QASM · 格式互转操作](qasm.md#格式互转操作) |

## 可视化

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:func}`uniqc.plot_time_line` | [主路径走读 · 5. 可视化](walkthrough.md#visualize) · [编译选项 · API 速查](../2_advanced/compiler_options_region.md#5-api-速查) |
| {py:func}`uniqc.circuit_to_html` | [主路径走读 · 5. 可视化](walkthrough.md#visualize) |
| `Circuit.draw` / {py:func}`uniqc.compile.draw.draw` | [构造电路 · 可视化](circuit.md#可视化) |
| {py:func}`uniqc.compile.compute_gate_depth` | [构造电路 · 线路信息](circuit.md#线路信息) |

## 异常类型

| API | 在哪个用户文档章节中使用 |
|-----|------------------------|
| {py:class}`uniqc.UnifiedQuantumError`（基类） | [提交任务 · 平台边界与限制](submit_task.md#平台边界与限制) |
| {py:class}`uniqc.AuthenticationError` / {py:class}`uniqc.NetworkError` / {py:class}`uniqc.QuotaExceededError` / {py:class}`uniqc.InsufficientCreditsError` | [任务管理器 · 错误处理](task_manager.md#guide-task-manager-error-handling) |
| {py:class}`uniqc.TaskFailedError` / {py:class}`uniqc.TaskNotFoundError` / {py:class}`uniqc.TaskTimeoutError` | [任务管理器 · 错误处理](task_manager.md#guide-task-manager-error-handling) |
| {py:class}`uniqc.BackendError` / {py:class}`uniqc.BackendNotFoundError` / {py:class}`uniqc.BackendNotAvailableError` / {py:class}`uniqc.BackendOptionsError` | [平台约定 · 统一后端工厂](platform_conventions.md#platform-get-backend) |
| {py:class}`uniqc.CircuitError` / {py:class}`uniqc.NotSupportedGateError` / {py:class}`uniqc.UnsupportedGateError` / {py:class}`uniqc.CircuitTranslationError` | [构造电路 · 量子门](circuit.md#量子门) · [QASM · 格式互转](qasm.md#格式互转操作) |
| {py:class}`uniqc.CompilationFailedError` / {py:class}`uniqc.CompilationResult` / {py:class}`uniqc.CompatibilityReport` | [编译选项（进阶）](../2_advanced/compiler_options_region.md#1-增强编译compile-函数) · [编译强度](../2_advanced/compile_levels.md) |
| {py:class}`uniqc.ConfigError` / {py:class}`uniqc.ConfigValidationError` / {py:class}`uniqc.ProfileNotFoundError` / {py:class}`uniqc.PlatformNotFoundError` | [平台约定 · 配置约定](platform_conventions.md#platform-configuration) |
| {py:class}`uniqc.RegisterDefinitionError` / {py:class}`uniqc.RegisterNotFoundError` / {py:class}`uniqc.RegisterOutOfRangeError` | [构造电路 · 命名量子寄存器](circuit.md#guide-circuit-named-qreg) |
| {py:class}`uniqc.StaleCalibrationError` | [校准（进阶） · 缓存管理](../2_advanced/calibration.md#8-缓存管理) |
| {py:class}`uniqc.TopologyError` / {py:class}`uniqc.TimelineDurationError` / {py:class}`uniqc.NotMatrixableError` / {py:class}`uniqc.MissingDependencyError` | [构造电路 · 提取酉矩阵](circuit.md#guide-circuit-unitary-matrix) · [平台约定 · DummyBackend](platform_conventions.md#platform-dummy-backend) |
