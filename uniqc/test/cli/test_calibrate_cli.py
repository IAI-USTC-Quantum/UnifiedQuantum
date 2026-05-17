"""Tests for the ``uniqc calibrate`` CLI subcommand.

XEB and readout calibration on the dummy backend run end-to-end here (no
network, no real hardware). Pattern analysis is a pure graph-colouring
problem and is exercised directly.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from uniqc.cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# `calibrate pattern`
# ---------------------------------------------------------------------------


def test_pattern_auto_default_qubits():
    result = runner.invoke(app, ["calibrate", "pattern"], env={"COLUMNS": "200"})
    assert result.exit_code == 0, result.output
    assert "Parallel Pattern Analysis" in result.output
    assert "Round" in result.output


def test_pattern_auto_with_custom_qubits():
    result = runner.invoke(
        app,
        ["calibrate", "pattern", "--qubits", "0", "--qubits", "1", "--qubits", "2"],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "Parallel rounds" in result.output


def test_pattern_circuit_mode_requires_file():
    result = runner.invoke(app, ["calibrate", "pattern", "--type", "circuit"])
    assert result.exit_code == 1
    assert "--circuit required" in result.output


def test_pattern_circuit_mode_missing_file(tmp_path):
    result = runner.invoke(
        app,
        ["calibrate", "pattern", "--type", "circuit", "--circuit", str(tmp_path / "nope.ir")],
    )
    assert result.exit_code == 1
    assert "not found" in result.output


def test_pattern_circuit_mode_reads_file(tmp_path):
    circuit = tmp_path / "bell.ir"
    circuit.write_text(
        """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["calibrate", "pattern", "--type", "circuit", "--circuit", str(circuit)],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "Parallel Pattern Analysis" in result.output


def test_pattern_writes_output_json(tmp_path):
    out_file = tmp_path / "pattern.json"
    result = runner.invoke(
        app,
        ["calibrate", "pattern", "--output", str(out_file)],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out_file.read_text())
    assert "n_rounds" in data
    assert "groups" in data


# ---------------------------------------------------------------------------
# `calibrate xeb`
# ---------------------------------------------------------------------------


def _stub_xeb(monkeypatch):
    """Stub xeb_workflow runs to return cheap fake results — XEB is expensive."""
    from uniqc.algorithms.workflows import xeb_workflow
    from uniqc.calibration.results import XEBResult

    fake_1q = {
        0: XEBResult(
            calibrated_at="2026-05-01T00:00:00Z",
            backend="dummy:local:simulator",
            type="xeb_1q",
            qubit=0,
            fidelity_per_layer=0.99,
            fidelity_std_error=0.001,
            fit_a=1.0,
            fit_b=0.0,
            fit_r=0.99,
            depths=(5, 10),
            n_circuits=10,
            shots=100,
        ),
    }
    fake_2q = {
        (0, 1): XEBResult(
            calibrated_at="2026-05-01T00:00:00Z",
            backend="dummy:local:simulator",
            type="xeb_2q",
            pairs=[(0, 1)],
            fidelity_per_layer=0.98,
            fidelity_std_error=0.002,
            fit_a=1.0,
            fit_b=0.0,
            fit_r=0.98,
            depths=(5, 10),
            n_circuits=10,
            shots=100,
        ),
    }
    monkeypatch.setattr(xeb_workflow, "run_1q_xeb_workflow", lambda **kw: fake_1q)
    monkeypatch.setattr(xeb_workflow, "run_2q_xeb_workflow", lambda **kw: fake_2q)


def test_xeb_default_runs_both_1q_and_2q(monkeypatch):
    _stub_xeb(monkeypatch)
    result = runner.invoke(
        app,
        ["calibrate", "xeb", "--qubits", "0", "--qubits", "1", "--depths", "5", "--depths", "10"],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "XEB complete" in result.output
    assert "Qubit 0" in result.output
    assert "Pair" in result.output


def test_xeb_1q_only(monkeypatch):
    _stub_xeb(monkeypatch)
    result = runner.invoke(
        app,
        [
            "calibrate",
            "xeb",
            "--type",
            "1q",
            "--qubits",
            "0",
            "--qubits",
            "1",
            "--depths",
            "5",
        ],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "Running 1q XEB" in result.output
    assert "Running 2q XEB" not in result.output


def test_xeb_writes_output(monkeypatch, tmp_path):
    _stub_xeb(monkeypatch)
    out = tmp_path / "xeb.json"
    result = runner.invoke(
        app,
        [
            "calibrate",
            "xeb",
            "--type",
            "1q",
            "--qubits",
            "0",
            "--depths",
            "5",
            "--output",
            str(out),
        ],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert "1q" in data


def test_xeb_pattern_circuit_mode(tmp_path):
    circuit = tmp_path / "c.ir"
    circuit.write_text(
        """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
""",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["calibrate", "xeb", "--pattern", "circuit", "--circuit", str(circuit)],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "Circuit pattern" in result.output


def test_xeb_pattern_circuit_missing_file_arg():
    result = runner.invoke(app, ["calibrate", "xeb", "--pattern", "circuit"])
    assert result.exit_code == 1
    assert "--circuit required" in result.output


def test_xeb_failure_exits_1(monkeypatch):
    from uniqc.algorithms.workflows import xeb_workflow

    def _boom(**kw):
        raise RuntimeError("xeb failed in test")

    monkeypatch.setattr(xeb_workflow, "run_1q_xeb_workflow", _boom)
    monkeypatch.setattr(xeb_workflow, "run_2q_xeb_workflow", _boom)

    result = runner.invoke(
        app,
        ["calibrate", "xeb", "--type", "1q", "--qubits", "0", "--depths", "5"],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 1
    assert "XEB failed" in result.output


# ---------------------------------------------------------------------------
# `calibrate readout`
# ---------------------------------------------------------------------------


def _stub_readout(monkeypatch):
    from uniqc.calibration.readout import calibrator as calibrator_mod

    class _FakeCalibrator:
        def __init__(self, **kwargs):
            pass

        def calibrate_1q(self, qubit):
            return {"assignment_fidelity": 0.97, "qubit": qubit}

        def calibrate_2q(self, qu, qv):
            return {"assignment_fidelity": 0.95, "qubits": (qu, qv)}

    monkeypatch.setattr(calibrator_mod, "ReadoutCalibrator", _FakeCalibrator)


def test_readout_default(monkeypatch):
    _stub_readout(monkeypatch)
    result = runner.invoke(
        app,
        ["calibrate", "readout", "--qubits", "0", "--qubits", "1"],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "Readout calibration complete" in result.output
    assert "Qubit 0" in result.output


def test_readout_1q_only(monkeypatch):
    _stub_readout(monkeypatch)
    result = runner.invoke(
        app,
        ["calibrate", "readout", "--type", "1q", "--qubits", "0"],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    assert "Calibrating 1q readout" in result.output
    assert "Calibrating 2q readout" not in result.output


def test_readout_writes_output(monkeypatch, tmp_path):
    _stub_readout(monkeypatch)
    out = tmp_path / "ro.json"
    result = runner.invoke(
        app,
        [
            "calibrate",
            "readout",
            "--type",
            "1q",
            "--qubits",
            "0",
            "--qubits",
            "1",
            "--output",
            str(out),
        ],
        env={"COLUMNS": "200"},
    )
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert "1q_q0" in data
    assert "1q_q1" in data
