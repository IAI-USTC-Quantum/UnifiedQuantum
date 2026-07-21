"""01 — Gateway / WebUI: programmatic launch and persistence

[doc-require: ]
[doc-output-include: stdout, source]

``uniqc gateway start`` 启动一个 FastAPI 服务（``uniqc.gateway.server:app``），既给前端 SPA
当后端，又对外提供 REST + WebSocket。本例不真的把进程留住，只演示如何在 Python 里
拿到 ASGI app、读出网关配置（host/port）以及触发一次任务，让后台任务库里有数据
可看。

实际开发中请用 ``uniqc gateway start --host 127.0.0.1 --port 8000`` 启动；前端在
``frontend/`` 下，``cd frontend && npm install && npm run dev``。
"""

from __future__ import annotations

from uniqc import Circuit, submit_task
from uniqc.gateway.config import load_gateway_config
from uniqc.gateway.server import create_app


def main() -> None:
    app = create_app()
    print("== Gateway ASGI app ==")
    print(type(app).__name__, "with", len(list(app.router.routes)), "routes")

    print()
    print("== Configured host/port ==")
    cfg = load_gateway_config()
    print("host:", cfg["host"])
    print("port:", cfg["port"])

    print()
    print("== Triggering one dummy task so the UI has something to show ==")
    c = Circuit()
    c.h(0)
    c.measure(0)
    task_id = submit_task(c, backend="dummy:local:simulator", shots=64)
    print("task_id:", task_id)

    print()
    print("Launch the UI with:")
    print(f"    uniqc gateway start --host {cfg['host']} --port {cfg['port']}")
    print(f"    # then open http://{cfg['host']}:{cfg['port']}/")


if __name__ == "__main__":
    main()
