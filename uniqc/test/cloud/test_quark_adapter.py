"""Tests for the QuarkStudio backend adapter."""

from __future__ import annotations

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
    core = [
        {k: b[k] for k in ("name", "status", "task_in_queue")} for b in backends
    ]
    assert core == [
        {"name": "Baihua", "status": "available", "task_in_queue": 0},
        {"name": "Miaofeng", "status": "unavailable", "task_in_queue": "Offline"},
        {"name": "Haituo", "status": "maintenance", "task_in_queue": "Calibrating"},
    ]


def test_normalise_quark_backend_status_payload():
    from uniqc.backend_adapter.backend_info import Platform
    from uniqc.backend_adapter.backend_registry import _normalise_quark

    backends = _normalise_quark([
        {"name": "Baihua", "status": "available", "task_in_queue": 0},
        {"name": "Miaofeng", "status": "unavailable", "task_in_queue": "Offline"},
        {"name": "Haituo", "status": "Calibrating", "task_in_queue": "Calibrating"},
        {"name": "Jiu", "task_in_queue": "Maintenance"},
    ])

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
