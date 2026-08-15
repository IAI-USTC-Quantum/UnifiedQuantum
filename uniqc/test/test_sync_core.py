"""Tests for ``uniqc.sync`` core logic (no subprocess / network)."""

from __future__ import annotations

import pytest

from uniqc import config as cfg
from uniqc.cli import sync as sync


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path):
    cfile = tmp_path / ".uniqc" / "config.yaml"
    monkeypatch.setattr(cfg, "CONFIG_DIR", cfile.parent)
    monkeypatch.setattr(cfg, "CONFIG_FILE", cfile)
    monkeypatch.delenv("UNIQC_PROFILE", raising=False)
    monkeypatch.delenv("UNIQC_INFISICAL_PROJECT_ID", raising=False)
    monkeypatch.delenv("UNIQC_INFISICAL_ENV", raising=False)
    return cfile


SAMPLE_CONFIG = {
    "always_ai_hints": True,
    "active_profile": "default",
    "sync": {"project_id": "proj-1", "env": "dev"},
    "default": {
        "originq": {
            "token": "originq-token",
            "task_group_size": 200,
            "available_qubits": [3, 7, 11],
        },
        "quark": {"QUARK_API_KEY": "quark-key"},
        "ibm": {
            "token": "ibm-token",
            "proxy": {"http": "http://127.0.0.1:7890", "https": ""},
        },
    },
    "work_ibm": {
        "originq": {"token": "@leading-at"},
    },
}


# ---------------------------------------------------------------------------
# Value encoding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "plain-token",
        "12345",  # numeric-looking token must stay a string
        "with spaces, = and # chars",
        "@leading-at",
        "json:looks-tagged",
        "line1\nline2",
        200,
        True,
        False,
        None,
        [1, 2, 3],
        {"http": "http://proxy", "https": "https://proxy"},
        {"nested": {"deep": [1, {"x": None}]}},
    ],
)
def test_encode_decode_roundtrip(value):
    assert sync.decode_value(sync.encode_value(value)) == value
    assert isinstance(sync.encode_value(value), str)


def test_encode_plain_string_is_verbatim():
    assert sync.encode_value("token-value") == "token-value"
    # Non-strings get the json: prefix so other tools can still read plain
    # string tokens directly.
    assert sync.encode_value(200) == "json:200"


def test_decode_invalid_json_tag_raises():
    with pytest.raises(sync.SyncError, match="not valid JSON"):
        sync.decode_value("json:{not json")


# ---------------------------------------------------------------------------
# Flatten / unflatten
# ---------------------------------------------------------------------------


def test_flatten_produces_expected_secret_names():
    flat = sync.flatten_config(SAMPLE_CONFIG)
    assert flat["UNIQC_DEFAULT_ORIGINQ_TOKEN"] == "originq-token"
    assert flat["UNIQC_DEFAULT_ORIGINQ_TASK_GROUP_SIZE"] == "json:200"
    assert flat["UNIQC_DEFAULT_ORIGINQ_AVAILABLE_QUBITS"] == "json:[3, 7, 11]"
    assert flat["UNIQC_DEFAULT_QUARK_QUARK_API_KEY"] == "quark-key"
    assert flat["UNIQC_DEFAULT_IBM_TOKEN"] == "ibm-token"
    assert flat["UNIQC_DEFAULT_IBM_PROXY_HTTP"] == "http://127.0.0.1:7890"
    # profile containing a platform name still flattens
    assert flat["UNIQC_WORK_IBM_ORIGINQ_TOKEN"] == "json:\"@leading-at\""


def test_flatten_skips_meta_keys_and_empty_values():
    flat = sync.flatten_config(SAMPLE_CONFIG)
    assert not any(k.startswith("UNIQC_ACTIVE") or k.startswith("UNIQC_SYNC") for k in flat)
    assert not any(k.startswith("UNIQC_ALWAYS") for k in flat)
    # ibm.proxy.https is "" → not synced
    assert "UNIQC_DEFAULT_IBM_PROXY_HTTPS" not in flat


def test_flatten_ignores_non_platform_sections():
    config = {"default": {"notaplatform": {"token": "x"}}}
    assert sync.flatten_config(config) == {}


def test_unflatten_roundtrip_restores_profiles():
    flat = sync.flatten_config(SAMPLE_CONFIG)
    profiles, skipped = sync.unflatten_secrets(flat)
    assert skipped == []
    expected = {
        "default": {
            **SAMPLE_CONFIG["default"],
            # empty values (ibm.proxy.https="") are not synced by design
            "ibm": {"token": "ibm-token", "proxy": {"http": "http://127.0.0.1:7890"}},
        },
        "work_ibm": SAMPLE_CONFIG["work_ibm"],
    }
    assert profiles == expected


def test_unflatten_preserves_types():
    flat = sync.flatten_config(SAMPLE_CONFIG)
    profiles, _ = sync.unflatten_secrets(flat)
    originq = profiles["default"]["originq"]
    assert originq["task_group_size"] == 200
    assert isinstance(originq["task_group_size"], int)
    assert originq["available_qubits"] == [3, 7, 11]
    assert profiles["default"]["ibm"]["proxy"]["http"] == "http://127.0.0.1:7890"
    # numeric-looking token stays a string
    flat2 = sync.flatten_config({"default": {"originq": {"token": "12345"}}})
    profiles2, _ = sync.unflatten_secrets(flat2)
    token = profiles2["default"]["originq"]["token"]
    assert token == "12345" and isinstance(token, str)


def test_parse_secret_name_quark_api_key_case():
    parsed = sync.parse_secret_name("UNIQC_DEFAULT_QUARK_QUARK_API_KEY")
    assert parsed == ("default", "quark", ["QUARK_API_KEY"])


def test_parse_secret_name_nested_fields():
    parsed = sync.parse_secret_name("UNIQC_DEFAULT_IBM_PROXY_HTTP")
    assert parsed == ("default", "ibm", ["proxy", "http"])


def test_parse_secret_name_underscore_profile():
    # The platform token is found scanning right-to-left, so profiles
    # containing underscores (or platform names) resolve correctly.
    parsed = sync.parse_secret_name("UNIQC_WORK_IBM_ORIGINQ_TOKEN")
    assert parsed == ("work_ibm", "originq", ["token"])


def test_parse_secret_name_rejects_foreign_names():
    assert sync.parse_secret_name("DATABASE_URL") is None
    assert sync.parse_secret_name("UNIQC_NOT_A_PLATFORM") is None
    assert sync.parse_secret_name("UNIQC_DEFAULT_TOKEN") is None  # no platform token


def test_unflatten_reports_unparsable_uniqc_secrets():
    _, skipped = sync.unflatten_secrets({"UNIQC_WEIRD": "x", "OTHER": "y"})
    assert skipped == ["UNIQC_WEIRD"]


def test_secret_name_to_display():
    assert sync.secret_name_to_display("UNIQC_DEFAULT_IBM_PROXY_HTTP") == "default.ibm.proxy.http"
    assert sync.secret_name_to_display("FOREIGN_KEY") == "FOREIGN_KEY"


# ---------------------------------------------------------------------------
# Change computation
# ---------------------------------------------------------------------------


def test_compute_changes():
    local = {"A": "1", "B": "2", "C": "3"}
    remote = {"B": "2-changed", "C": "3", "D": "4"}
    changes = sync.compute_changes(local, remote)
    assert changes["push_add"] == ["A"]
    assert changes["push_change"] == ["B"]
    assert changes["prune"] == ["D"]
    assert changes["pull_add"] == ["D"]
    assert changes["pull_change"] == ["B"]


# ---------------------------------------------------------------------------
# Settings resolution
# ---------------------------------------------------------------------------


def test_resolve_settings_from_config_file(isolate_config):
    cfg.save_config(SAMPLE_CONFIG)
    assert sync.resolve_sync_settings(None, None) == ("proj-1", "dev")


def test_resolve_settings_precedence(monkeypatch, isolate_config):
    cfg.save_config(SAMPLE_CONFIG)
    monkeypatch.setenv("UNIQC_INFISICAL_PROJECT_ID", "env-project")
    monkeypatch.setenv("UNIQC_INFISICAL_ENV", "prod")
    # flag > env var > config
    assert sync.resolve_sync_settings("flag-project", "staging") == ("flag-project", "staging")
    assert sync.resolve_sync_settings(None, None) == ("env-project", "prod")


def test_resolve_settings_missing_project_id(monkeypatch, isolate_config):
    cfg.save_config({"default": {}})
    monkeypatch.delenv("UNIQC_INFISICAL_PROJECT_ID", raising=False)
    with pytest.raises(sync.SyncError, match="uniqc sync setup"):
        sync.resolve_sync_settings(None, None)


# ---------------------------------------------------------------------------
# Infisical adapter (subprocess mocked)
# ---------------------------------------------------------------------------


def test_run_infisical_missing_binary(monkeypatch):
    monkeypatch.setattr(sync.shutil, "which", lambda name: None)
    with pytest.raises(sync.SyncError, match="infisical.*not found"):
        sync.run_infisical(["secrets"])


def test_run_infisical_failure_includes_stderr_tail(monkeypatch):
    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "line1\nError: unauthorized (401)\nline3"

    monkeypatch.setattr(sync.shutil, "which", lambda name: "/usr/bin/infisical")
    monkeypatch.setattr(
        sync.subprocess,
        "run",
        lambda *a, **k: FakeResult(),
    )
    with pytest.raises(sync.SyncError, match="401"):
        sync.run_infisical(["secrets"])


def test_fetch_remote_secrets_parses_json(monkeypatch):
    captured = {}

    def fake_run_infisical(args, token=None, confirm=None):
        captured["args"] = args
        return '[{"secretKey":"A","secretValue":"1"},{"secretKey":"B","secretValue":"2"}]'

    monkeypatch.setattr(sync, "run_infisical", fake_run_infisical)
    secrets = sync.fetch_remote_secrets("proj", "dev")
    assert secrets == {"A": "1", "B": "2"}
    assert captured["args"][:4] == ["secrets", "-o", "json", "--projectId"]
    assert "proj" in captured["args"] and "dev" in captured["args"]


def test_fetch_remote_secrets_empty_project(monkeypatch):
    monkeypatch.setattr(sync, "run_infisical", lambda *a, **k: "null")
    assert sync.fetch_remote_secrets("proj", "dev") == {}


def test_push_secrets_batches_assignments(monkeypatch):
    captured = {}

    def fake_run_infisical(args, token=None, confirm=None):
        captured["args"] = args
        captured["token"] = token
        return "[]"

    monkeypatch.setattr(sync, "run_infisical", fake_run_infisical)
    sync.push_secrets({"A": "1", "B": "json:2"}, "proj", "dev", token="tok")
    assert captured["args"][:2] == ["secrets", "set"]
    assert "A=1" in captured["args"] and "B=json:2" in captured["args"]
    assert captured["token"] == "tok"
    assert "--type" in captured["args"] and "shared" in captured["args"]


def test_delete_remote_secret_confirms_and_tolerates_failure(monkeypatch):
    calls = []

    def fake_run_infisical(args, token=None, confirm=None):
        calls.append((args, confirm))
        if len(calls) == 1:
            raise sync.SyncError("boom")
        return "ok"

    monkeypatch.setattr(sync, "run_infisical", fake_run_infisical)
    assert sync.delete_remote_secret("X", "proj", "dev") is False  # failure → False
    assert sync.delete_remote_secret("X", "proj", "dev") is True
    assert calls[0][1] == "y\n"


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def test_backup_config_file(isolate_config):
    cfg.save_config(SAMPLE_CONFIG)
    backup = sync.backup_config_file(cfg.CONFIG_FILE)
    assert backup is not None and "bak-" in backup
    assert cfg.load_config(backup) == SAMPLE_CONFIG


def test_backup_missing_file_returns_none(tmp_path):
    assert sync.backup_config_file(tmp_path / "nope.yaml") is None
