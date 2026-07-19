# CLI 完整 walkthrough

下面这个例子通过 ``subprocess`` 把所有最常用的 CLI 子命令连续跑了一遍，输出就是 CLI
真实的样子。本页内容由 ``examples/4_cli/01_cli_walkthrough.py`` 自动生成，
保证只要本地能 `make html`，示例就可运行。

## 示例

```{include} ../_generated/examples/4_cli/01_cli_walkthrough.md
```

## 子命令一览

| 命令 | 说明 | 详细文档 |
|------|------|---------|
| ``uniqc --help`` | 顶层帮助，列出所有子命令 | [CLI 介绍](index.md) |
| ``uniqc simulate <file> [--shots N] [--backend <id>]`` | 本地模拟 OriginIR / QASM 文件 | [`uniqc simulate`](simulate.md) |
| ``uniqc submit <file> -b <provider:chip> [-s <shots>] [--wait]`` | 提交线路；``-b dummy:local:simulator`` 用本地 dummy；真平台需配 token | [`uniqc submit`](submit.md) |
| ``uniqc submit ... --dry-run`` | 离线校验（不真的提交） | [`uniqc submit`](submit.md) |
| ``uniqc result <task_id>`` | 查询 / 取回单个任务结果 | [`uniqc result`](result.md) |
| ``uniqc task list / show / ...`` | 本地任务历史（SQLite at ``~/.uniqc/tasks.db``） | [`uniqc task`](task.md) |
| ``uniqc backend list / show / update`` | 后端发现与缓存（``~/.uniqc/backend/backends.json``） | [`uniqc backend`](backend.md) |
| ``uniqc backend chip-display <id>`` | 全屏可视化芯片标定（T1/T2、保真度、拓扑） | [`uniqc backend`](backend.md) |
| ``uniqc backend virtual init / list / show / validate`` | 自定义含噪量子虚拟机（``~/.uniqc/backend/virtual/``） | [`uniqc backend`](backend.md) · [含噪虚拟机](../2_advanced/virtual_backends.md) |
| ``uniqc config init / set / get / validate`` | 配置文件管理（``~/.uniqc/config.yaml``） | [`uniqc config`](config.md) |
| ``uniqc calibrate xeb / readout / pattern`` | 芯片标定 → 写入 ``~/.uniqc/calibration_cache/`` | [`uniqc calibrate`](calibrate.md) |
| ``uniqc circuit ...`` | 电路文件转换 / 检查 | [`uniqc circuit`](circuit.md) |
| ``uniqc doctor`` | 一键环境诊断：依赖、配置、缓存、网络连通性 | [`uniqc doctor`](doctor.md) |
| ``uniqc gateway --host ... --port ...`` | 启动 WebUI / FastAPI 网关 | [`uniqc gateway`](gateway.md) · [WebUI](../5_webui/index.md) |

帮助文本里都附带了对应文档的 URL；加 ``--ai-hints`` 选项（或环境变量 ``UNIQC_AI_HINTS=1``）
会输出额外的 AI 工作流提示。

## Dummy backend id 命名

CLI ``-p`` / ``-b`` 跟 Python API ``backend=...`` 共用同一套 id 文法（详见
[进阶教程 · Dummy 系统](../2_advanced/walkthrough.md#advanced-dummy-system)）：

| id | 含义 |
|----|------|
| ``dummy`` / ``dummy:local:simulator`` | 完全无约束、无噪声 |
| ``dummy:local:virtual-line-N`` | 虚拟线性拓扑、无噪声 |
| ``dummy:local:virtual-grid-RxC`` | 虚拟网格拓扑、无噪声 |
| ``dummy:local:mps-linear-N[:chi=K[:cutoff=E][:seed=S]]`` | MPS 引擎，线性拓扑 |
| ``dummy:<platform>:<backend>`` | 复用真实芯片拓扑 + 标定噪声 |
