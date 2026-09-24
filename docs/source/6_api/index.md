# API 参考

由 ``sphinx-apidoc`` 从 ``uniqc/`` 源码自动生成。`make html` / `make html-fast` 在每次构建时都会**重新跑** ``sphinx-apidoc``，
所以这一章总是与当前 git checkout 的源码保持一致。

## 顶层公共 API

最常用的符号都从 ``uniqc`` 顶层导出（见 ``uniqc/__init__.py`` 的 ``__all__``）；
新增公共符号时请在 ``__init__.py`` 同步更新。

* {py:class}`Circuit <uniqc.circuit_builder.qcircuit.Circuit>`, {py:class}`NamedCircuit <uniqc.circuit_builder.named_circuit.NamedCircuit>`, {py:class}`QReg <uniqc.circuit_builder.qubit.QReg>`,
  {py:class}`Qubit <uniqc.circuit_builder.qubit.Qubit>`, {py:func}`circuit_def() <uniqc.circuit_builder.named_circuit.circuit_def>`
* {py:func}`compile() <uniqc.compile.compiler.compile>`, {py:func}`compile_for_backend() <uniqc.compile.policy.compile_for_backend>`,
  {py:class}`TranspilerConfig <uniqc.compile.compiler.TranspilerConfig>`
* {py:func}`submit_task() <uniqc.backend_adapter.task_manager.submit_task>`, {py:func}`dry_run_task() <uniqc.backend_adapter.task_manager.dry_run_task>`,
  {py:func}`submit_batch() <uniqc.backend_adapter.task_manager.submit_batch>`, {py:func}`wait_for_result() <uniqc.backend_adapter.task_manager.wait_for_result>`,
  {py:func}`query_task() <uniqc.backend_adapter.task_manager.query_task>`, {py:func}`get_task() <uniqc.backend_adapter.task_manager.get_task>`
* {py:class}`QuantumBackend <uniqc.backend_adapter.backend.QuantumBackend>`, {py:class}`OriginQBackend <uniqc.backend_adapter.backend.OriginQBackend>`,
  {py:class}`IBMBackend <uniqc.backend_adapter.backend.IBMBackend>`,
  {py:class}`QuarkBackend <uniqc.backend_adapter.backend.QuarkBackend>`, {py:class}`DummyBackend <uniqc.backend_adapter.backend.DummyBackend>`
* {py:class}`BackendInfo <uniqc.backend_adapter.backend_info.BackendInfo>`, {py:class}`QubitTopology <uniqc.backend_adapter.backend_info.QubitTopology>`,
  {py:class}`RegionSelector <uniqc.backend_adapter.region_selector.RegionSelector>`
* {py:class}`M3Mitigator <uniqc.qem.m3.M3Mitigator>`, {py:class}`ReadoutEM <uniqc.qem.readout_em.ReadoutEM>`
* 异常都在 {py:mod}`uniqc.exceptions`

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
