# 基本用法

构造电路、本地模拟、提交到 dummy 或真机、读取并后处理结果——这一章把"从空电路到
真机结果"的主路径上你需要的 API 全部走一遍，并附带最常用的配置 / 可视化。

## 主要 API（速查）

| 任务 | API | 文档 |
|------|-----|------|
| 构造电路 | {py:class}`uniqc.Circuit`, {py:class}`uniqc.NamedCircuit`, {py:func}`uniqc.circuit_def` | [API 参考](../6_api/index.md) |
| 本地模拟 | {py:class}`uniqc.simulator.OriginIR_Simulator` (statevector / density / MPS / qutip / torchquantum) | [02 本地模拟](#local-simulation) |
| 编译到目标后端 | {py:func}`uniqc.compile`, {py:func}`uniqc.compile_for_backend` | [进阶 / 编译选项](../2_advanced/index.md) |
| 提交任务 | {py:func}`uniqc.submit_task`, {py:func}`uniqc.dry_run_task`, {py:func}`uniqc.submit_batch` | [03 提交与后处理](#submit-postprocess) |
| 等待 / 查询 | {py:func}`uniqc.wait_for_result`, {py:func}`uniqc.query_task`, {py:func}`uniqc.get_task` | 同上 |
| 后端发现 | {py:func}`uniqc.list_backends`, {py:func}`uniqc.find_backend`, {py:func}`uniqc.fetch_all_backends` | [CLI / backend](../4_cli/index.md) |
| 后处理 | {py:func}`uniqc.calculate_expectation`, {py:func}`uniqc.shots2prob`, {py:func}`uniqc.kv2list` | 同 03 |
| 配置 | {py:mod}`uniqc.config`, ``uniqc config set ...`` | [04 配置](#config) |
| 可视化 | {py:func}`uniqc.plot_time_line`, {py:func}`uniqc.circuit_to_html`, ``matplotlib`` | [05 可视化](#visualize) |

(circuit-basics)=
## 1. 构造电路：原生 Circuit、qreg、OriginIR / QASM 导出

```{include} ../_generated/examples/1_basic_usage/01_circuit_basics.md
```

(local-simulation)=
## 2. 本地模拟

```{include} ../_generated/examples/1_basic_usage/02_local_simulation.md
```

(submit-postprocess)=
## 3. 通过 ``submit_task`` 提交并后处理

```{include} ../_generated/examples/1_basic_usage/03_submit_and_postprocess.md
```

(config)=
## 4. 配置文件 / `~/.uniqc/config.yaml`

UnifiedQuantum 把 token、proxy、profile 等配置统一存放在 ``~/.uniqc/config.yaml``，
并通过 ``UNIQC_PROFILE`` 环境变量切换 profile。

```{include} ../_generated/examples/1_basic_usage/04_config.md
```

(visualize)=
## 5. 可视化

```{include} ../_generated/examples/1_basic_usage/05_visualize.md
```

## 真机提交模板

```python
from uniqc import Circuit, dry_run_task, submit_task, wait_for_result

c = Circuit(); c.h(0); c.cnot(0, 1); c.measure(0, 1)

# 1. 离线检查（推荐每次都先 dry_run）
print(dry_run_task(c, backend="originq", backend_name="WK_C180", shots=1000))

# 2. 真机提交
task_id = submit_task(c, backend="originq", backend_name="WK_C180", shots=1000)
print(wait_for_result(task_id))
```

更多真机相关的细节（dummy:<platform>:<backend>、calibration cache、QEM）在
[进阶教程](../2_advanced/index.md)。
