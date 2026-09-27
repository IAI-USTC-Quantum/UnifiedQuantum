# API 参考

由 ``sphinx-apidoc`` 从 ``uniqc/`` 源码自动生成。`make html` / `make html-fast` 在每次构建时都会**重新跑** ``sphinx-apidoc``，
所以这一章总是与当前 git checkout 的源码保持一致。

## 顶层公共 API

最常用的符号都从 ``uniqc`` 顶层导出（见 ``uniqc/__init__.py`` 的 ``__all__``）；
新增公共符号时请在 ``__init__.py`` 同步更新。

* {py:class}`uniqc.Circuit <uniqc.circuit_builder.qcircuit.Circuit>`, {py:class}`uniqc.NamedCircuit <uniqc.circuit_builder.named_circuit.NamedCircuit>`, {py:class}`uniqc.QReg <uniqc.circuit_builder.qubit.QReg>`,
  {py:class}`uniqc.Qubit <uniqc.circuit_builder.qubit.Qubit>`, {py:func}`uniqc.circuit_def <uniqc.circuit_builder.named_circuit.circuit_def>`
* {py:func}`uniqc.compile`, {py:func}`uniqc.compile_for_backend <uniqc.compile.policy.compile_for_backend>`,
  {py:class}`uniqc.TranspilerConfig <uniqc.compile.compiler.TranspilerConfig>`
* {py:func}`uniqc.submit_task <uniqc.backend_adapter.task_manager.submit_task>`, {py:func}`uniqc.dry_run_task <uniqc.backend_adapter.task_manager.dry_run_task>`,
  {py:func}`uniqc.submit_batch <uniqc.backend_adapter.task_manager.submit_batch>`, {py:func}`uniqc.wait_for_result <uniqc.backend_adapter.task_manager.wait_for_result>`,
  {py:func}`uniqc.query_task <uniqc.backend_adapter.task_manager.query_task>`, {py:func}`uniqc.get_task <uniqc.backend_adapter.task_manager.get_task>`
* {py:class}`uniqc.QuantumBackend <uniqc.backend_adapter.backend.QuantumBackend>`, {py:class}`uniqc.OriginQBackend <uniqc.backend_adapter.backend.OriginQBackend>`,
  {py:class}`uniqc.IBMBackend <uniqc.backend_adapter.backend.IBMBackend>`,
  {py:class}`uniqc.QuarkBackend <uniqc.backend_adapter.backend.QuarkBackend>`, {py:class}`uniqc.DummyBackend <uniqc.backend_adapter.backend.DummyBackend>`
* {py:class}`uniqc.BackendInfo <uniqc.backend_adapter.backend_info.BackendInfo>`, {py:class}`uniqc.QubitTopology <uniqc.backend_adapter.backend_info.QubitTopology>`,
  {py:class}`uniqc.RegionSelector <uniqc.backend_adapter.region_selector.RegionSelector>`
* {py:class}`uniqc.M3Mitigator <uniqc.qem.m3.M3Mitigator>`, {py:class}`uniqc.ReadoutEM <uniqc.qem.readout_em.ReadoutEM>`
* 异常都在 {py:mod}`uniqc.exceptions`

## 按主题找指南页

每个 API 领域都有对应的叙事文档（含示例与坑位说明）：

| API 领域 | 指南页 |
|---|---|
| `Circuit` / 线路构建 | [构建量子线路](../1_basic_usage/circuit.md) · [线路分析](../2_advanced/circuit_analysis.md) |
| 模拟器 | [本地模拟](../1_basic_usage/simulation.md) · [MPS 模拟器](../2_advanced/mps_simulator.md) · [噪声模拟](../2_advanced/noise_simulation.md) · [动态电路](../2_advanced/dynamic_circuits.md) |
| 编译（`compile` / `TranspilerConfig`） | [编译选项与 Region 选择器](../2_advanced/compiler_options_region.md) · [编译策略](../2_advanced/compile_levels.md) |
| 任务提交（`submit_task` 等） | [提交任务到量子云平台](../1_basic_usage/submit_task.md) · [任务管理器](../1_basic_usage/task_manager.md) |
| 后端 / 适配器（`BackendInfo` / `RegionSelector`） | [云平台适配器架构](../2_advanced/adapter_architecture.md) · [平台约定](../1_basic_usage/platform_conventions.md) |
| 校准 / QEM（`M3Mitigator` / `ReadoutEM`） | [芯片校准与量子错误缓解](../2_advanced/calibration.md) |
| PyTorch | [PyTorch 集成](../1_basic_usage/pytorch.md) |
| CLI | [命令行工具](../4_cli/index.md) |

## 子模块索引

```{toctree}
:maxdepth: 2

uniqc
```

## PyTorch 与训练 API

以下公开页面与完整 API 树一起生成，并在缺失时由 ``sphinx -W`` 阻止文档构建：

```{toctree}
:maxdepth: 2

uniqc.torch_adapter
uniqc.algorithms.core.training
```

## 索引

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
