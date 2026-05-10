# API 参考

由 [sphinx-autoapi](https://sphinx-autoapi.readthedocs.io/) 从 ``uniqc/`` 源码自动
生成。`make html` / `make html-fast` 在每次构建时都会**重新跑** ``sphinx-apidoc``，
所以这一章总是与当前 git checkout 的源码保持一致。

## 顶层公共 API

最常用的符号都从 ``uniqc`` 顶层导出（见 ``uniqc/__init__.py`` 的 ``__all__``）；
新增公共符号时请在 ``__init__.py`` 同步更新。

* {py:class}`uniqc.Circuit`, {py:class}`uniqc.NamedCircuit`, {py:class}`uniqc.QReg`,
  {py:class}`uniqc.Qubit`, {py:func}`uniqc.circuit_def`
* {py:func}`uniqc.compile`, {py:func}`uniqc.compile_for_backend`,
  {py:class}`uniqc.TranspilerConfig`
* {py:func}`uniqc.submit_task`, {py:func}`uniqc.dry_run_task`,
  {py:func}`uniqc.submit_batch`, {py:func}`uniqc.wait_for_result`,
  {py:func}`uniqc.query_task`, {py:func}`uniqc.get_task`
* {py:class}`uniqc.QuantumBackend`, {py:class}`uniqc.OriginQBackend`,
  {py:class}`uniqc.IBMBackend`,
  {py:class}`uniqc.QuarkBackend`, {py:class}`uniqc.DummyBackend`
* {py:class}`uniqc.BackendInfo`, {py:class}`uniqc.QubitTopology`,
  {py:class}`uniqc.RegionSelector`
* {py:class}`uniqc.M3Mitigator`, {py:class}`uniqc.ReadoutEM`
* 异常都在 {py:mod}`uniqc.exceptions`

## 子模块索引

```{toctree}
:maxdepth: 2

uniqc
```

## 索引

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
