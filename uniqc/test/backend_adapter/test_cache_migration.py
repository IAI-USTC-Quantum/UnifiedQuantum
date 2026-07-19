"""Tests for the one-time legacy cache migration into ``~/.uniqc/backend/``."""

from __future__ import annotations

import json
import time

from uniqc.backend_adapter import backend_cache as bc
from uniqc.backend_adapter.backend_info import Platform
from uniqc.cli import chip_cache as cc
from uniqc.cli.chip_info import ChipCharacterization


def _redirect_backend_cache(tmp_path, monkeypatch, *, guard_passes: bool = True):
    legacy_dir = tmp_path / "legacy-cache"
    new_dir = tmp_path / "new-backend"
    legacy_dir.mkdir()
    monkeypatch.setattr(bc, "LEGACY_CACHE_DIR", legacy_dir)
    monkeypatch.setattr(bc, "DEFAULT_CACHE_DIR", new_dir)
    monkeypatch.setattr(bc, "_BUILTIN_CACHE_DIR", new_dir if guard_passes else tmp_path / "builtin")
    monkeypatch.setattr(bc, "_migration_attempted", False)
    return legacy_dir, new_dir


def _redirect_chip_cache(tmp_path, monkeypatch, *, guard_passes: bool = True):
    legacy_dir = tmp_path / "legacy-chips"
    new_dir = tmp_path / "new-chips"
    legacy_dir.mkdir()
    monkeypatch.setattr(cc, "LEGACY_CACHE_DIR", legacy_dir)
    monkeypatch.setattr(cc, "DEFAULT_CACHE_DIR", new_dir)
    monkeypatch.setattr(cc, "_BUILTIN_CACHE_DIR", new_dir if guard_passes else tmp_path / "builtin")
    monkeypatch.setattr(cc, "_migration_attempted", False)
    return legacy_dir, new_dir


def test_backend_cache_migrates_legacy_file(tmp_path, monkeypatch):
    legacy_dir, new_dir = _redirect_backend_cache(tmp_path, monkeypatch)
    payload = {"originq": {"updated_at": time.time(), "backends": []}}
    (legacy_dir / "backends.json").write_text(json.dumps(payload), encoding="utf-8")

    info = bc.cache_info()

    assert "originq" in info
    assert not (legacy_dir / "backends.json").exists()
    assert (new_dir / "backends.json").exists()


def test_backend_cache_migration_is_idempotent(tmp_path, monkeypatch):
    legacy_dir, new_dir = _redirect_backend_cache(tmp_path, monkeypatch)
    payload = {"originq": {"updated_at": time.time(), "backends": []}}
    (legacy_dir / "backends.json").write_text(json.dumps(payload), encoding="utf-8")

    bc.cache_info()
    bc.cache_info()  # second call must not fail or re-move

    assert (new_dir / "backends.json").exists()


def test_backend_cache_keeps_new_file_when_both_exist(tmp_path, monkeypatch):
    legacy_dir, new_dir = _redirect_backend_cache(tmp_path, monkeypatch)
    new_dir.mkdir()
    (legacy_dir / "backends.json").write_text(json.dumps({"originq": {"updated_at": 1, "backends": []}}))
    fresh = {"ibm": {"updated_at": time.time(), "backends": []}}
    (new_dir / "backends.json").write_text(json.dumps(fresh), encoding="utf-8")

    info = bc.cache_info()

    assert set(info) == {"ibm"}
    assert (legacy_dir / "backends.json").exists()  # legacy left in place


def test_backend_cache_migration_guard_blocks_redirected_dir(tmp_path, monkeypatch):
    legacy_dir, _ = _redirect_backend_cache(tmp_path, monkeypatch, guard_passes=False)
    (legacy_dir / "backends.json").write_text(json.dumps({}), encoding="utf-8")

    bc.cache_info()

    assert (legacy_dir / "backends.json").exists()  # never moved


def test_chip_cache_migrates_legacy_files(tmp_path, monkeypatch):
    legacy_dir, new_dir = _redirect_chip_cache(tmp_path, monkeypatch)
    chip = ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="X",
        full_id="originq:X",
        available_qubits=(0, 1),
    )
    (legacy_dir / "originq-X.json").write_text(json.dumps(chip.to_dict()), encoding="utf-8")
    (legacy_dir / "README.txt").write_text("not a chip file", encoding="utf-8")

    loaded = cc.get_chip(Platform.ORIGINQ, "X")

    assert loaded is not None and loaded.chip_name == "X"
    assert (new_dir / "originq-X.json").exists()
    # Non-JSON leftovers keep the legacy directory alive.
    assert (legacy_dir / "README.txt").exists()


def test_chip_cache_migration_removes_empty_legacy_dir(tmp_path, monkeypatch):
    legacy_dir, new_dir = _redirect_chip_cache(tmp_path, monkeypatch)
    chip = ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="X",
        full_id="originq:X",
        available_qubits=(0, 1),
    )
    (legacy_dir / "originq-X.json").write_text(json.dumps(chip.to_dict()), encoding="utf-8")

    cc.get_chip(Platform.ORIGINQ, "X")

    assert not legacy_dir.exists()
    assert (new_dir / "originq-X.json").exists()


def test_chip_cache_migration_guard_blocks_redirected_dir(tmp_path, monkeypatch):
    legacy_dir, _ = _redirect_chip_cache(tmp_path, monkeypatch, guard_passes=False)
    chip = ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="X",
        full_id="originq:X",
        available_qubits=(0, 1),
    )
    (legacy_dir / "originq-X.json").write_text(json.dumps(chip.to_dict()), encoding="utf-8")

    assert cc.get_chip(Platform.ORIGINQ, "X") is None
    assert (legacy_dir / "originq-X.json").exists()  # never moved
