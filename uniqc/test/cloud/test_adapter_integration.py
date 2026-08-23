"""End-to-end integration tests for the IBM adapter.

These tests require real API credentials and network access.
They are skipped unless the active ``~/.uniqc/config.yaml`` profile has tokens.

Run locally:
    uniqc config set ibm.token xxx
    pytest uniqc/test/cloud/test_adapter_integration.py -v -m cloud
    pytest uniqc/test/cloud/test_adapter_integration.py -v --real-cloud-test
"""

from __future__ import annotations

import pytest

ORIGINIR_BELL = """
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""".strip()

ORIGINIR_GATES = """
QINIT 3
CREG 3
X q[0]
Y q[1]
Z q[2]
S q[0]
T q[1]
SX q[2]
CNOT q[0], q[1]
CZ q[1], q[2]
SWAP q[0], q[2]
ISWAP q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
""".strip()


# =============================================================================
# Qiskit/IBM Integration Tests
# =============================================================================


@pytest.mark.cloud
class RunTestQiskitAdapterReal:
    """End-to-end tests for QiskitAdapter with real credentials."""

    def run_test_translate_circuit(self):
        """Translate Bell pair to Qiskit QuantumCircuit."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        assert qc is not None
        assert hasattr(qc, "num_qubits")
        assert qc.num_qubits >= 2

    @pytest.mark.real_cloud_execution
    def run_test_submit_single(self):
        """Submit single circuit to a real IBM chip (ibm_fez)."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        job_id = adapter.submit(qc, shots=100, chip_id="ibm_fez")
        assert isinstance(job_id, str)

        result = adapter.query(job_id)
        assert "status" in result

    @pytest.mark.real_cloud_execution
    def run_test_submit_batch_returns_list(self):
        """Submit 3 circuits; verify submit_batch returns list[str] (not str).

        This validates the fix for the B3 bug: submit_batch previously returned
        str, causing isinstance(result, list) checks in task_manager to fail.
        """
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        result = adapter.submit_batch([qc, qc, qc], shots=100, chip_id="ibm_fez")
        # Must be a list, not a string
        assert isinstance(result, list), f"submit_batch must return list, got {type(result)}"
        assert len(result) >= 1, f"Expected at least 1 job ID, got {result}"
        assert all(isinstance(tid, str) for tid in result), f"All IDs must be str, got {result}"

    @pytest.mark.real_cloud_execution
    def run_test_query_sync(self):
        """Use query_sync to poll until result available."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        job_ids = adapter.submit_batch([qc, qc], shots=100, chip_id="ibm_fez")
        assert isinstance(job_ids, list)

        results = adapter.query_sync(job_ids, interval=5.0, timeout=180.0)
        assert isinstance(results, list)
        assert len(results) >= 1

    @pytest.mark.real_cloud_execution
    def run_test_result_shape_batch(self):
        """Verify batch result: {"status": "success", "result": [counts_dict, ...], ...}."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        job_ids = adapter.submit_batch([qc, qc], shots=100, chip_id="ibm_fez")
        results = adapter.query_sync(job_ids, interval=5.0, timeout=180.0)

        assert isinstance(results, list)
        assert len(results) >= 1
        for r in results:
            assert isinstance(r, dict)
            # Each result is a counts dict: {"00": N, "11": M}
            for key, val in r.items():
                assert isinstance(key, str)
                assert isinstance(val, int) and val >= 0

    def run_test_list_backends(self):
        """List IBM backends; verify real chips appear."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        backends = adapter._service.backends()
        names = [b.name for b in backends]
        # At least one known chip should appear (the open instance has real hardware)
        known_chips = {"ibm_fez", "ibm_marrakesh", "ibm_kingston"}
        assert any(c in names for c in known_chips), f"Expected known chips in {names}"
