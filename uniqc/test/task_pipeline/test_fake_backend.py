"""Fake-backend tests for the full submit→query→result pipeline.

All tests run against ``dummy:local:simulator`` — no API keys or cloud
access required.
"""

from __future__ import annotations

import pytest

from uniqc import (
    Circuit,
    TaskStatus,
    get_result,
    poll_result,
    submit_batch,
    submit_task,
    wait_for_result,
)

BACKEND = "dummy:local:simulator"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _bell_pair() -> Circuit:
    c = Circuit(2)
    c.h(0)
    c.cnot(0, 1)
    c.measure(0, 1)
    return c


def _all_gates_circuit() -> Circuit:
    """Build a circuit exercising the full target gate set.

    Single-qubit: H, X, Y, Z, S, T, RX, RY, RZ, P, U1, U2, U3
    Two-qubit  : CNOT, CZ, SWAP, CRX, CRY, CRZ, CP, CU
    Multi-qubit: TOFFOLI
    """
    c = Circuit(4)

    # 1q parametric
    c.rx(0, 0.1)
    c.ry(0, 0.2)
    c.rz(0, 0.3)
    c.p(0, 0.4)
    c.u1(0, 0.5)
    c.u2(0, 0.6, 0.7)
    c.u3(0, 0.8, 0.9, 1.0)

    # 1q non-parametric
    c.h(0)
    c.x(0)
    c.y(0)
    c.z(0)
    c.s(0)
    c.t(0)

    # 2q non-parametric
    c.cnot(0, 1)
    c.cz(0, 1)
    c.swap(0, 1)

    # 2q parametric
    c.crx(0, 1, 0.5)
    c.cry(0, 1, 0.6)
    c.crz(0, 1, 0.7)
    c.cp(0, 1, 0.8)
    c.cu(0, 1, 0.9, 1.0, 1.1)

    # 3q
    c.toffoli(0, 1, 2)

    c.measure(0, 1, 2, 3)
    return c


# ---------------------------------------------------------------------------
# Tests: submit_task + get_result / wait_for_result
# ---------------------------------------------------------------------------


class TestSubmitAndGetResult:
    """End-to-end submit→get_result against dummy backend."""

    def test_bell_pair_submits_and_returns_counts(self):
        task_id = submit_task(_bell_pair(), backend=BACKEND, shots=2048)
        assert task_id.startswith("uqt_")

        result = get_result(task_id, timeout=30)
        assert result is not None
        assert isinstance(result.counts, dict)
        assert sum(result.counts.values()) == 2048

    def test_wait_for_result_alias(self):
        task_id = submit_task(_bell_pair(), backend=BACKEND, shots=512)
        result = wait_for_result(task_id, timeout=30)
        assert result is not None

    def test_all_target_gates_circuit(self):
        c = _all_gates_circuit()
        task_id = submit_task(c, backend=BACKEND, shots=100)
        result = get_result(task_id, timeout=30)
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: poll_result (non-blocking)
# ---------------------------------------------------------------------------


class TestPollResult:
    """Non-blocking poll_result tests."""

    def test_poll_returns_task_info(self):
        task_id = submit_task(_bell_pair(), backend=BACKEND, shots=256)
        info = poll_result(task_id)
        # Dummy tasks complete instantly so status should be SUCCESS.
        assert info.status == TaskStatus.SUCCESS

    def test_poll_nonexistent_raises(self):
        with pytest.raises(Exception):
            poll_result("uqt_nonexistent_12345")


# ---------------------------------------------------------------------------
# Tests: batch submission
# ---------------------------------------------------------------------------


class TestBatchSubmission:
    """Batch submit + per-circuit result ordering."""

    def test_submit_batch_returns_task_id(self):
        circuits = [_bell_pair(), _bell_pair()]
        task_id = submit_batch(circuits, backend=BACKEND, shots=500)
        assert isinstance(task_id, str)
        assert task_id.startswith("uqt_")

    def test_batch_results_ordered_by_submission(self):
        c1 = Circuit(1)
        c1.x(0)
        c1.measure(0)

        c2 = Circuit(1)
        c2.h(0)
        c2.measure(0)

        task_id = submit_batch([c1, c2], backend=BACKEND, shots=2000)
        results = get_result(task_id, timeout=30)
        assert isinstance(results, list)
        assert len(results) == 2
        # X gate → mostly |1⟩
        assert int(max(results[0].counts, key=results[0].counts.get)) == 1


# ---------------------------------------------------------------------------
# Tests: string auto-detection
# ---------------------------------------------------------------------------


class TestStringAutoDetection:
    """submit_task accepts OriginIR / QASM strings directly."""

    def test_originir_string_input(self):
        originir = "QINIT 2\nCREG 2\nH q[0]\nCNOT q[0], q[1]\nMEASURE q[0], c[0]\nMEASURE q[1], c[1]\n"
        task_id = submit_task(originir, backend=BACKEND, shots=512)
        result = get_result(task_id, timeout=30)
        assert result is not None

    def test_qasm_string_input(self):
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\ncreg c[2];\n"
            "h q[0];\ncx q[0],q[1];\n"
            "measure q[0] -> c[0];\nmeasure q[1] -> c[1];\n"
        )
        task_id = submit_task(qasm, backend=BACKEND, shots=512)
        result = get_result(task_id, timeout=30)
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: Circuit serialization roundtrip
# ---------------------------------------------------------------------------


class TestCircuitSerializationRoundtrip:
    """Circuit → to_qasm → from_qasm → submit produces equivalent results."""

    def test_qasm_roundtrip_preserves_gate_count(self):
        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        c.measure(0, 1)

        qasm_str = c.to_qasm()
        c2 = Circuit.from_qasm(qasm_str)
        assert len(c2.opcode_list) == len(c.opcode_list)

    def test_originir_roundtrip_preserves_gate_count(self):
        c = Circuit(2)
        c.h(0)
        c.cnot(0, 1)
        c.measure(0, 1)

        oir_str = c.to_originir()
        c2 = Circuit.from_originir(oir_str)
        assert len(c2.opcode_list) == len(c.opcode_list)

    def test_roundtripped_circuit_submits_successfully(self):
        c = _bell_pair()
        qasm_str = c.to_qasm()
        c2 = Circuit.from_qasm(qasm_str)

        task_id = submit_task(c2, backend=BACKEND, shots=1024)
        result = get_result(task_id, timeout=30)
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: dry_run
# ---------------------------------------------------------------------------


class TestDryRun:
    """dry_run_task against dummy backend."""

    def test_dry_run_succeeds(self):
        from uniqc import dry_run_task

        result = dry_run_task(_bell_pair(), backend=BACKEND, shots=500)
        assert result.success


# ---------------------------------------------------------------------------
# Tests: qiskit.QuantumCircuit auto-detection (requires qiskit)
# ---------------------------------------------------------------------------


@pytest.mark.requires_qiskit
class TestQiskitAutoDetection:
    """submit_task accepts qiskit.QuantumCircuit with auto-detection."""

    def test_qiskit_quantumcircuit_input(self):
        from qiskit import QuantumCircuit as QiskitQC

        qc = QiskitQC(2, 2)
        qc.h(0)
        qc.cx(0, 1)
        qc.measure([0, 1], [0, 1])

        task_id = submit_task(qc, backend=BACKEND, shots=1024)
        result = get_result(task_id, timeout=30)
        assert result is not None
