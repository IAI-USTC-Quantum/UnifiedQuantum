"""End-to-end integration tests for Quafu and IBM adapters.

These tests require real API credentials and network access.
They are skipped unless the corresponding environment variables are set.

Run locally:
    QUAFU_API_TOKEN=xxx pytest uniqc/test/cloud/test_adapter_integration.py -v -m cloud
    IBM_TOKEN=xxx pytest uniqc/test/cloud/test_adapter_integration.py -v -m cloud
"""

from __future__ import annotations

import os

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
# Quafu Integration Tests
# =============================================================================

@pytest.mark.cloud
@pytest.mark.skipif(not os.environ.get("QUAFU_API_TOKEN"), reason="QUAFU_API_TOKEN not set")
class RunTestQuafuAdapterReal:
    """End-to-end tests for QuafuAdapter with real credentials."""

    def run_test_translate_bell_pair(self):
        """Translate Bell pair circuit and verify Quafu circuit is valid."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        assert qc is not None
        assert hasattr(qc, "h")
        assert hasattr(qc, "cnot")

    def run_test_translate_with_all_gates(self):
        """Test translation of circuit using Y, Z, S, SX, T, SWAP, ISWAP gates.

        This validates that QuafuAdapter._reconstruct_qasm supports the
        full gate set (Y, Z, S, SX, T, SWAP, ISWAP, BARRIER).
        """
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        # Should not raise RuntimeError
        qc = adapter.translate_circuit(ORIGINIR_GATES)
        assert qc is not None
        assert hasattr(qc, "y")
        assert hasattr(qc, "z")
        assert hasattr(qc, "s")
        assert hasattr(qc, "sx")
        assert hasattr(qc, "t")
        assert hasattr(qc, "swap")
        assert hasattr(qc, "iswap")
        assert hasattr(qc, "cz")
        assert hasattr(qc, "cnot")

    def run_test_submit_sync(self):
        """Submit with wait=True and verify immediate completion."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        # Use a simulator chip if available, otherwise any valid chip
        task_id = adapter.submit(qc, shots=100, chip_id="ScQ-Sim10", wait=True)
        assert isinstance(task_id, str) and len(task_id) > 0

        result = adapter.query(task_id)
        assert "status" in result
        assert result["status"] in ("success", "failed", "running")

    def run_test_submit_async_then_query_sync(self):
        """Submit async, poll with query_sync, verify result shape."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        task_id = adapter.submit(qc, shots=100, chip_id="ScQ-Sim10", wait=False)
        assert isinstance(task_id, str)

        # Poll until done (or timeout after 60s)
        results = adapter.query_sync(task_id, interval=5.0, timeout=60.0)
        assert isinstance(results, list)
        assert len(results) == 1
        # query_sync returns inner result dicts from query_batch — for Quafu
        # these are {"counts": {...}, "probabilities": {...}}, no "status" key
        assert "counts" in results[0]
        assert "probabilities" in results[0]

    def run_test_submit_batch_sync(self):
        """Batch submit 3 circuits with wait=True."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        task_ids = adapter.submit_batch(
            [qc, qc, qc], shots=100, chip_id="ScQ-Sim10", wait=True
        )
        assert isinstance(task_ids, list)
        assert len(task_ids) == 3
        assert all(isinstance(tid, str) for tid in task_ids)

    def run_test_result_shape(self):
        """Verify result has {"status": "success", "result": {"counts": ..., "probabilities": ...}}."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        task_id = adapter.submit(qc, shots=100, chip_id="ScQ-Sim10", wait=True)
        result = adapter.query(task_id)

        assert result["status"] == "success", f"Expected success, got {result}"
        assert "result" in result
        inner = result["result"]
        assert "counts" in inner, f"Result must have 'counts', got {inner.keys()}"
        assert "probabilities" in inner, f"Result must have 'probabilities', got {inner.keys()}"

        # Verify counts are non-negative integers
        for key, val in inner["counts"].items():
            assert isinstance(key, str), f"Count key must be str, got {type(key)}"
            assert isinstance(val, int) and val >= 0, f"Count value must be non-neg int, got {val}"

    def run_test_list_backends(self):
        """Call list_backends and verify expected chip names appear."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        backends = adapter.list_backends()
        assert isinstance(backends, list)
        assert len(backends) > 0
        names = [b["name"] for b in backends]
        # At least one of the known chips should appear
        known_chips = {"ScQ-Sim10", "ScQ-P18", "ScQ-P136", "ScQ-Sim10C", "Dongling"}
        assert any(c in names for c in known_chips), f"Expected known chips in {names}"


# =============================================================================
# Qiskit/IBM Integration Tests
# =============================================================================

@pytest.mark.cloud
@pytest.mark.skipif(not os.environ.get("IBM_TOKEN"), reason="IBM_TOKEN not set")
class RunTestQiskitAdapterReal:
    """End-to-end tests for QiskitAdapter with real credentials."""

    def run_test_translate_circuit(self):
        """Translate Bell pair to Qiskit QuantumCircuit."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        assert qc is not None
        assert hasattr(qc, "num_qubits")
        assert qc.num_qubits >= 2

    def run_test_submit_single(self):
        """Submit single circuit to a real IBM chip (ibm_fez)."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        job_id = adapter.submit(qc, shots=100, chip_id="ibm_fez")
        assert isinstance(job_id, str)

        result = adapter.query(job_id)
        assert "status" in result

    def run_test_submit_batch_returns_list(self):
        """Submit 3 circuits; verify submit_batch returns list[str] (not str).

        This validates the fix for the B3 bug: submit_batch previously returned
        str, causing isinstance(result, list) checks in task_manager to fail.
        """
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        result = adapter.submit_batch(
            [qc, qc, qc], shots=100, chip_id="ibm_fez"
        )
        # Must be a list, not a string
        assert isinstance(result, list), f"submit_batch must return list, got {type(result)}"
        assert len(result) >= 1, f"Expected at least 1 job ID, got {result}"
        assert all(isinstance(tid, str) for tid in result), f"All IDs must be str, got {result}"

    def run_test_query_sync(self):
        """Use query_sync to poll until result available."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        job_ids = adapter.submit_batch(
            [qc, qc], shots=100, chip_id="ibm_fez"
        )
        assert isinstance(job_ids, list)

        results = adapter.query_sync(job_ids, interval=5.0, timeout=180.0)
        assert isinstance(results, list)
        assert len(results) == 2

    def run_test_result_shape_batch(self):
        """Verify batch result: {"status": "success", "result": [counts_dict, ...], ...}."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        job_ids = adapter.submit_batch(
            [qc, qc], shots=100, chip_id="ibm_fez"
        )
        results = adapter.query_sync(job_ids, interval=5.0, timeout=180.0)

        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, dict)
            # Each result is a counts dict: {"00": N, "11": M}
            for key, val in r.items():
                assert isinstance(key, str)
                assert isinstance(val, int) and val >= 0

    def run_test_list_backends(self):
        """List IBM backends; verify real chips appear."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        backends = adapter._service.backends()
        names = [b.name for b in backends]
        # At least one known chip should appear (the open instance has real hardware)
        known_chips = {"ibm_fez", "ibm_marrakesh", "ibm_kingston"}
        assert any(c in names for c in known_chips), f"Expected known chips in {names}"
