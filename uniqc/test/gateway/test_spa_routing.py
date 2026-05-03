from __future__ import annotations

import anyio
import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import PlainTextResponse


def _scope(path: str) -> dict:
    return {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
    }


def test_spa_static_files_falls_back_to_index_for_client_routes(monkeypatch):
    from fastapi.staticfiles import StaticFiles

    from uniqc.gateway.server import _SPAStaticFiles

    calls: list[str] = []

    async def fake_static_response(self, path, scope):
        calls.append(path)
        if path == "index.html":
            return PlainTextResponse("spa-index")
        raise StarletteHTTPException(status_code=404)

    monkeypatch.setattr(StaticFiles, "get_response", fake_static_response)
    static = object.__new__(_SPAStaticFiles)

    response = anyio.run(static.get_response, "backends", _scope("/backends"))

    assert response.status_code == 200
    assert response.body == b"spa-index"
    assert calls == ["backends", "index.html"]


def test_spa_static_files_keeps_asset_404s(monkeypatch):
    from fastapi.staticfiles import StaticFiles

    from uniqc.gateway.server import _SPAStaticFiles

    async def fake_static_response(self, path, scope):
        if path == "assets/app.js":
            return PlainTextResponse("asset")
        raise StarletteHTTPException(status_code=404)

    monkeypatch.setattr(StaticFiles, "get_response", fake_static_response)
    static = object.__new__(_SPAStaticFiles)

    asset = anyio.run(static.get_response, "assets/app.js", _scope("/assets/app.js"))
    assert asset.status_code == 200
    assert asset.body == b"asset"

    with pytest.raises(StarletteHTTPException) as exc_info:
        anyio.run(static.get_response, "assets/missing.js", _scope("/assets/missing.js"))
    assert exc_info.value.status_code == 404


def test_spa_asset_path_detection():
    from uniqc.gateway.server import _looks_like_static_asset

    assert _looks_like_static_asset("assets/app.js") is True
    assert _looks_like_static_asset("favicon.ico") is True
    assert _looks_like_static_asset("backends") is False
    assert _looks_like_static_asset("tasks/task-1") is False
