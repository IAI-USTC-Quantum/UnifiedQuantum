"""CLI tests for ``uniqc sync``.

The Infisical subcommands (setup/status/push/pull) are tested with all
Infisical interaction mocked; the confsync-based ``upload`` subcommand is
tested with a fake ``confsync`` module.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uniqc import config as cfg
from uniqc.cli import sync as sync_mod
from uniqc.cli.main import app

runner = CliRunner()

LOCAL_CONFIG = {
    "always_ai_hints": False,
    "active_profile": "default",
    "sync": {"project_id": "proj-1", "env": "dev"},
    "default": {
        "originq": {
            "token": "local-token",
            "task_group_size": 200,
            "available_qubits": [1, 2],
        },
        "quark": {"QUARK_API_KEY": "quark-key"},
    },
}

REMOTE_SECRETS = {
    "UNIQC_DEFAULT_ORIGINQ_TOKEN": "remote-token",
    "UNIQC_DEFAULT_QUARK_QUARK_API_KEY": "quark-key",
    "UNIQC_DEFAULT_IBM_TOKEN": "ibm-remote",
    "FOREIGN_SECRET": "not-ours",
}


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path):
    cfile = tmp_path / ".uniqc" / "config.yaml"
    monkeypatch.setattr(cfg, "CONFIG_DIR", cfile.parent)
    monkeypatch.setattr(cfg, "CONFIG_FILE", cfile)
    # The pull command binds CONFIG_FILE at call time from uniqc.config.
    monkeypatch.delenv("UNIQC_PROFILE", raising=False)
    monkeypatch.delenv("UNIQC_INFISICAL_PROJECT_ID", raising=False)
    monkeypatch.delenv("UNIQC_INFISICAL_ENV", raising=False)
    monkeypatch.delenv("UNIQC_INFISICAL_TOKEN", raising=False)
    yield cfile


@pytest.fixture
def remote(monkeypatch):
    """Mock the Infisical fetch; record what push/delete would send."""
    state = {"remote": dict(REMOTE_SECRETS), "pushed": [], "deleted": []}
    monkeypatch.setattr(
        sync_mod, "fetch_remote_secrets", lambda *a, **k: dict(state["remote"])
    )

    def fake_push(secrets, project_id, env, token=None):
        state["pushed"].append(dict(secrets))
        state["remote"].update(secrets)

    def fake_delete(name, project_id, env, token=None):
        state["deleted"].append(name)
        state["remote"].pop(name, None)
        return True

    monkeypatch.setattr(sync_mod, "push_secrets", fake_push)
    monkeypatch.setattr(sync_mod, "delete_remote_secret", fake_delete)
    return state


def _write_local(cfile, config=LOCAL_CONFIG):
    cfg.save_config(config, cfile)


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


def test_sync_setup_persists_settings(isolate_config):
    result = runner.invoke(app, ["sync", "setup", "--project-id", "abc", "--env", "prod"])
    assert result.exit_code == 0, result.output
    stored = cfg.load_config()["sync"]
    assert stored == {"project_id": "abc", "env": "prod"}


def test_sync_setup_requires_project_id():
    result = runner.invoke(app, ["sync", "setup"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_sync_status_reports_both_directions(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "status"])
    assert result.exit_code == 0, result.output
    # local-only → would push; remote-only → would pull; differing → update
    assert "default.originq.task_group_size" in result.output
    assert "default.ibm.token" in result.output
    # values are never printed
    assert "remote-token" not in result.output
    assert "local-token" not in result.output
    # foreign secrets are ignored
    assert "FOREIGN_SECRET" not in result.output


def test_sync_status_json(isolate_config, remote):
    import re

    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "status", "--format", "json"])
    assert result.exit_code == 0, result.output
    # Rich highlighting may inject ANSI codes; strip them before parsing.
    clean = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    payload = json.loads(clean[clean.index("{") : clean.rindex("}") + 1])
    assert payload["project_id"] == "proj-1"
    assert "default.originq.token" in payload["pull_change"]
    assert "default.ibm.token" in payload["pull_add"]


def test_sync_fails_without_project_settings(isolate_config, monkeypatch):
    cfg.save_config({"default": {}}, isolate_config)
    result = runner.invoke(app, ["sync", "status"])
    assert result.exit_code == 1
    assert "sync setup" in result.output


def test_sync_project_id_flag_overrides(isolate_config, remote, monkeypatch):
    _write_local(isolate_config)
    seen = {}

    def fake_fetch(project_id, env, token=None):
        seen["id"] = project_id
        seen["env"] = env
        return {}

    monkeypatch.setattr(sync_mod, "fetch_remote_secrets", fake_fetch)
    result = runner.invoke(app, ["sync", "status", "--project-id", "flag-id", "--env", "prod"])
    assert result.exit_code == 0, result.output
    assert seen == {"id": "flag-id", "env": "prod"}


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


def test_sync_push_uploads_changes(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "push"])
    assert result.exit_code == 0, result.output
    pushed = remote["pushed"][0]
    assert "UNIQC_DEFAULT_ORIGINQ_TOKEN" in pushed
    assert pushed["UNIQC_DEFAULT_ORIGINQ_TOKEN"] == "local-token"
    assert pushed["UNIQC_DEFAULT_ORIGINQ_TASK_GROUP_SIZE"] == "json:200"
    # unchanged secret (quark key) is not re-pushed
    assert "UNIQC_DEFAULT_QUARK_QUARK_API_KEY" not in pushed
    # token value never echoed
    assert "local-token" not in result.output


def test_sync_push_no_changes(isolate_config, remote):
    flat = sync_mod.flatten_config(LOCAL_CONFIG)
    remote["remote"] = dict(flat)
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "push"])
    assert result.exit_code == 0, result.output
    assert remote["pushed"] == []
    assert "nothing to push" in result.output


def test_sync_push_prune_deletes_stale(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "push", "--prune"])
    assert result.exit_code == 0, result.output
    # IBM token exists only remotely → pruned; foreign secret untouched
    assert remote["deleted"] == ["UNIQC_DEFAULT_IBM_TOKEN"]
    assert "FOREIGN_SECRET" in remote["remote"]


def test_sync_push_without_prune_keeps_stale(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "push"])
    assert result.exit_code == 0, result.output
    assert remote["deleted"] == []
    assert "UNIQC_DEFAULT_IBM_TOKEN" in remote["remote"]


def test_sync_push_dry_run_does_not_write(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "push", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert remote["pushed"] == []
    assert "Would push" in result.output


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


def test_sync_pull_replaces_profiles_and_backs_up(isolate_config, remote):
    config = {
        **LOCAL_CONFIG,
        # platform-free top-level sections are machine-local and survive pull
        "gateway": {"host": "127.0.0.1", "port": 18765},
    }
    _write_local(isolate_config, config)
    result = runner.invoke(app, ["sync", "pull"])
    assert result.exit_code == 0, result.output
    pulled = cfg.load_config()
    # remote wins
    assert pulled["default"]["originq"]["token"] == "remote-token"
    assert pulled["default"]["ibm"]["token"] == "ibm-remote"
    assert pulled["default"]["quark"]["QUARK_API_KEY"] == "quark-key"
    # local-only values are dropped (mirror semantics)
    assert "task_group_size" not in pulled["default"]["originq"]
    # machine-local keys preserved
    assert pulled["sync"] == {"project_id": "proj-1", "env": "dev"}
    assert pulled["active_profile"] == "default"
    assert pulled["always_ai_hints"] is False
    assert pulled["gateway"] == {"host": "127.0.0.1", "port": 18765}
    # backup contains the previous config
    backups = list(isolate_config.parent.glob("config.yaml.bak-*"))
    assert len(backups) == 1
    assert cfg.load_config(backups[0])["default"]["originq"]["token"] == "local-token"


def test_sync_pull_preserves_quark_api_key_casing(isolate_config, remote):
    _write_local(isolate_config)
    runner.invoke(app, ["sync", "pull"])
    pulled = cfg.load_config()
    assert "QUARK_API_KEY" in pulled["default"]["quark"]


def test_sync_pull_restores_types(isolate_config, remote):
    flat = sync_mod.flatten_config(LOCAL_CONFIG)
    remote["remote"] = dict(flat)
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "pull"])
    assert result.exit_code == 0, result.output
    pulled = cfg.load_config()
    assert pulled["default"]["originq"]["task_group_size"] == 200
    assert pulled["default"]["originq"]["available_qubits"] == [1, 2]


def test_sync_pull_no_backup_flag(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "pull", "--no-backup"])
    assert result.exit_code == 0, result.output
    assert not list(isolate_config.parent.glob("config.yaml.bak-*"))


def test_sync_pull_empty_remote_refuses(isolate_config, remote):
    _write_local(isolate_config)
    remote["remote"] = {}
    result = runner.invoke(app, ["sync", "pull"])
    assert result.exit_code == 1
    assert "Refusing" in result.output
    # local config untouched
    assert cfg.load_config()["default"]["originq"]["token"] == "local-token"


def test_sync_pull_dry_run(isolate_config, remote):
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "pull", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert cfg.load_config()["default"]["originq"]["token"] == "local-token"
    assert "Would pull" in result.output


def test_sync_pull_fresh_machine_reports_no_removals(isolate_config, remote):
    # A fresh machine (default config, empty tokens) pulls everything and
    # must NOT report phantom "Removed" keys — only local-only keys are
    # dropped by the mirror semantics.
    cfg.save_config(
        {
            **LOCAL_CONFIG,
            "default": {"originq": {"token": ""}},
        },
        isolate_config,
    )
    result = runner.invoke(app, ["sync", "pull"])
    assert result.exit_code == 0, result.output
    assert "Removed" not in result.output
    assert "Added default.originq.token" in result.output


def test_sync_pull_dry_run_lists_local_only_drops(isolate_config, remote):
    # task_group_size exists locally but not remotely → dropped on pull.
    _write_local(isolate_config)
    result = runner.invoke(app, ["sync", "pull", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Local-only keys that would be dropped" in result.output
    assert "default.originq.task_group_size" in result.output


def test_sync_pull_resets_missing_active_profile(isolate_config, remote):
    config = dict(LOCAL_CONFIG)
    config["active_profile"] = "gone"
    _write_local(isolate_config, config)
    result = runner.invoke(app, ["sync", "pull"])
    assert result.exit_code == 0, result.output
    assert cfg.load_config()["active_profile"] == "default"
    assert "gone" in result.output


# ---------------------------------------------------------------------------
# Infisical failure surfaces
# ---------------------------------------------------------------------------


def test_sync_error_surfaces_cli_failure(isolate_config, remote, monkeypatch):
    _write_local(isolate_config)

    def boom(*a, **k):
        raise sync_mod.SyncError("infisical CLI failed (exit 1): unauthorized (401)")

    monkeypatch.setattr(sync_mod, "fetch_remote_secrets", boom)
    result = runner.invoke(app, ["sync", "status"])
    assert result.exit_code == 1
    assert "401" in result.output


# ---------------------------------------------------------------------------
# upload (confsync backend)
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_file(tmp_path: Path, monkeypatch) -> Path:
    """Point uniqc at an isolated config file with known content."""
    cfg_dir = tmp_path / ".uniqc"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.yaml"
    cfg_file.write_text("active_profile: default\ndefault:\n  originq:\n    token: xxx\n", encoding="utf-8")
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", cfg_file)
    return cfg_file


class _FakeConfsyncError(Exception):
    pass


def _install_fake_confsync(monkeypatch, *, push_result: int = 3, error: Exception | None = None) -> dict:
    """Register a fake ``confsync`` module; returns a dict recording calls."""
    calls: dict = {}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

        def push(self, app: str, name: str, content: str) -> int:
            if error is not None:
                raise error
            calls["push"] = {"app": app, "name": name, "content": content}
            return push_result

    fake = types.ModuleType("confsync")
    fake.ConfsyncError = _FakeConfsyncError
    fake.load_client = lambda: FakeClient()
    monkeypatch.setitem(sys.modules, "confsync", fake)
    return calls


def test_upload_missing_config_file(tmp_path, monkeypatch):
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")
    result = runner.invoke(app, ["sync", "upload"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_upload_without_confsync_installed(config_file, monkeypatch):
    monkeypatch.setitem(sys.modules, "confsync", None)  # force ImportError
    result = runner.invoke(app, ["sync", "upload"])
    assert result.exit_code == 1
    assert "confsync-client is not installed" in result.output


def test_upload_success(config_file, monkeypatch):
    calls = _install_fake_confsync(monkeypatch, push_result=7)
    result = runner.invoke(app, ["sync", "upload"])
    assert result.exit_code == 0, result.output
    assert calls["push"]["app"] == "uniqc"
    assert calls["push"]["name"] == "config.yaml"
    assert calls["push"]["content"] == config_file.read_text(encoding="utf-8")
    assert "version 7" in result.output


def test_upload_custom_name(config_file, monkeypatch):
    calls = _install_fake_confsync(monkeypatch)
    result = runner.invoke(app, ["sync", "upload", "--name", "laptop.yaml"])
    assert result.exit_code == 0, result.output
    assert calls["push"]["name"] == "laptop.yaml"


def test_upload_server_error(config_file, monkeypatch):
    _install_fake_confsync(monkeypatch, error=_FakeConfsyncError("cannot reach server"))
    result = runner.invoke(app, ["sync", "upload"])
    assert result.exit_code == 1
    assert "Upload failed" in result.output
