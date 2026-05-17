"""Tests for the ``uniqc backend`` CLI subcommand.

All cloud calls are stubbed via monkeypatch so this test module runs in CI
without credentials or network access.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
from uniqc.cli import backend as backend_cli
from uniqc.cli.chip_info import (
    ChipCharacterization,
    ChipGlobalInfo,
    SingleQubitData,
    TwoQubitData,
    TwoQubitGateData,
)
from uniqc.cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _fake_backends() -> dict[Platform, list[BackendInfo]]:
    return {
        Platform.ORIGINQ: [
            BackendInfo(
                platform=Platform.ORIGINQ,
                name="wuyuan",
                description="WK-C72 superconducting chip",
                num_qubits=72,
                topology=(QubitTopology(0, 1), QubitTopology(1, 2)),
                status="available",
                is_hardware=True,
                avg_1q_fidelity=0.998,
                avg_2q_fidelity=0.985,
            ),
            BackendInfo(
                platform=Platform.ORIGINQ,
                name="full_amplitude",
                num_qubits=30,
                status="available",
                is_simulator=True,
            ),
        ],
        Platform.IBM: [
            BackendInfo(
                platform=Platform.IBM,
                name="ibm_torino",
                num_qubits=133,
                status="unavailable",
                is_hardware=True,
            ),
        ],
    }


def _patch_registry(monkeypatch, backends: dict[Platform, list[BackendInfo]] | None = None) -> None:
    backends = backends if backends is not None else _fake_backends()

    def _fetch_all() -> dict[Platform, list[BackendInfo]]:
        return backends

    def _fetch_one(plat: Platform, force_refresh: bool = False):
        return backends.get(plat, []), True

    def _find(identifier: str) -> BackendInfo:
        for plat_list in backends.values():
            for b in plat_list:
                if b.full_id() == identifier or b.name == identifier:
                    return b
        raise ValueError(f"Backend not found: {identifier}")

    monkeypatch.setattr(backend_cli, "fetch_all_backends", _fetch_all)
    monkeypatch.setattr(backend_cli, "fetch_platform_backends", _fetch_one)
    monkeypatch.setattr(backend_cli, "find_backend", _find)
    monkeypatch.setattr(backend_cli, "cache_info", lambda: {})


# ---------------------------------------------------------------------------
# `backend list`
# ---------------------------------------------------------------------------


def test_backend_list_default_shows_available_backends(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list"])

    assert result.exit_code == 0, result.output
    assert "wuyuan" in result.output
    assert "full_amplitude" in result.output
    # ibm_torino is "unavailable" → filtered out by default
    assert "ibm_torino" not in result.output


def test_backend_list_all_includes_unavailable(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list", "--all"])

    assert result.exit_code == 0, result.output
    assert "ibm_torino" in result.output


def test_backend_list_filter_by_platform(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list", "--platform", "ibm", "--all"])

    assert result.exit_code == 0, result.output
    assert "ibm_torino" in result.output
    assert "wuyuan" not in result.output


def test_backend_list_unknown_platform_errors(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list", "--platform", "not-a-platform"])

    assert result.exit_code == 1
    assert "Unknown platform" in result.output


def test_backend_list_status_filter_simulator(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list", "--status", "simulator"])

    assert result.exit_code == 0, result.output
    assert "full_amplitude" in result.output
    assert "wuyuan" not in result.output


def test_backend_list_json_format(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = result.stdout[result.stdout.index("[") : result.stdout.rindex("]") + 1]
    data = json.loads(payload)
    names = {row["name"] for row in data}
    assert "wuyuan" in names


def test_backend_list_info_shows_fidelity(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "list", "--info"], env={"COLUMNS": "200"})

    assert result.exit_code == 0, result.output
    assert "0.998" in result.output


def test_backend_list_empty_returns_warning(monkeypatch):
    _patch_registry(monkeypatch, backends={})

    result = runner.invoke(app, ["backend", "list"])

    assert result.exit_code == 0
    assert "No backends found" in result.output


def test_backend_list_fetch_failure_exits_1(monkeypatch):
    def _boom():
        raise RuntimeError("network down")

    monkeypatch.setattr(backend_cli, "fetch_all_backends", _boom)

    result = runner.invoke(app, ["backend", "list"])

    assert result.exit_code == 1
    assert "Failed to fetch" in result.output


# ---------------------------------------------------------------------------
# `backend show` and `--show`
# ---------------------------------------------------------------------------


def test_backend_show_subcommand(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "show", "originq:wuyuan"])

    assert result.exit_code == 0, result.output
    assert "wuyuan" in result.output
    assert "Hardware" in result.output


def test_backend_show_json(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "show", "originq:wuyuan", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = result.stdout[result.stdout.index("{") : result.stdout.rindex("}") + 1]
    data = json.loads(payload)
    assert data["name"] == "wuyuan"


def test_backend_show_not_found(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "show", "originq:bogus"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_backend_show_via_option(monkeypatch, request):
    """`uniqc backend --show <id>` uses the callback path; bypass the
    conftest fixture that forces ``_subcommand_given`` to True."""
    request.getfixturevalue("_force_subcommand_detection")
    monkeypatch.setattr(backend_cli, "_subcommand_given", lambda: False)
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "--show", "originq:wuyuan"])

    assert result.exit_code == 0, result.output
    assert "wuyuan" in result.output


# ---------------------------------------------------------------------------
# `backend update`
# ---------------------------------------------------------------------------


def test_backend_update_aggregates_success_and_warnings(monkeypatch):
    backends = _fake_backends()
    calls: list[tuple[Platform, bool]] = []

    def _fetch_one(plat: Platform, force_refresh: bool = False):
        calls.append((plat, force_refresh))
        if plat == Platform.IBM:
            raise RuntimeError("IBM unreachable")
        return backends.get(plat, []), True

    monkeypatch.setattr(backend_cli, "fetch_platform_backends", _fetch_one)
    monkeypatch.setattr(backend_cli, "invalidate_all", lambda: calls.append(("invalidate", True)))

    result = runner.invoke(app, ["backend", "update", "--clear"])

    assert result.exit_code == 0, result.output
    assert ("invalidate", True) in calls
    assert "ibm" in result.output.lower()
    assert "originq" in result.output.lower()


def test_backend_update_single_platform(monkeypatch):
    _patch_registry(monkeypatch)

    result = runner.invoke(app, ["backend", "update", "--platform", "originq"])

    assert result.exit_code == 0, result.output
    assert "originq" in result.output.lower()


def test_backend_update_no_backends_returned(monkeypatch):
    def _fetch_one(plat: Platform, force_refresh: bool = False):
        return [], True

    monkeypatch.setattr(backend_cli, "fetch_platform_backends", _fetch_one)

    result = runner.invoke(app, ["backend", "update"])

    assert result.exit_code == 0
    assert "no backends" in result.output.lower() or "Skipped" in result.output


# ---------------------------------------------------------------------------
# `backend chip-display`
# ---------------------------------------------------------------------------


def _make_chip() -> ChipCharacterization:
    return ChipCharacterization(
        platform=Platform.ORIGINQ,
        chip_name="wuyuan",
        full_id="originq:wuyuan",
        available_qubits=(0, 1, 2),
        connectivity=(QubitTopology(0, 1), QubitTopology(1, 2)),
        single_qubit_data=(
            SingleQubitData(qubit_id=0, t1=42.0, t2=18.0, single_gate_fidelity=0.999),
            SingleQubitData(qubit_id=1, t1=40.0, t2=17.0, single_gate_fidelity=0.998),
        ),
        two_qubit_data=(TwoQubitData(qubit_u=0, qubit_v=1, gates=(TwoQubitGateData(gate="cz", fidelity=0.985),)),),
        global_info=ChipGlobalInfo(
            single_qubit_gates=("rx", "ry", "rz"),
            two_qubit_gates=("cz",),
            single_qubit_gate_time=30.0,
            two_qubit_gate_time=200.0,
        ),
        calibrated_at="2026-05-01T00:00:00Z",
    )


def test_backend_chip_display_success(monkeypatch):
    chip = _make_chip()
    monkeypatch.setattr(
        "uniqc.cli.chip_service.fetch_chip_characterization",
        lambda name, platform, force_refresh=False: chip,
    )

    result = runner.invoke(app, ["backend", "chip-display", "originq/wuyuan"])

    assert result.exit_code == 0, result.output
    assert "wuyuan" in result.output
    assert "42" in result.output  # T1


def test_backend_chip_display_missing(monkeypatch):
    monkeypatch.setattr(
        "uniqc.cli.chip_service.fetch_chip_characterization",
        lambda name, platform, force_refresh=False: None,
    )

    result = runner.invoke(app, ["backend", "chip-display", "originq/bogus"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_backend_chip_display_bad_identifier():
    result = runner.invoke(app, ["backend", "chip-display", "no-slash"])

    assert result.exit_code == 1
    assert "platform/chip_name" in result.output


def test_backend_chip_display_unknown_platform():
    result = runner.invoke(app, ["backend", "chip-display", "wat/foo"])

    assert result.exit_code == 1
    assert "Unknown platform" in result.output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_format_age_seconds():
    assert backend_cli._format_age(5) == "5s"
    assert backend_cli._format_age(120) == "2m"
    assert backend_cli._format_age(7200) == "2h"
    assert backend_cli._format_age(60 * 60 * 24 * 3) == "3d"


def test_fmt_fidelity_handles_none():
    assert backend_cli._fmt_fidelity(None) == "-"
    assert backend_cli._fmt_fidelity(0.987654).startswith("0.98")
