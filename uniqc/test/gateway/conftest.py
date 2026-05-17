"""Shared fixtures for gateway tests.

Each gateway test gets a fresh, isolated SQLite task store + archive store
backed by ``tmp_path``. Without this, gateway endpoints would touch the real
``~/.uniqc/cache/tasks.sqlite``.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_task_db(monkeypatch, tmp_path: Path) -> Path:
    """Redirect ``DEFAULT_CACHE_DIR`` to ``tmp_path`` for the duration of a test.

    Both ``TaskStore()`` and ``ArchiveStore()`` (which calls ``TaskStore()``
    internally with no args) will land in ``tmp_path`` instead of
    ``~/.uniqc/cache/``.
    """
    monkeypatch.setattr("uniqc.backend_adapter.task.store.DEFAULT_CACHE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fastapi_client(isolated_task_db, monkeypatch):
    """Return a ``TestClient`` for the gateway FastAPI app, isolated from disk."""
    from fastapi.testclient import TestClient

    from uniqc.gateway.server import create_app

    # No frontend mount: avoid serving the real frontend/dist/ during tests
    monkeypatch.setattr("uniqc.gateway.server._mount_frontend", lambda app: None)

    return TestClient(create_app())
