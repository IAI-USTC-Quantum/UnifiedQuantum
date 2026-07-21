"""Tests for the ``uniqc gateway`` CLI subcommand and gateway/server module.

Avoid spawning a real uvicorn — patch ``subprocess.Popen`` so the start
command is exercised without touching the network.
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uniqc.gateway import cli as gateway_cli
from uniqc.gateway.cli import app as gateway_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_pid_and_cache(monkeypatch, tmp_path):
    """Redirect PID file and cache dir to tmp_path so test runs never touch
    the real ``~/.uniqc/cache/gateway.pid``."""
    monkeypatch.setattr(gateway_cli, "DEFAULT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(gateway_cli, "PID_FILE", tmp_path / "gateway.pid")
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / "config.yaml")


@pytest.fixture
def fake_popen(monkeypatch):
    """Stub ``subprocess.Popen`` so ``start`` doesn't actually spawn uvicorn."""

    class _FakeProc:
        def __init__(self, pid: int = 99999) -> None:
            self.pid = pid

    captured: dict = {"called": False, "cmd": None}

    def _popen(cmd, **kwargs):
        captured["called"] = True
        captured["cmd"] = cmd
        return _FakeProc()

    # The CLI's resolution may run a subprocess check for uv — also stub that.
    real_run = subprocess.run

    def _run(cmd, *args, **kwargs):
        if cmd and cmd[0] == "uv":

            class _CP:
                returncode = 1

            return _CP()
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", _popen)
    monkeypatch.setattr(subprocess, "run", _run)
    return captured


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_read_pid_missing(tmp_path):
    assert gateway_cli._read_pid() is None


def test_write_and_read_pid(tmp_path):
    gateway_cli._write_pid(12345)
    assert gateway_cli._read_pid() == 12345


def test_read_pid_corrupted(tmp_path):
    gateway_cli.PID_FILE.write_text("not-a-pid")
    assert gateway_cli._read_pid() is None


def test_clear_pid(tmp_path):
    gateway_cli._write_pid(12345)
    gateway_cli._clear_pid()
    assert gateway_cli._read_pid() is None
    # Idempotent
    gateway_cli._clear_pid()


def test_is_alive_self():
    assert gateway_cli._is_alive(os.getpid()) is True


def test_is_alive_bogus():
    # PID 0 is special and os.kill(0, 0) signals the process group → may
    # behave inconsistently; pick a definitely-dead but valid-shaped PID.
    assert gateway_cli._is_alive(2_000_000_000) is False


def test_resolve_uvicorn_cmd_fallback(monkeypatch):
    """When ``uv run python -c 'import uvicorn'`` fails, we fall back to
    the plain Python invocation."""

    def _run(cmd, *args, **kwargs):
        class _CP:
            returncode = 1

        return _CP()

    monkeypatch.setattr(subprocess, "run", _run)
    cmd = gateway_cli._resolve_uvicorn_cmd("127.0.0.1", 18765)
    assert "uvicorn" in " ".join(cmd)
    assert "uniqc.gateway.server:create_app" in cmd
    assert "127.0.0.1" in cmd
    assert "18765" in cmd


def test_resolve_uvicorn_cmd_prefers_uv(monkeypatch):
    def _run(cmd, *args, **kwargs):
        class _CP:
            returncode = 0

        return _CP()

    monkeypatch.setattr(subprocess, "run", _run)
    cmd = gateway_cli._resolve_uvicorn_cmd("127.0.0.1", 18765)
    assert cmd[0] == "uv"


# ---------------------------------------------------------------------------
# `gateway start` / `gateway stop` / `gateway status`
# ---------------------------------------------------------------------------


def test_start_creates_pid_file(fake_popen):
    result = runner.invoke(gateway_app, ["start", "--port", "19999"])
    assert result.exit_code == 0, result.output
    assert fake_popen["called"] is True
    assert gateway_cli._read_pid() == 99999


def test_start_when_already_running(fake_popen, monkeypatch):
    gateway_cli._write_pid(os.getpid())
    monkeypatch.setattr(gateway_cli, "_is_alive", lambda pid: True)

    result = runner.invoke(gateway_app, ["start", "--port", "19999"])
    assert result.exit_code == 0
    assert "already running" in result.output


def test_stop_kills_and_clears_pid(monkeypatch):
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
    monkeypatch.setattr(gateway_cli, "_is_alive", lambda pid: True)

    gateway_cli._write_pid(54321)

    result = runner.invoke(gateway_app, ["stop"])
    assert result.exit_code == 0
    assert (54321, signal.SIGTERM) in killed
    assert gateway_cli._read_pid() is None


def test_stop_when_not_running():
    result = runner.invoke(gateway_app, ["stop"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_status_when_running(monkeypatch):
    monkeypatch.setattr(gateway_cli, "_is_alive", lambda pid: True)
    gateway_cli._write_pid(7777)

    result = runner.invoke(gateway_app, ["status"])
    assert result.exit_code == 0, result.output
    assert "running" in result.output
    assert "7777" in result.output


def test_status_when_not_running():
    result = runner.invoke(gateway_app, ["status"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_restart_invokes_start(fake_popen, monkeypatch):
    result = runner.invoke(gateway_app, ["restart", "--port", "19998"])
    assert result.exit_code == 0, result.output
    assert fake_popen["called"] is True


@pytest.mark.parametrize("host", ["localhost", "LOCALHOST.", "127.0.0.1", "127.12.34.56", "::1", "[::1]"])
def test_loopback_hosts_are_accepted(host):
    from uniqc.gateway.config import validate_loopback_host

    assert validate_loopback_host(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.10", "example.com"])
def test_non_loopback_hosts_are_rejected(host):
    from uniqc.gateway.config import validate_loopback_host

    with pytest.raises(ValueError, match="loopback"):
        validate_loopback_host(host)


def test_start_rejects_cli_non_loopback_host_before_spawn(fake_popen):
    result = runner.invoke(gateway_app, ["start", "--host", "0.0.0.0"])

    assert result.exit_code == 1
    assert "not allowed" in result.output
    assert "loopback" in result.output
    assert fake_popen["called"] is False


def test_start_loopback_override_recovers_invalid_saved_host(fake_popen):
    from uniqc.config import save_config

    save_config({"gateway": {"host": "0.0.0.0", "port": 19997}})
    result = runner.invoke(gateway_app, ["start", "--host", "127.0.0.1"])

    assert result.exit_code == 0, result.output
    assert fake_popen["called"] is True
    assert "127.0.0.1" in result.output


def test_start_rejects_persisted_non_loopback_host_before_spawn(fake_popen):
    from uniqc.config import save_config

    save_config({"gateway": {"host": "192.168.1.10", "port": 18765}})
    result = runner.invoke(gateway_app, ["start"])

    assert result.exit_code == 1
    assert "not allowed" in result.output
    assert "loopback" in result.output
    assert fake_popen["called"] is False


def test_ipv6_gateway_url_uses_brackets():
    assert gateway_cli._gateway_url("::1", 18765) == "http://[::1]:18765"


# ---------------------------------------------------------------------------
# Gateway server module
# ---------------------------------------------------------------------------


def test_uniqc_version_helper():
    from uniqc.gateway.server import _uniqc_version

    v = _uniqc_version()
    assert isinstance(v, str) and v


def test_looks_like_static_asset():
    from uniqc.gateway.server import _looks_like_static_asset

    assert _looks_like_static_asset("assets/main.js") is True
    assert _looks_like_static_asset("static/icon.png") is True
    assert _looks_like_static_asset("dashboard") is False
    assert _looks_like_static_asset("") is False


def test_create_app_returns_fastapi(monkeypatch):
    from uniqc.gateway.server import create_app

    monkeypatch.setattr("uniqc.gateway.server._mount_frontend", lambda app: None)
    app = create_app()
    assert app.title == "uniqc Gateway"

    # Sanity: health route registered
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/health" in routes
    assert "/api/version" in routes


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"],
)
def test_cors_allows_explicit_vite_dev_origins(fastapi_client, origin):
    response = fastapi_client.options(
        "/api/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_non_local_origin(fastapi_client):
    response = fastapi_client.options(
        "/api/health",
        headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_same_origin_requests_work_without_cors_origin(fastapi_client):
    response = fastapi_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "access-control-allow-origin" not in response.headers


def test_frontend_dist_dir_returns_path():
    from uniqc.gateway.server import _frontend_dist_dir

    assert isinstance(_frontend_dist_dir(), Path)


# ---------------------------------------------------------------------------
# gateway.config (small module that wasn't already covered)
# ---------------------------------------------------------------------------


def test_gateway_config_load_save_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / "config.yaml")
    from uniqc.gateway.config import load_gateway_config, save_gateway_config

    save_gateway_config(host="::1", port=22222)
    cfg = load_gateway_config()
    assert cfg == {"host": "::1", "port": 22222}
