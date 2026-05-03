"""FastAPI application for the uniqc gateway management UI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from uniqc.gateway import api
from uniqc.gateway.ws import broadcaster

GITHUB_URL = "https://github.com/IAI-USTC-Quantum/UnifiedQuantum"
DOCS_URL = "https://iai-ustc-quantum.github.io/UnifiedQuantum/"


def _uniqc_version() -> str:
    """Return the installed uniqc package version used by this process."""
    try:
        return package_version("unified-quantum")
    except PackageNotFoundError:
        try:
            from uniqc import __version__
        except Exception:
            return "0.0.0+unknown"
        return __version__

# ---------------------------------------------------------------------------
# App factory (importable from uvicorn)
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="uniqc Gateway",
        description="Management UI for uniqc quantum backends and tasks",
        version=_uniqc_version(),
    )

    # CORS — allow local dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST API
    app.include_router(api.router, prefix="/api")

    # Health check
    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/version")
    def version():
        return {
            "version": _uniqc_version(),
            "github_url": GITHUB_URL,
            "docs_url": DOCS_URL,
        }

    # WebSocket endpoint
    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket):
        await broadcaster.connect(websocket)
        try:
            while True:
                # Keep-alive: client can send any text; we just don't disconnect
                await websocket.receive_text()
        except WebSocketDisconnect:
            broadcaster.disconnect(websocket)

    # Static file serving (SPA fallback)
    _mount_frontend(app)

    return app


# ---------------------------------------------------------------------------
# Frontend static mount
# ---------------------------------------------------------------------------

def _mount_frontend(app: FastAPI) -> None:
    """Mount the built React SPA from frontend/dist/ if it exists."""
    # The frontend lives at the repo root: frontend/dist
    # server.py is at uniqc/gateway/server.py
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

    if not frontend_dist.exists():
        return  # Dev mode: no built frontend yet

    async def _spa_fallback(request):
        """Serve index.html for any unknown non-asset path (SPA routing)."""
        from starlette.responses import FileResponse, JSONResponse

        # Let StaticFiles handle assets — only serve index.html for app routes
        path = request.path_params.get("path", "")
        if path.startswith("assets/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)

        index = frontend_dist / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse(
            {"detail": "Frontend not built. Run: cd frontend && npm install && npm run build"},
            status_code=503,
        )

    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
    app.add_route("/{path:path}", _spa_fallback)


# ---------------------------------------------------------------------------
# Entry point (run directly with: python -m uniqc.gateway.server)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    from uniqc.gateway.config import load_gateway_config

    cfg = load_gateway_config()
    uvicorn.run(
        "uniqc.gateway.server:create_app",
        factory=True,
        host=cfg["host"],
        port=cfg["port"],
        reload=False,
    )
