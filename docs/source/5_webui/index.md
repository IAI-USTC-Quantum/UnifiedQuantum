# WebUI 与持久化

UnifiedQuantum 自带一个 FastAPI 网关 + 前端 SPA，可以用浏览器查看 backend 列表、
芯片可视化、本地任务历史、提交并跟踪任务。

## 启动方式

```bash
# 前端构建在 frontend/dist 下，CLI 会自动 mount 它
uniqc gateway --host 127.0.0.1 --port 8000
# 然后在浏览器打开 http://127.0.0.1:8000/
```

开发前端：

```bash
cd frontend
npm install
npm run dev   # vite dev server，会代理到 uniqc gateway 后端
```

后端的 ASGI app 由 ``uniqc.gateway.server.create_app()`` 构造；可以直接用 uvicorn /
gunicorn / 第三方 reverse-proxy 部署。

## 编程访问

```{include} ../_generated/examples/5_webui/01_gateway_demo.md
```

## 持久化层

| 路径 | 内容 |
|------|------|
| ``~/.uniqc/config.yaml`` | 平台 token、proxy、profile、gateway host/port |
| ``~/.uniqc/tasks.db`` | 本地任务历史（SQLite，由 ``TaskStore`` 管理） |
| ``~/.uniqc/backend-cache/`` | 后端发现 / chip characterization 缓存 |
| ``~/.uniqc/calibration_cache/`` | XEB / readout 校准结果（带 ISO-8601 时间戳） |
| ``~/.uniqc/logs/`` | gateway / cli 运行日志（如果启用） |

任务库是 ``TaskStore`` 抽象（``uniqc.backend_adapter.task.store``）的默认 SQLite 实现，
schema 由 ``uniqc.backend_adapter.database_migration`` 管理，可以平滑升级到新版本。
迁移在每次 ``submit_task`` / ``query_task`` 第一次调用时自动触发。
