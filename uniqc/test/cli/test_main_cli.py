"""Regression tests for top-level uniqc CLI command parsing."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from uniqc.cli import result as result_module
from uniqc.cli import simulate as simulate_module
from uniqc.cli import submit as submit_module
from uniqc.cli.main import app

runner = CliRunner()


def _write_originir(path: Path) -> None:
    path.write_text(
        """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""",
        encoding="utf-8",
    )


def test_circuit_accepts_options_after_input_file(tmp_path: Path):
    input_file = tmp_path / "bell.ir"
    _write_originir(input_file)

    result = runner.invoke(app, ["circuit", str(input_file), "--info"])

    assert result.exit_code == 0, result.stdout
    assert "Circuit Info" in result.stdout
    assert "OPENQASM 2.0;" in result.stdout


def test_simulate_accepts_options_after_input_file(tmp_path: Path, monkeypatch):
    input_file = tmp_path / "bell.ir"
    _write_originir(input_file)

    monkeypatch.setattr(
        simulate_module,
        "_run_simulation",
        lambda content, backend, shots: {"00": 0.5, "11": 0.5},
    )

    result = runner.invoke(app, ["simulate", str(input_file), "--shots", "16"])

    assert result.exit_code == 0, result.stdout
    assert "Simulation Results" in result.stdout
    assert "00" in result.stdout
    assert "11" in result.stdout


def test_submit_accepts_options_after_input_files(tmp_path: Path, monkeypatch):
    input_file = tmp_path / "bell.ir"
    _write_originir(input_file)

    seen: dict[str, object] = {}

    def fake_submit_single(circuit: str, platform: str, backend_name: str | None, shots: int, name: str | None) -> str:
        seen["platform"] = platform
        seen["backend_name"] = backend_name
        seen["shots"] = shots
        seen["name"] = name
        seen["circuit"] = circuit
        return "task-123"

    monkeypatch.setattr(submit_module, "_submit_single", fake_submit_single)

    result = runner.invoke(app, ["submit", str(input_file), "--platform", "dummy"])

    assert result.exit_code == 0, result.stdout
    assert "task-123" in result.stdout
    assert seen["platform"] == "dummy"
    assert isinstance(seen["circuit"], str)


def test_submit_dry_run_failure_exits_nonzero(tmp_path: Path, monkeypatch):
    input_file = tmp_path / "bell.ir"
    _write_originir(input_file)

    monkeypatch.setattr(submit_module, "_handle_dry_run", lambda *args, **kwargs: False)

    result = runner.invoke(app, ["submit", str(input_file), "--platform", "dummy", "--dry-run"])

    assert result.exit_code == 1


def test_submit_parse_originir_preserves_measurements(tmp_path: Path):
    input_file = tmp_path / "bell.ir"
    _write_originir(input_file)

    circuit = submit_module._parse_to_circuit(input_file.read_text(encoding="utf-8"))

    assert circuit.cbit_num == 2
    assert circuit.measure_list == [0, 1]
    assert "MEASURE q[0], c[0]" in circuit.originir
    assert "MEASURE q[1], c[1]" in circuit.originir


def test_result_accepts_options_after_task_id(monkeypatch):
    seen: dict[str, object] = {}

    def fake_show_result(
        task_id: str,
        platform: str | None = None,
        wait: bool = False,
        timeout: float = 300.0,
        format: str = "table",
    ) -> None:
        seen["task_id"] = task_id
        seen["platform"] = platform
        seen["wait"] = wait
        seen["timeout"] = timeout
        seen["format"] = format

    monkeypatch.setattr(result_module, "show_result", fake_show_result)

    result = runner.invoke(app, ["result", "task-123", "--wait", "--timeout", "1"])

    assert result.exit_code == 0, result.stdout
    assert seen == {
        "task_id": "task-123",
        "platform": None,
        "wait": True,
        "timeout": 1.0,
        "format": "table",
    }
