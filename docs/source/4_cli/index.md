# CLI 介绍

UnifiedQuantum 的 CLI 入口是 ``uniqc``（由 ``uv tool install unified-quantum`` 全局安装），
等价的模块入口是 ``python -m uniqc.cli``。

## 子命令一览

| 命令 | 说明 |
|------|------|
| ``uniqc --help`` | 顶层帮助，列出所有子命令 |
| ``uniqc simulate <file> [--shots N] [--backend <id>]`` | 本地模拟 OriginIR / QASM 文件 |
| ``uniqc submit <file> -p <platform> [-b <backend>] [-s <shots>] [--wait]`` | 提交线路；``-p dummy`` 用本地 dummy；真平台需配 token |
| ``uniqc submit ... --dry-run`` | 离线校验（不真的提交） |
| ``uniqc result <task_id>`` | 查询 / 取回单个任务结果 |
| ``uniqc task list / show / ...`` | 本地任务历史（SQLite at ``~/.uniqc/tasks.db``） |
| ``uniqc backend list / show / update`` | 后端发现与缓存（``~/.uniqc/backend-cache/``） |
| ``uniqc backend chip-display <id>`` | 全屏可视化芯片标定（T1/T2、保真度、拓扑） |
| ``uniqc config init / set / get / validate`` | 配置文件管理（``~/.uniqc/config.yaml``） |
| ``uniqc calibrate xeb / readout / pattern`` | 芯片标定 → 写入 ``~/.uniqc/calibration_cache/`` |
| ``uniqc circuit ...`` | 电路文件转换 / 检查 |
| ``uniqc gateway --host ... --port ...`` | 启动 WebUI / FastAPI 网关（见 [WebUI](../5_webui/index.md)） |

帮助文本里都附带了对应文档的 URL；加 ``--ai-hints`` 选项（或环境变量 ``UNIQC_AI_HINTS=1``）
会输出额外的 AI 工作流提示。

## 完整 walkthrough

下面这个例子通过 ``subprocess`` 把所有最常用的 CLI 子命令连续跑了一遍，输出就是 CLI
真实的样子。

```{include} ../_generated/examples/4_cli/01_cli_walkthrough.md
```

## Dummy backend id 命名

CLI ``-p`` / ``-b`` 跟 Python API ``backend=...`` 共用同一套 id 文法（详见
[进阶 / Dummy 系统](../2_advanced/index.md)）：

| id | 含义 |
|----|------|
| ``dummy`` / ``dummy:local:simulator`` | 完全无约束、无噪声 |
| ``dummy:local:virtual-line-N`` | 虚拟线性拓扑、无噪声 |
| ``dummy:local:virtual-grid-RxC`` | 虚拟网格拓扑、无噪声 |
| ``dummy:local:mps-linear-N[:chi=K[:cutoff=E][:seed=S]]`` | MPS 引擎，线性拓扑 |
| ``dummy:<platform>:<backend>`` | 复用真实芯片拓扑 + 标定噪声 |
