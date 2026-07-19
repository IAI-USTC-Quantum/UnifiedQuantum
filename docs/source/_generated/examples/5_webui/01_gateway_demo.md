### 01 — Gateway / WebUI: programmatic launch and persistence

*Source*: ``examples/5_webui/01_gateway_demo.py``  
*Status*: **pass**

``uniqc gateway`` 启动一个 FastAPI 服务（``uniqc.gateway.server:app``），既给前端 SPA
当后端，又对外提供 REST + WebSocket。本例不真的把进程留住，只演示如何在 Python 里
拿到 ASGI app、读出网关配置（host/port）以及触发一次任务，让后台任务库里有数据
可看。

实际开发中请用 ``uniqc gateway --host 127.0.0.1 --port 8000`` 启动；前端在
``frontend/`` 下，``cd frontend && npm install && npm run dev``。

**Source code**

```{literalinclude} ../../../examples/5_webui/01_gateway_demo.py
:language: python
```

**Stdout**

```text
== Gateway ASGI app ==
FastAPI with 9 routes

== Configured host/port ==
host: 127.0.0.1
port: 18765

== Triggering one dummy task so the UI has something to show ==
task_id: uqt_5a77d85d1f8343c195987d602a797a83

Launch the UI with:
    uniqc gateway --host 127.0.0.1 --port 18765
    # then open http://127.0.0.1:18765/
```

