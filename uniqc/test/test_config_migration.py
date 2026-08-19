"""Tests for config.yaml schema versioning and automatic migration."""

from __future__ import annotations

import pytest
import yaml

import uniqc.config as cfg


@pytest.fixture()
def config_path(tmp_path, monkeypatch):
    path = tmp_path / ".uniqc" / "config.yaml"
    monkeypatch.setattr(cfg, "CONFIG_FILE", path)
    return path


def test_default_config_carries_current_version():
    assert cfg.DEFAULT_CONFIG[cfg.CONFIG_VERSION_KEY] == cfg.CURRENT_CONFIG_VERSION


def test_version_key_is_a_meta_key():
    assert cfg.CONFIG_VERSION_KEY in cfg.META_KEYS


def test_load_legacy_unversioned_config_migrates_and_persists(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text("default:\n  originq:\n    token: abc\n", encoding="utf-8")

    config = cfg.load_config()
    assert config[cfg.CONFIG_VERSION_KEY] == cfg.CURRENT_CONFIG_VERSION
    # User data is preserved
    assert config["default"]["originq"]["token"] == "abc"

    # The migration is written back to disk
    on_disk = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert on_disk[cfg.CONFIG_VERSION_KEY] == cfg.CURRENT_CONFIG_VERSION
    assert on_disk["default"]["originq"]["token"] == "abc"


def test_load_current_version_config_is_untouched(config_path):
    config_path.parent.mkdir(parents=True)
    original = f"{cfg.CONFIG_VERSION_KEY}: {cfg.CURRENT_CONFIG_VERSION}\ndefault:\n  originq:\n    token: abc\n"
    config_path.write_text(original, encoding="utf-8")

    config = cfg.load_config()
    assert config[cfg.CONFIG_VERSION_KEY] == cfg.CURRENT_CONFIG_VERSION
    assert config_path.read_text(encoding="utf-8") == original


def test_load_newer_version_raises(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(f"{cfg.CONFIG_VERSION_KEY}: {cfg.CURRENT_CONFIG_VERSION + 1}\n", encoding="utf-8")

    with pytest.raises(cfg.ConfigError, match="newer than this uniqc supports"):
        cfg.load_config()


def test_invalid_version_raises(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(f"{cfg.CONFIG_VERSION_KEY}: not-a-number\n", encoding="utf-8")

    with pytest.raises(cfg.ConfigError, match="Invalid 'config_version'"):
        cfg.load_config()


def test_migrate_config_stamps_version_on_legacy_dict():
    legacy = {"default": {"originq": {"token": "abc"}}}
    migrated = cfg.migrate_config(legacy)
    assert migrated[cfg.CONFIG_VERSION_KEY] == cfg.CURRENT_CONFIG_VERSION
    assert migrated["default"]["originq"]["token"] == "abc"


def test_validate_config_ignores_version_key():
    errors = cfg.validate_config(
        {
            cfg.CONFIG_VERSION_KEY: cfg.CURRENT_CONFIG_VERSION,
            "default": {"originq": {"token": "abc"}},
        }
    )
    assert not any(cfg.CONFIG_VERSION_KEY in e for e in errors)
