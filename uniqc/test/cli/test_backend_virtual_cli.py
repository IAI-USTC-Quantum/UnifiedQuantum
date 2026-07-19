"""Tests for the ``uniqc backend virtual`` CLI subcommands."""

from __future__ import annotations

from typer.testing import CliRunner

from uniqc.backend_adapter import virtual_machine as vm
from uniqc.cli.main import app

runner = CliRunner()


def test_init_validate_list_show(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "DEFAULT_VIRTUAL_DIR", tmp_path)

    result = runner.invoke(app, ["backend", "virtual", "init", "demo"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "demo.yaml").exists()

    result = runner.invoke(app, ["backend", "virtual", "init", "demo"])
    assert result.exit_code == 1
    assert "already exists" in result.output

    result = runner.invoke(app, ["backend", "virtual", "init", "demo", "--force"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["backend", "virtual", "validate", "demo"])
    assert result.exit_code == 0, result.output
    assert "valid" in result.output

    result = runner.invoke(app, ["backend", "virtual", "list"])
    assert result.exit_code == 0, result.output
    assert "demo" in result.output

    result = runner.invoke(app, ["backend", "virtual", "show", "demo"])
    assert result.exit_code == 0, result.output
    assert "virtual:demo" in result.output
    assert "dummy:virtual:demo" in result.output


def test_init_rejects_bad_name(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "DEFAULT_VIRTUAL_DIR", tmp_path)

    result = runner.invoke(app, ["backend", "virtual", "init", "bad/name"])
    assert result.exit_code == 1
    assert "Invalid virtual machine name" in result.output


def test_validate_reports_invalid_config(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "DEFAULT_VIRTUAL_DIR", tmp_path)
    (tmp_path / "broken.yaml").write_text("num_qubits: 2\ntopology:\n  - [0, 9]\n", encoding="utf-8")

    result = runner.invoke(app, ["backend", "virtual", "validate", "broken"])
    assert result.exit_code == 1
    assert "undeclared qubit 9" in result.output

    result = runner.invoke(app, ["backend", "virtual", "list"])
    assert result.exit_code == 0, result.output
    assert "invalid" in result.output


def test_validate_missing_config(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "DEFAULT_VIRTUAL_DIR", tmp_path)

    result = runner.invoke(app, ["backend", "virtual", "validate", "absent"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_list_empty_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "DEFAULT_VIRTUAL_DIR", tmp_path)

    result = runner.invoke(app, ["backend", "virtual", "list"])
    assert result.exit_code == 0, result.output
    assert "No virtual machines" in result.output
