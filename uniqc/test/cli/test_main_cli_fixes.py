"""Regression tests for 4 CLI / parser bugs.

These tests lock the expected behavior of the following fixes:

1. ``OpenQASM2_BaseParser.to_originir()`` must preserve ``MEASURE`` lines.
2. ``uniqc simulate`` must accept OpenQASM 2.0 input (not only OriginIR).
3. ``uniqc task show`` / ``uniqc result`` must tolerate the real
   ``TaskInfo.result`` shapes (nested counts/probabilities, originq
   key/value list, etc.), not only flat ``{state: count}`` dicts.
4. ``uniqc config profile list`` must not list the top-level
   ``active_profile`` meta key as if it were a profile.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from uniqc.backend_adapter.task_manager import TaskInfo, TaskStatus
from uniqc.cli.main import app

runner = CliRunner()


def _write_qasm(path: Path) -> None:
    path.write_text(
        """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
""",
        encoding="utf-8",
    )


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


# ---------------------------------------------------------------------------
# Bug 1: QASM -> OriginIR must preserve MEASURE statements
# ---------------------------------------------------------------------------


def test_qasm_to_originir_preserves_measurements():
    from uniqc.compile.qasm import OpenQASM2_BaseParser

    qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""
    parser = OpenQASM2_BaseParser()
    parser.parse(qasm_str)
    originir = parser.to_originir()

    assert "MEASURE q[0], c[0]" in originir
    assert "MEASURE q[1], c[1]" in originir


def test_qasm_to_originir_accepts_comma_measurements():
    from uniqc.compile.qasm import OpenQASM2_BaseParser

    qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q[0], c[0];
measure q[1],c[1];
"""
    parser = OpenQASM2_BaseParser()
    parser.parse(qasm_str)
    originir = parser.to_originir()

    assert "MEASURE q[0], c[0]" in originir
    assert "MEASURE q[1], c[1]" in originir


def test_circuit_cli_qasm_to_originir_preserves_measurements(tmp_path: Path):
    input_file = tmp_path / "bell.qasm"
    _write_qasm(input_file)

    result = runner.invoke(app, ["circuit", str(input_file), "--format", "originir"])

    assert result.exit_code == 0, result.stdout
    assert "MEASURE q[0], c[0]" in result.stdout
    assert "MEASURE q[1], c[1]" in result.stdout


# ---------------------------------------------------------------------------
# Bug 2: `uniqc simulate` must accept QASM input
# ---------------------------------------------------------------------------


def test_simulate_accepts_qasm_input(tmp_path: Path):
    from uniqc.cli.simulate import _run_simulation

    qasm_str = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
"""
    # Must not raise (previously the OriginIR parser rejected OPENQASM 2.0;).
    results = _run_simulation(qasm_str, backend="statevector", shots=16)

    assert isinstance(results, dict)
    assert set(results.keys()).issubset({"00", "01", "10", "11"})
    total = sum(results.values())
    assert total == pytest.approx(1.0, rel=1e-6)


def test_simulate_accepts_originir_input(tmp_path: Path):
    """Sanity check: OriginIR path must keep working after the QASM branch."""
    from uniqc.cli.simulate import _run_simulation

    originir = """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
"""
    results = _run_simulation(originir, backend="statevector", shots=16)

    assert isinstance(results, dict)
    assert set(results.keys()).issubset({"00", "01", "10", "11"})


# ---------------------------------------------------------------------------
# Bug 3: task show / uniqc result must tolerate nested result shapes
# ---------------------------------------------------------------------------


def test_task_show_tolerates_nested_result(monkeypatch):
    """Dummy / quafu write result={'counts': ..., 'probabilities': ...}.

    Before the fix, CLI did sum(result.values()) which raised TypeError.
    """
    task_info = TaskInfo(
        task_id="dummy-abc",
        backend="dummy:originq",
        status=TaskStatus.SUCCESS,
        shots=1000,
        result={
            "counts": {"00": 512, "11": 488},
            "probabilities": {"00": 0.512, "11": 0.488},
        },
    )

    monkeypatch.setattr("uniqc.backend_adapter.task_manager.get_task", lambda _tid: task_info)
    monkeypatch.setattr("uniqc.backend_adapter.task_manager.query_task", lambda _tid: task_info)

    result = runner.invoke(app, ["task", "show", "dummy-abc"])

    assert result.exit_code == 0, result.stdout
    assert "dummy-abc" in result.stdout
    assert "00" in result.stdout
    assert "11" in result.stdout
    assert "512" in result.stdout
    assert "488" in result.stdout


def test_uniqc_result_tolerates_nested_result(monkeypatch):
    """`uniqc result` table mode must handle the same nested shape."""
    task_info = TaskInfo(
        task_id="dummy-xyz",
        backend="dummy:originq",
        status=TaskStatus.SUCCESS,
        shots=1000,
        result={
            "counts": {"00": 512, "11": 488},
            "probabilities": {"00": 0.512, "11": 0.488},
        },
    )

    from uniqc.cli import result as result_module

    monkeypatch.setattr(result_module, "_query_result", lambda *_a, **_k: task_info.result)

    result = runner.invoke(app, ["result", "dummy-xyz"])

    assert result.exit_code == 0, result.stdout
    assert "00" in result.stdout
    assert "11" in result.stdout


# ---------------------------------------------------------------------------
# Bug 4: `uniqc config profile list` must not show active_profile meta key
# ---------------------------------------------------------------------------


def test_profile_list_hides_meta_keys(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", config_file)

    from uniqc.config import save_config

    save_config(
        {
            "active_profile": "default",
            "default": {"originq": {"token": ""}},
            "prod": {"originq": {"token": "xxx"}},
        },
        config_path=config_file,
    )

    result = runner.invoke(app, ["config", "profile", "list"])

    assert result.exit_code == 0, result.stdout
    # The two real profiles appear as rows...
    assert "default" in result.stdout
    assert "prod" in result.stdout
    # ... but the meta key must not show up as a profile.
    assert "active_profile" not in result.stdout


def test_config_set_preserves_existing_platform_fields(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", config_file)

    from uniqc.config import get_platform_config, save_config

    save_config(
        {
            "default": {
                "ibm": {
                    "token": "old-token",
                    "proxy": {"http": "", "https": "http://proxy:8080"},
                }
            }
        },
        config_path=config_file,
    )

    result = runner.invoke(app, ["config", "set", "ibm.token", "new-token"])

    assert result.exit_code == 0, result.stdout
    ibm = get_platform_config("ibm", config_path=config_file)
    assert ibm["token"] == "new-token"
    assert ibm["proxy"]["https"] == "http://proxy:8080"


def test_config_set_supports_nested_ibm_proxy(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", config_file)

    from uniqc.config import get_platform_config, save_config

    save_config({"default": {"ibm": {"token": "token"}}}, config_path=config_file)

    result = runner.invoke(app, ["config", "set", "ibm.proxy.https", "http://127.0.0.1:7890"])

    assert result.exit_code == 0, result.stdout
    ibm = get_platform_config("ibm", config_path=config_file)
    assert ibm["token"] == "token"
    assert ibm["proxy"]["https"] == "http://127.0.0.1:7890"


def test_config_always_ai_hint_enables_hints_by_default(tmp_path: Path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    monkeypatch.setattr("uniqc.config.CONFIG_FILE", config_file)

    result = runner.invoke(app, ["config", "always-ai-hint", "on"])
    assert result.exit_code == 0, result.stdout

    result = runner.invoke(app, ["config", "list", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    assert "AI Workflow Hints" in result.stdout
