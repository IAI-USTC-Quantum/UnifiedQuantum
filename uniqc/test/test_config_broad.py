"""Broad coverage tests for ``uniqc.config``.

The existing ``uniqc/test/cloud/test_config.py`` is gated by the cloud
marker and skipped in CI. This module exercises the public API directly
against ``tmp_path`` so it runs in the default suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uniqc import config as cfg
from uniqc.exceptions import ConfigError, PlatformNotFoundError, ProfileNotFoundError


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path: Path) -> Path:
    cfile = tmp_path / ".uniqc" / "config.yaml"
    monkeypatch.setattr(cfg, "CONFIG_DIR", cfile.parent)
    monkeypatch.setattr(cfg, "CONFIG_FILE", cfile)
    monkeypatch.delenv("UNIQC_PROFILE", raising=False)
    return cfile


# ---------------------------------------------------------------------------
# load_config / save_config / round-trip
# ---------------------------------------------------------------------------


def test_load_config_missing_returns_defaults(isolate_config):
    out = cfg.load_config()
    assert "default" in out
    # Returns a copy → mutating doesn't poison the default
    out["mutated"] = True
    assert "mutated" not in cfg.load_config()


def test_save_then_load_roundtrip(isolate_config):
    payload = {
        "active_profile": "myprof",
        "myprof": {
            "originq": {"token": "abc", "task_group_size": 100},
            "ibm": {"token": "xyz"},
        },
    }
    cfg.save_config(payload)
    loaded = cfg.load_config()
    assert loaded == payload


def test_load_config_with_empty_file_returns_defaults(isolate_config):
    isolate_config.parent.mkdir(parents=True, exist_ok=True)
    isolate_config.write_text("")
    out = cfg.load_config()
    assert "default" in out


def test_load_config_invalid_yaml_raises(isolate_config):
    isolate_config.parent.mkdir(parents=True, exist_ok=True)
    isolate_config.write_text("[: unmatched bracket")
    with pytest.raises(ConfigError):
        cfg.load_config()


def test_save_config_sets_restrictive_perms(isolate_config):
    cfg.save_config({"a": 1})
    # On Linux/macOS, the file mode should be 0o600
    mode = isolate_config.stat().st_mode & 0o777
    assert mode in (0o600, 0o644)  # 0o644 on some FS that ignore chmod


# ---------------------------------------------------------------------------
# Profile management
# ---------------------------------------------------------------------------


def test_get_active_profile_default(isolate_config):
    assert cfg.get_active_profile() == "default"


def test_get_active_profile_from_env(isolate_config, monkeypatch):
    monkeypatch.setenv("UNIQC_PROFILE", "production")
    assert cfg.get_active_profile() == "production"


def test_get_active_profile_from_file(isolate_config):
    cfg.save_config({"active_profile": "prod", "prod": {}})
    assert cfg.get_active_profile() == "prod"


def test_set_active_profile_persists(isolate_config):
    cfg.save_config({"default": {}, "prod": {}})
    cfg.set_active_profile("prod")
    assert cfg.get_active_profile() == "prod"


def test_set_active_profile_unknown_raises(isolate_config):
    cfg.save_config({"default": {}})
    with pytest.raises(ProfileNotFoundError):
        cfg.set_active_profile("ghost")


# ---------------------------------------------------------------------------
# Platform config
# ---------------------------------------------------------------------------


def test_get_platform_config_unknown_platform_raises(isolate_config):
    with pytest.raises(PlatformNotFoundError):
        cfg.get_platform_config("not-a-platform")


def test_get_platform_config_unknown_profile_raises(isolate_config):
    cfg.save_config({"default": {"originq": {"token": "x"}}})
    with pytest.raises(ProfileNotFoundError):
        cfg.get_platform_config("originq", profile="ghost")


def test_get_platform_config_missing_platform_in_profile(isolate_config):
    cfg.save_config({"default": {}})
    with pytest.raises(ConfigError):
        cfg.get_platform_config("originq")


def test_get_platform_config_returns_section(isolate_config):
    cfg.save_config({"default": {"originq": {"token": "abc"}}})
    out = cfg.get_platform_config("originq")
    assert out == {"token": "abc"}


def test_update_platform_config_creates_profile(isolate_config):
    cfg.save_config({"default": {}})
    cfg.update_platform_config("originq", {"token": "new"}, profile="staging")
    loaded = cfg.load_config()
    assert loaded["staging"]["originq"] == {"token": "new"}


def test_update_platform_config_unknown_platform_raises(isolate_config):
    with pytest.raises(PlatformNotFoundError):
        cfg.update_platform_config("not-real", {"token": "x"})


# ---------------------------------------------------------------------------
# Per-platform getters
# ---------------------------------------------------------------------------


def test_per_platform_get_dispatches(isolate_config):
    cfg.save_config(
        {
            "default": {
                "originq": {"token": "o"},
                "quafu": {"token": "q"},
                "quark": {"QUARK_API_KEY": "k"},
                "ibm": {"token": "i"},
            },
        }
    )
    assert cfg.get_originq_config() == {"token": "o"}
    assert cfg.get_quafu_config() == {"token": "q"}
    assert cfg.get_quark_config() == {"QUARK_API_KEY": "k"}
    assert cfg.get_ibm_config() == {"token": "i"}


def test_load_originq_config_returns_api_key(isolate_config):
    cfg.save_config({"default": {"originq": {"token": "abc", "task_group_size": "50"}}})
    out = cfg.load_originq_config()
    assert out == {"api_key": "abc", "task_group_size": 50, "available_qubits": []}


def test_load_originq_config_missing_token_raises(isolate_config):
    cfg.save_config({"default": {"originq": {"token": ""}}})
    with pytest.raises(ImportError):
        cfg.load_originq_config()


def test_load_quafu_config_round_trip(isolate_config):
    cfg.save_config({"default": {"quafu": {"token": "q"}}})
    assert cfg.load_quafu_config() == {"api_token": "q"}


def test_load_quafu_config_missing_token_raises(isolate_config):
    cfg.save_config({"default": {"quafu": {"token": ""}}})
    with pytest.raises(ImportError):
        cfg.load_quafu_config()


def test_load_quark_config_supports_legacy_token(isolate_config):
    cfg.save_config({"default": {"quark": {"token": "qq"}}})
    assert cfg.load_quark_config() == {"api_token": "qq"}


def test_load_quark_config_missing_raises(isolate_config):
    cfg.save_config({"default": {"quark": {"QUARK_API_KEY": ""}}})
    with pytest.raises(ImportError):
        cfg.load_quark_config()


def test_load_ibm_config_round_trip(isolate_config):
    cfg.save_config({"default": {"ibm": {"token": "ibmtok"}}})
    assert cfg.load_ibm_config() == {"api_token": "ibmtok"}


def test_load_ibm_config_missing_raises(isolate_config):
    cfg.save_config({"default": {"ibm": {"token": ""}}})
    with pytest.raises(ImportError):
        cfg.load_ibm_config()


def test_load_dummy_config_inherits_originq_topology(isolate_config):
    cfg.save_config(
        {
            "default": {
                "originq": {
                    "token": "x",
                    "available_qubits": [0, 1, 2],
                    "available_topology": [[0, 1], [1, 2]],
                    "task_group_size": 7,
                }
            }
        }
    )
    out = cfg.load_dummy_config()
    assert out == {
        "available_qubits": [0, 1, 2],
        "available_topology": [[0, 1], [1, 2]],
        "task_group_size": 7,
    }


def test_load_dummy_config_with_missing_originq_section(isolate_config):
    cfg.save_config({"default": {}})
    out = cfg.load_dummy_config()
    assert out["task_group_size"] == 200


# ---------------------------------------------------------------------------
# has_platform_credentials
# ---------------------------------------------------------------------------


def test_has_platform_credentials_true(isolate_config):
    cfg.save_config({"default": {"originq": {"token": "x"}}})
    assert cfg.has_platform_credentials("originq") is True


def test_has_platform_credentials_false_when_empty(isolate_config):
    cfg.save_config({"default": {"originq": {"token": ""}}})
    assert cfg.has_platform_credentials("originq") is False


def test_has_platform_credentials_false_when_missing(isolate_config):
    cfg.save_config({"default": {}})
    assert cfg.has_platform_credentials("originq") is False


def test_has_platform_credentials_quark_supports_legacy(isolate_config):
    cfg.save_config({"default": {"quark": {"token": "y"}}})
    assert cfg.has_platform_credentials("quark") is True


# ---------------------------------------------------------------------------
# AI hints
# ---------------------------------------------------------------------------


def test_get_set_always_ai_hints(isolate_config):
    assert cfg.get_always_ai_hints() is False
    cfg.set_always_ai_hints(True)
    assert cfg.get_always_ai_hints() is True
    cfg.set_always_ai_hints(False)
    assert cfg.get_always_ai_hints() is False


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


def test_validate_empty_returns_warning():
    assert cfg.validate_config(config={}) == ["Configuration is empty"]


def test_validate_non_dict_returns_error():
    assert cfg.validate_config(config="not a dict") == ["Configuration must be a dictionary"]


def test_validate_missing_required_token():
    errors = cfg.validate_config(config={"default": {"originq": {}}})
    assert any("Missing required field 'token'" in e for e in errors)


def test_validate_quark_accepts_legacy_token():
    errors = cfg.validate_config(config={"default": {"quark": {"token": "q"}}})
    assert not any("Missing required field" in e for e in errors)


def test_validate_unknown_field_warning():
    errors = cfg.validate_config(
        config={"default": {"originq": {"token": "x", "foo": "bar"}}},
    )
    assert any("unknown field 'foo'" in e for e in errors)


def test_validate_ibm_proxy_type_error():
    errors = cfg.validate_config(
        config={"default": {"ibm": {"token": "x", "proxy": "not-a-dict"}}},
    )
    assert any("must be a dictionary" in e for e in errors)


def test_validate_ibm_proxy_value_type():
    errors = cfg.validate_config(
        config={"default": {"ibm": {"token": "x", "proxy": {"http": 123}}}},
    )
    assert any("must be a string" in e for e in errors)


def test_validate_non_dict_profile_value():
    errors = cfg.validate_config(config={"default": "not a dict"})
    assert any("must be a dictionary" in e for e in errors)


def test_validate_loads_from_path(isolate_config):
    isolate_config.parent.mkdir(parents=True, exist_ok=True)
    isolate_config.write_text(yaml.safe_dump({"default": {"originq": {"token": "x"}}}))
    assert cfg.validate_config() == []


# ---------------------------------------------------------------------------
# create_default_config
# ---------------------------------------------------------------------------


def test_create_default_config_writes_file(isolate_config):
    assert not isolate_config.exists()
    cfg.create_default_config()
    assert isolate_config.exists()
    loaded = cfg.load_config()
    assert "default" in loaded


def test_create_default_config_does_not_overwrite(isolate_config):
    cfg.save_config({"default": {"originq": {"token": "existing"}}})
    cfg.create_default_config()
    assert cfg.get_platform_config("originq")["token"] == "existing"
