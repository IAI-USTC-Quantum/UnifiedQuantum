"""FastAPI application for the uniqc gateway management UI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from uniqc.gateway import api
from uniqc.gateway.ws import broadcaster

GITHUB_URL = "https://github.com/IAI-USTC-Quantum/UnifiedQuantum"
DOCS_URL = "https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/"


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

def _frontend_dist_dir() -> Path:
    """Return the built frontend distribution directory."""
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


class _SPAStaticFiles(StaticFiles):
    """Serve Vite static files with React Router history fallback."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or _looks_like_static_asset(path):
                raise
            return await super().get_response("index.html", scope)


def _looks_like_static_asset(path: str) -> bool:
    """Return True for paths that should keep normal 404 semantics."""
    normalized = path.strip("/")
    if not normalized:
        return False
    if normalized.startswith("assets/"):
        return True
    return Path(normalized).suffix != ""


def _mount_frontend(app: FastAPI) -> None:
    """Mount the built React SPA from frontend/dist/ if it exists."""
    frontend_dist = _frontend_dist_dir()

    if not frontend_dist.exists():
        return  # Dev mode: no built frontend yet

    app.mount("/", _SPAStaticFiles(directory=str(frontend_dist), html=True), name="static")


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
