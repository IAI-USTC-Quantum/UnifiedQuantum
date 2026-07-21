"""Tests for the ``uniqc doctor`` CLI subcommand."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from uniqc.backend_adapter.backend_info import BackendInfo, Platform
from uniqc.cli import doctor as doctor_cli
from uniqc.cli.chip_info import ChipCharacterization, ChipGlobalInfo
from uniqc.cli.main import app

runner = CliRunner()


def _isolate_config(monkeypatch, tmp_path: Path) -> Path:
    """Point uniqc at a fresh, empty config dir."""
    cfg_dir = tmp_path / ".uniqc"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.yaml"
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", cfg_file)
    return cfg_file


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------


def test_doctor_check_environment_prints_uniqc_version(capsys):
    doctor_cli._check_environment()
    captured = capsys.readouterr()
    assert "uniqc" in captured.out.lower()
    assert "Python" in captured.out


def test_doctor_check_dependencies_lists_core_and_optional(capsys):
    doctor_cli._check_dependencies()
    captured = capsys.readouterr()
    assert "numpy" in captured.out
    # At least one optional group label present
    assert any(group in captured.out for group, _ in doctor_cli._DEPENDENCY_GROUPS)


def test_doctor_check_config_missing_file(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / ".uniqc" / "config.yaml"  # does NOT exist
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", cfg)

    doctor_cli._check_config()
    out = capsys.readouterr().out
    assert "not found" in out


def test_doctor_check_config_with_credentials(tmp_path, monkeypatch, capsys):
    cfg = _isolate_config(monkeypatch, tmp_path)
    cfg.write_text(
        """active_profile: default
default:
  originq:
    token: aabbccddeeff112233
""",
        encoding="utf-8",
    )
    doctor_cli._check_config()
    out = capsys.readouterr().out
    assert "valid" in out.lower() or "Configuration" in out
    assert "configured" in out
    # Token must be fully masked, including its prefix.
    assert "aabbccddeeff112233" not in out
    assert "aabbcc" not in out


def test_doctor_check_task_db_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("uniqc.backend_adapter.task.store.DEFAULT_CACHE_DIR", tmp_path)
    doctor_cli._check_task_db()
    out = capsys.readouterr().out
    assert "not found" in out


def test_doctor_check_task_db_existing(tmp_path, monkeypatch, capsys):
    from uniqc.backend_adapter.task.store import APPLICATION_ID, DB_FILENAME

    monkeypatch.setattr("uniqc.backend_adapter.task.store.DEFAULT_CACHE_DIR", tmp_path)
    db = tmp_path / DB_FILENAME

    conn = sqlite3.connect(db)
    try:
        conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        conn.execute("PRAGMA user_version = 1")
        conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO tasks (id) VALUES ('demo-1')")
        conn.commit()
    finally:
        conn.close()

    doctor_cli._check_task_db()
    out = capsys.readouterr().out
    assert "application_id" in out
    assert "Task count: 1" in out


def test_doctor_check_backend_cache_empty(monkeypatch, capsys):
    monkeypatch.setattr("uniqc.backend_adapter.backend_cache.cache_info", lambda: {})
    doctor_cli._check_backend_cache()
    out = capsys.readouterr().out
    assert "empty" in out.lower()


def test_doctor_check_backend_cache_populated(monkeypatch, capsys):
    monkeypatch.setattr(
        "uniqc.backend_adapter.backend_cache.cache_info",
        lambda: {
            "originq": {"num_backends": 4, "age_seconds": 120, "is_stale": False},
            "ibm": {"num_backends": 9, "age_seconds": 86400 * 2, "is_stale": True},
        },
    )
    doctor_cli._check_backend_cache()
    out = capsys.readouterr().out
    assert "originq" in out
    assert "ibm" in out


def test_doctor_check_platform_connectivity_no_credentials(monkeypatch, capsys):
    monkeypatch.setattr("uniqc.config.has_platform_credentials", lambda p: False)
    doctor_cli._check_platform_connectivity()
    out = capsys.readouterr().out
    assert "No platform credentials" in out


def test_doctor_check_platform_connectivity_with_calibration(monkeypatch, capsys):
    monkeypatch.setattr(
        "uniqc.config.has_platform_credentials",
        lambda p: p == "originq",
    )
    backend_info = BackendInfo(
        platform=Platform.ORIGINQ,
        name="wuyuan",
        num_qubits=72,
        is_hardware=True,
        status="available",
    )
    monkeypatch.setattr(
        "uniqc.backend_adapter.backend_registry.fetch_platform_backends",
        lambda plat, force_refresh=False: ([backend_info], True),
    )

    chip = ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="wuyuan",
        full_id="originq:wuyuan",
        available_qubits=(0, 1),
        connectivity=(),
        single_qubit_data=(),
        two_qubit_data=(),
        global_info=ChipGlobalInfo(),
        calibrated_at="2026-05-01T00:00:00Z",
    )
    monkeypatch.setattr(
        "uniqc.cli.chip_service.fetch_chip_characterization",
        lambda name, platform, force_refresh=False: chip,
    )

    doctor_cli._check_platform_connectivity()
    out = capsys.readouterr().out
    assert "originq" in out
    # Should detect empty calibration arrays as warnings
    assert "empty" in out


def test_doctor_check_platform_connectivity_handles_fetch_failure(monkeypatch, capsys):
    monkeypatch.setattr("uniqc.config.has_platform_credentials", lambda p: p == "originq")

    def _boom(plat, force_refresh=False):
        raise RuntimeError("network down")

    monkeypatch.setattr("uniqc.backend_adapter.backend_registry.fetch_platform_backends", _boom)

    doctor_cli._check_platform_connectivity()
    out = capsys.readouterr().out
    assert "Failed" in out


def test_doctor_mask_key():
    assert doctor_cli._mask_key("short") == "****"
    assert doctor_cli._mask_key("abcdef1234567890") == "****"


def test_doctor_import_version():
    # numpy is a hard dep
    assert doctor_cli._import_version("numpy") != "not installed"
    assert doctor_cli._import_version("definitely_not_a_real_package_xyz") == "not installed"


# ---------------------------------------------------------------------------
# End-to-end command invocation
# ---------------------------------------------------------------------------


def test_doctor_command_runs_all_sections(monkeypatch, tmp_path):
    _isolate_config(monkeypatch, tmp_path)
    monkeypatch.setattr("uniqc.backend_adapter.task.store.DEFAULT_CACHE_DIR", tmp_path)
    monkeypatch.setattr("uniqc.backend_adapter.backend_cache.cache_info", lambda: {})

    result = runner.invoke(app, ["doctor"], env={"COLUMNS": "200"})

    assert result.exit_code == 0, result.output
    assert "Environment" in result.output
    assert "Dependencies" in result.output
    assert "Config" in result.output
    assert "Task Database" in result.output
    assert "Backend Cache" in result.output
    assert "Done" in result.output
