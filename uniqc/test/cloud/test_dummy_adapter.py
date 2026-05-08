"""Tests for the dummy_adapter module."""

from __future__ import annotations

import pytest


@pytest.mark.requires_cpp
class TestDummyAdapter:
    """Tests for DummyAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create a DummyAdapter instance."""
        from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter
        return DummyAdapter()

    def test_name(self, adapter):
        """Test adapter name."""
        assert adapter.name == "dummy"

    def test_is_available(self, adapter):
        """Test is_available returns True."""
        assert adapter.is_available()

    def test_translate_circuit(self, adapter):
        """Test translate_circuit returns circuit unchanged."""
        circuit = "QINIT 2\nH q[0]"
        result = adapter.translate_circuit(circuit)
        assert result == circuit

    def test_query_returns_result(self, adapter):
        """Test query returns a result dict."""
        circuit = "QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]"
        task_id = adapter.submit(circuit, shots=1000)

        result = adapter.query(task_id)

        assert "status" in result
        assert result["status"] == "success"
        assert "result" in result

    def test_query_nonexistent_task(self, adapter):
        """Test query for nonexistent task returns failed."""
        result = adapter.query("nonexistent-task-id")

        assert result["status"] == "failed"
        assert "error" in result

    def test_deterministic_task_id(self, adapter):
        """Test that same circuit produces same task ID."""
        circuit = "QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]"

        task_id1 = adapter.submit(circuit)
        task_id2 = adapter.submit(circuit)

        assert task_id1 == task_id2

    def test_different_circuits_different_ids(self, adapter):
        """Test that different circuits produce different task IDs."""
        circuit1 = "QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]"
        circuit2 = "QINIT 2\nCREG 2\nX q[0]\nMEASURE q[0], c[0]"

        task_id1 = adapter.submit(circuit1)
        task_id2 = adapter.submit(circuit2)

        assert task_id1 != task_id2

    def test_submit_batch(self, adapter):
        """Test submitting multiple circuits."""
        circuits = [
            "QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]",
            "QINIT 2\nCREG 2\nX q[0]\nMEASURE q[0], c[0]",
        ]

        task_ids = adapter.submit_batch(circuits, shots=1000)

        assert len(task_ids) == 2
        assert all(isinstance(tid, str) for tid in task_ids)

    def test_query_batch(self, adapter):
        """Test querying multiple tasks."""
        circuits = [
            "QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]",
            "QINIT 2\nCREG 2\nX q[0]\nMEASURE q[0], c[0]",
        ]
        task_ids = adapter.submit_batch(circuits, shots=1000)

        result = adapter.query_batch(task_ids)

        assert result["status"] == "success"
        assert len(result["result"]) == 2

    def test_explicit_readout_noise_affects_submission(self):
        """Readout-only noise should affect submitted dummy counts."""
        from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

        adapter = DummyAdapter(noise_model={"readout": [0.08, 0.12]})
        circuit = "QINIT 1\nCREG 1\nX q[0]\nMEASURE q[0], c[0]\n"

        task_id = adapter.submit(circuit, shots=1000)
        result = adapter.query(task_id)

        assert result["status"] == "success"
        assert result["result"]["0"] == pytest.approx(120, abs=1)
        assert result["result"]["1"] == pytest.approx(880, abs=1)

    def test_explicit_readout_noise_is_stable_after_exact_query(self):
        """Exact probability queries must not pollute later submissions."""
        from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

        adapter = DummyAdapter(noise_model={"readout": [0.08, 0.12]})
        circuit = "QINIT 1\nCREG 1\nX q[0]\nMEASURE q[0], c[0]\n"

        assert adapter.simulate_pmeasure(circuit) == pytest.approx([0.12, 0.88])
        task_id = adapter.submit(circuit, shots=1000)
        result = adapter.query(task_id)

        assert result["result"]["0"] == pytest.approx(120, abs=1)
        assert result["result"]["1"] == pytest.approx(880, abs=1)

    def test_clear_cache(self, adapter):
        """Test clearing the cache."""
        circuit = "QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]"
        task_id = adapter.submit(circuit)

        adapter.clear_cache()

        result = adapter.query(task_id)
        assert result["status"] == "failed"
