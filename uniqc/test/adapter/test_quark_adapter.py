"""Tests for the QuarkStudio backend adapter."""

from __future__ import annotations

import pytest

from uniqc.backend_adapter.backend_info import Platform
from uniqc.backend_adapter.task.adapters.base import TASK_STATUS_RUNNING, TASK_STATUS_SUCCESS
from uniqc.backend_adapter.task.adapters.quark_adapter import QuarkAdapter

ORIGINIR_BELL = """
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""".strip()


class FakeTask:
    def __init__(self):
        self.submitted = []
        self.status_payload = {"Baihua": 0, "Miaofeng": "Offline", "Haituo": "Calibrating"}
        self.result_payload = {}

    def run(self, task, repeat=1):
        self.submitted.append((task, repeat))
        return 123456

    def result(self, tid):
        return self.result_payload.get(tid, {})

    def status(self, tid=0):
        if tid:
            return {"status": "Running"}
        return self.status_payload


def test_translate_originir_to_qasm2():
    adapter = QuarkAdapter(token="token", task_client=FakeTask())

    qasm = adapter.translate_circuit(ORIGINIR_BELL)

    assert "OPENQASM 2.0" in qasm
    assert "cxq[0],q[1]" in qasm.replace(" ", "")


def test_submit_builds_quark_task_dict():
    fake = FakeTask()
    adapter = QuarkAdapter(token="token", task_client=fake)
    qasm = adapter.translate_circuit(ORIGINIR_BELL)

    task_id = adapter.submit(
        qasm,
        shots=2048,
        chip_id="Baihua",
        task_name="bell",
        compiler="qiskit",
        correct=True,
        target_qubits=[0, 1],
    )

    assert task_id == "123456"
    task, repeat = fake.submitted[0]
    assert repeat == 2
    assert task["chip"] == "Baihua"
    assert task["name"] == "bell"
    assert task["shots"] == 2048
    assert task["compile"] is True
    assert task["circuit"] == qasm
    assert task["options"]["compiler"] == "qiskit"
    assert task["options"]["correct"] is True
    assert task["options"]["target_qubits"] == [0, 1]


def test_query_normalises_counts_result():
    fake = FakeTask()
    fake.result_payload[123456] = {"status": "Finished", "count": {"00": 10, "11": 14}}
    adapter = QuarkAdapter(token="token", task_client=fake)

    result = adapter.query("123456")

    assert result["status"] == TASK_STATUS_SUCCESS
    assert result["result"]["counts"] == {"00": 10, "11": 14}


def test_query_running_when_no_result_yet():
    adapter = QuarkAdapter(token="token", task_client=FakeTask())

    result = adapter.query("123456")

    assert result["status"] == TASK_STATUS_RUNNING


def test_list_backends_from_status_payload():
    adapter = QuarkAdapter(token="token", task_client=FakeTask())

    backends = adapter.list_backends()

    # list_backends() may enrich entries with optional chip-info fields
    # (num_qubits / topology / valid_gates / backend_info_available) when
    # quarkcircuit is installed. Check the core fields explicitly.
    assert len(backends) == 3
    core = [{k: b[k] for k in ("name", "status", "task_in_queue")} for b in backends]
    assert core == [
        {"name": "Baihua", "status": "available", "task_in_queue": 0},
        {"name": "Miaofeng", "status": "unavailable", "task_in_queue": "Offline"},
        {"name": "Haituo", "status": "maintenance", "task_in_queue": "Calibrating"},
    ]


def test_normalise_quark_backend_status_payload():
    from uniqc.backend_adapter.backend_info import Platform
    from uniqc.backend_adapter.backend_registry import _normalise_quark

    backends = _normalise_quark(
        [
            {"name": "Baihua", "status": "available", "task_in_queue": 0},
            {"name": "Miaofeng", "status": "unavailable", "task_in_queue": "Offline"},
            {"name": "Haituo", "status": "Calibrating", "task_in_queue": "Calibrating"},
            {"name": "Jiu", "task_in_queue": "Maintenance"},
        ]
    )

    assert backends[0].platform == Platform.QUARK
    assert backends[0].name == "Baihua"
    assert backends[0].status == "available"
    assert backends[0].is_hardware is True
    assert backends[1].status == "unavailable"
    assert backends[2].status == "maintenance"
    assert backends[3].status == "maintenance"


def test_dry_run_accepts_qasm2_translation_and_warns_on_non_1024_shots():
    adapter = QuarkAdapter(token="token", task_client=FakeTask())

    result = adapter.dry_run(ORIGINIR_BELL, shots=1000, chip_id="Baihua")

    assert result.success
    assert result.backend_name == "Baihua"
    assert result.circuit_qubits == 2
    assert result.warnings


ORIGINIR_3Q = """
QINIT 3
CREG 3
H q[0]
CNOT q[0], q[1]
CNOT q[1], q[2]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
""".strip()


def test_dry_run_fails_when_circuit_exceeds_chip_qubits(monkeypatch):
    """A circuit touching qubits outside the chip's available set must fail."""
    adapter = QuarkAdapter(token="token", task_client=FakeTask())
    # FAKE_CHIP_INFO (defined below) exposes exactly qubits {0, 1}.
    monkeypatch.setattr(adapter, "_load_chip_basic_info", lambda chip: FAKE_CHIP_INFO)

    result = adapter.dry_run(ORIGINIR_3Q, shots=1024, chip_id="Baihua")

    assert not result.success
    assert "[2]" in result.error
    assert "Baihua" in result.details


def test_dry_run_passes_when_circuit_fits_chip(monkeypatch):
    adapter = QuarkAdapter(token="token", task_client=FakeTask())
    monkeypatch.setattr(adapter, "_load_chip_basic_info", lambda chip: FAKE_CHIP_INFO)

    result = adapter.dry_run(ORIGINIR_BELL, shots=1024, chip_id="Baihua")

    assert result.success
    assert not any("skipped qubit-availability" in w for w in result.warnings)


def test_dry_run_skips_qubit_validation_when_chip_metadata_unavailable(monkeypatch):
    adapter = QuarkAdapter(token="token", task_client=FakeTask())
    monkeypatch.setattr(adapter, "_load_chip_basic_info", lambda chip: None)

    result = adapter.dry_run(ORIGINIR_3Q, shots=1024, chip_id="Baihua")

    assert result.success
    assert any("skipped qubit-availability validation" in w for w in result.warnings)


FAKE_CHIP_INFO = {
    "global_info": {
        "nqubits_available": 2,
        "two_qubit_gate_basis": "cz",
        "one_qubit_gate_length": 3e-8,
        "two_qubit_gate_length": 6e-8,
    },
    "basis_gates": ["sx", "rz"],
    "qubits_info": {
        "q0": {
            "index": 0,
            "T1": 30.0,
            "T2": 20.0,
            "fidelity": 0.999,
            "readout g_fidelity": 0.98,
            "readout e_fidelity": 0.97,
        },
        "q1": {
            "index": 1,
            "T1": 28.0,
            "T2": 18.0,
            "fidelity": 0.998,
            "readout g_fidelity": 0.97,
            "readout e_fidelity": 0.96,
        },
    },
    "couplers_info": {"c01": {"qubits_index": [0, 1], "fidelity": 0.99}},
    "calibration_time": "2026-08-20T00:00:00+08:00",
}


def test_get_chip_characterization_builds_unified_model(monkeypatch):
    adapter = QuarkAdapter(token="token", task_client=FakeTask())
    monkeypatch.setattr(adapter, "_load_chip_basic_info", lambda chip: FAKE_CHIP_INFO)

    chip = adapter.get_chip_characterization("Baihua")

    assert chip is not None
    assert chip.full_id == "quark:Baihua"
    assert chip.platform is Platform.QUARK
    assert chip.available_qubits == (0, 1)
    assert [(e.u, e.v) for e in chip.connectivity] == [(0, 1)]
    assert [s.t1 for s in chip.single_qubit_data] == [30.0, 28.0]
    assert chip.single_qubit_data[0].avg_readout_fidelity == pytest.approx(0.975)
    assert chip.two_qubit_data[0].gates[0].gate == "cz"
    assert chip.two_qubit_data[0].gates[0].fidelity == pytest.approx(0.99)
    assert chip.global_info.single_qubit_gates == ("sx", "rz")
    assert chip.global_info.two_qubit_gates == ("cz",)
    assert chip.global_info.single_qubit_gate_time == pytest.approx(30.0)
    assert chip.calibrated_at == "2026-08-20T00:00:00+08:00"


def test_get_chip_characterization_returns_none_without_chip_info(monkeypatch):
    adapter = QuarkAdapter(token="token", task_client=FakeTask())
    monkeypatch.setattr(adapter, "_load_chip_basic_info", lambda chip: None)

    assert adapter.get_chip_characterization("Baihua") is None


def test_wrap_as_unified_result_accepts_quark_nested_counts_payload():
    """Regression: quark's ``{"counts": ..., "raw_result": ...}`` payload used
    to crash ``wait_for_result`` with ``int() ... not 'dict'``."""
    from uniqc.backend_adapter.task_manager import _wrap_as_unified_result

    adapter = QuarkAdapter(token="token", task_client=FakeTask())
    adapter._task_client.result_payload[123456] = {"status": "Finished", "count": {"00": 10, "11": 14}}
    payload = adapter.query("123456")["result"]

    result = _wrap_as_unified_result(payload, task_id="123456", backend="quark:Baihua", shots=24)

    assert result.counts == {"00": 10, "11": 14}
    assert result.platform == "quark"
    assert result.backend_name == "quark:Baihua"
