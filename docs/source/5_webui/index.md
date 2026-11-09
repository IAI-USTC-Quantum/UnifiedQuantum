# WebUI 与持久化

UnifiedQuantum 自带一个 FastAPI 网关 + 前端 SPA，可以用浏览器查看 backend 列表、
芯片可视化、本地任务历史，并运行本地量子实验。

## 启动方式

```bash
# 发行包自带界面，安装后即可启动
uniqc gateway start --host 127.0.0.1 --port 8000
# 然后在浏览器打开 http://127.0.0.1:8000/
```

打开 `/demo` 的 **Local quantum lab**，选择 GHZ、W 态或 Ramsey 干涉，设置
2–8 个量子比特后运行。页面展示原生 statevector 的精确概率、独立解析对照误差、
实际线路和 JSON 导出；右侧最低位对应 `q[0]`。更改参数后旧结果失效。
这是本地模拟演示，耗时是本机软件运行时间。

同一演示也可从 CLI 运行：

```bash
uniqc demo --case ghz --qubits 4 --output ghz.json
uniqc demo --case ramsey --qubits 3 --phase 0.73
```

开发前端：

```bash
cd frontend
npm ci
npm run dev   # vite dev server，会代理到 uniqc gateway 后端
```

后端的 ASGI app 由 ``uniqc.gateway.server.create_app()`` 构造；可以直接用 uvicorn /
gunicorn / 第三方 reverse-proxy 部署。

从源码开发构建发行包时，需要 Node/npm；PEP517 构建后端按已提交的
`package-lock.json` 构建界面，并保存前端源文件、构建器和实际资产的 SHA256。
正式源码包自带这些资产，构建 wheel 无需 Node 或 npm 网络下载。
前端生产依赖的原始许可与来源随包保留。使用 `frontend/dist` 的开发回退仍可用。

## 编程访问

```{include} ../_generated/examples/5_webui/01_gateway_demo.md
```

```{include} ../_generated/examples/5_webui/02_local_quantum_lab.md
```

## 持久化层

| 路径 | 内容 |
|------|------|
| ``~/.uniqc/config.yaml`` | 平台 token、proxy、profile、gateway host/port |
| ``~/.uniqc/cache/tasks.sqlite`` | 本地任务历史（SQLite，由 ``TaskStore`` 管理） |
| ``~/.uniqc/backend/backends.json`` | 后端发现缓存 |
| ``~/.uniqc/backend/chips/`` | chip characterization 缓存 |
| ``~/.uniqc/backend/virtual/`` | 用户自定义含噪量子虚拟机（YAML） |
| ``~/.uniqc/calibration_cache/`` | XEB / readout 校准结果（带 ISO-8601 时间戳） |
| ``~/.uniqc/logs/`` | gateway / cli 运行日志（如果启用） |

任务库是 ``TaskStore`` 抽象（``uniqc.backend_adapter.task.store``）的默认 SQLite 实现，
schema 由 ``uniqc.backend_adapter.database_migration`` 管理，可以平滑升级到新版本。
迁移在每次 ``submit_task`` / ``query_task`` 第一次调用时自动触发。

## 相关页面

- [CLI gateway 命令](../4_cli/gateway.md) —— `start` / `stop` / `status` 与配置项
- [任务管理器](../1_basic_usage/task_manager.md) —— 任务库的上层 API
- [自定义含噪量子虚拟机](../2_advanced/virtual_backends.md) —— `~/.uniqc/backend/virtual/` 的 YAML 格式
- [芯片校准与 QEM](../2_advanced/calibration.md) —— `~/.uniqc/calibration_cache/` 的读写方
- [CLI config 命令](../4_cli/config.md) —— `~/.uniqc/config.yaml` 的字段与 profile
