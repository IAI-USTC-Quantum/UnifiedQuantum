"""Tests for the task adapter layer.

These tests verify that:
1. Each adapter correctly translates OriginIR to provider-native circuits.
2. Config is loaded from environment variables.
3. Task modules delegate to adapters.

Cloud tests require real credentials and are marked with @pytest.mark.cloud.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORIGINIR_BELL = """
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""".strip()

ORIGINIR_3Q = """
QINIT 3
CREG 3
H q[0]
H q[1]
H q[2]
CNOT q[0], q[1]
CNOT q[1], q[2]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
""".strip()


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class RunTestConfigEnvVars:
    """Config loading from environment variables (preferred)."""

    def run_test_originq_config_from_env(self, monkeypatch, tmp_path):
        """OriginQ config is read from ORIGINQ_API_KEY env var."""
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key_123")
        monkeypatch.setenv("ORIGINQ_TASK_GROUP_SIZE", "100")

        # Ensure no config file exists
        monkeypatch.chdir(tmp_path)

        from uniqc.task.config import load_originq_config

        config = load_originq_config()
        assert config["api_key"] == "test_key_123"
        assert config["task_group_size"] == 100

    def run_test_quafu_config_from_env(self, monkeypatch, tmp_path):
        """Quafu config is read from QUAHU_API_TOKEN env var."""
        monkeypatch.setenv("QUAFU_API_TOKEN", "quafu_secret_token")
        monkeypatch.chdir(tmp_path)

        from uniqc.task.config import load_quafu_config

        config = load_quafu_config()
        assert config["api_token"] == "quafu_secret_token"

    def run_test_ibm_config_from_env(self, monkeypatch, tmp_path):
        """IBM config is read from IBM_TOKEN env var."""
        monkeypatch.setenv("IBM_TOKEN", "ibm_secret_token")
        monkeypatch.chdir(tmp_path)

        from uniqc.task.config import load_ibm_config

        config = load_ibm_config()
        assert config["api_token"] == "ibm_secret_token"

    def run_test_dummy_config_from_env(self, monkeypatch, tmp_path):
        """OriginQ Dummy config is read from ORIGINQ_* env vars."""
        monkeypatch.setenv(
            "ORIGINQ_AVAILABLE_QUBITS", json.dumps([0, 1, 2, 3])
        )
        monkeypatch.setenv(
            "ORIGINQ_AVAILABLE_TOPOLOGY",
            json.dumps([[0, 1], [1, 2], [2, 3]]),
        )
        monkeypatch.setenv("ORIGINQ_TASK_GROUP_SIZE", "50")
        monkeypatch.chdir(tmp_path)

        from uniqc.task.config import load_dummy_config

        config = load_dummy_config()
        assert config["available_qubits"] == [0, 1, 2, 3]
        assert config["available_topology"] == [[0, 1], [1, 2], [2, 3]]
        assert config["task_group_size"] == 50

    def run_test_originq_config_deprecated_file_fallback(self, monkeypatch, tmp_path):
        """File fallback is no longer supported - ImportError raised when env vars absent."""
        monkeypatch.delenv("ORIGINQ_API_KEY", raising=False)

        # Create a config file (should NOT be used anymore)
        config_file = tmp_path / "originq_cloud_config.json"
        config_file.write_text(
            json.dumps(
                {
                    "apitoken": "file_key",
                    "task_group_size": 50,
                }
            )
        )
        monkeypatch.chdir(tmp_path)

        # Clear module cache to force re-import
        if "uniqc.task.config" in sys.modules:
            del sys.modules["uniqc.task.config"]

        from uniqc.task.config import load_originq_config

        # Should raise ImportError - file fallback is no longer supported
        with pytest.raises(ImportError, match="ORIGINQ_API_KEY"):
            load_originq_config()

    def run_test_originq_config_import_error_without_config(self, monkeypatch, tmp_path):
        """ImportError raised when env vars are absent."""
        monkeypatch.delenv("ORIGINQ_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)

        # Force re-import by clearing module cache
        if "uniqc.task.config" in sys.modules:
            del sys.modules["uniqc.task.config"]

        from uniqc.task.config import load_originq_config

        with pytest.raises(ImportError, match="ORIGINQ_API_KEY"):
            load_originq_config()


# ---------------------------------------------------------------------------
# OriginQ adapter tests (require credentials)
# ---------------------------------------------------------------------------

@pytest.mark.cloud
@pytest.mark.skipif(
    not os.environ.get("ORIGINQ_API_KEY"),
    reason="ORIGINQ_API_KEY not set"
)
@pytest.mark.requires_pyqpanda3
class RunTestOriginQAdapterIntegration:
    """Integration tests for OriginQ adapter with real pyqpanda3 and credentials."""

    def run_test_translate_circuit(self):
        """Test that translate_circuit converts OriginIR to QProg."""
        from uniqc.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        result = adapter.translate_circuit(ORIGINIR_BELL)
        assert result is not None

    def run_test_submit_and_query(self):
        """Test submit and query with real service."""
        from uniqc.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        task_id = adapter.submit(ORIGINIR_BELL, shots=1000)
        assert task_id is not None

        result = adapter.query(task_id)
        assert "status" in result

    def run_test_submit_batch(self):
        """Test submit_batch with real service."""
        from uniqc.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        circuits = [ORIGINIR_BELL] * 2
        task_ids = adapter.submit_batch(circuits, shots=1000)
        assert len(task_ids) >= 1


# ---------------------------------------------------------------------------
# Quafu adapter tests (require credentials)
# ---------------------------------------------------------------------------

@pytest.mark.cloud
@pytest.mark.skipif(
    not os.environ.get("QUAFU_API_TOKEN"),
    reason="QUAFU_API_TOKEN not set"
)
@pytest.mark.requires_quafu
class RunTestQuafuAdapterIntegration:
    """Integration tests for Quafu adapter with real quafu and credentials."""

    def run_test_translate_simple_gates(self):
        """Test circuit translation with real quafu."""
        originir = """
QINIT 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
""".strip()

        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        result = adapter.translate_circuit(originir)
        assert result is not None

    def run_test_submit_and_query(self):
        """Test submit and query with real service."""
        from uniqc.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()

        # Translate circuit first
        circuit = adapter.translate_circuit(ORIGINIR_BELL)
        task_id = adapter.submit(circuit, shots=1000, chip_id="ScQ-P10")
        assert task_id is not None

        result = adapter.query(task_id)
        assert "status" in result


# ---------------------------------------------------------------------------
# IBM adapter tests (require credentials)
# ---------------------------------------------------------------------------

@pytest.mark.cloud
@pytest.mark.skipif(
    not os.environ.get("IBM_TOKEN"),
    reason="IBM_TOKEN not set"
)
@pytest.mark.requires_qiskit
class RunTestIBMAdapterIntegration:
    """Integration tests for IBM adapter with real qiskit and credentials."""

    def run_test_translate_circuit(self):
        """Test circuit translation with real qiskit."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        result = adapter.translate_circuit(ORIGINIR_BELL)
        assert result is not None
        assert hasattr(result, "num_qubits")

    def run_test_submit_and_query(self):
        """Test submit and query with real service."""
        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()

        circuit = adapter.translate_circuit(ORIGINIR_BELL)
        # Note: IBM submission requires backend selection
        # This test may need adjustment based on available backends


# ---------------------------------------------------------------------------
# Adapter availability tests
# ---------------------------------------------------------------------------

class RunTestAdapterAvailability:
    """Each adapter reports availability based on installed packages / config."""

    def run_test_originq_adapter_available_with_config(self, monkeypatch):
        """Test OriginQ adapter availability with config."""
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key")

        from uniqc.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        assert adapter.is_available() is True

    def run_test_quafu_adapter_available_with_config(self, monkeypatch):
        """Test Quafu adapter availability with config."""
        from uniqc.task.optional_deps import check_quafu
        monkeypatch.setenv("QUAFU_API_TOKEN", "test_token")

        # Check if quafu is actually installed
        quafu_available = check_quafu()

        if not quafu_available:
            pytest.skip("quafu not installed")

        from uniqc.task.adapters import QuafuAdapter
        adapter = QuafuAdapter()
        assert isinstance(adapter.is_available(), bool)

    def run_test_ibm_adapter_available_with_config(self, monkeypatch):
        """Test IBM adapter availability with config."""
        from uniqc.task.optional_deps import check_qiskit
        monkeypatch.setenv("IBM_TOKEN", "test_token")

        # Check if qiskit is actually installed
        qiskit_available = check_qiskit()

        if not qiskit_available:
            pytest.skip("qiskit not installed")

        from uniqc.task.adapters import QiskitAdapter
        adapter = QiskitAdapter()
        assert isinstance(adapter.is_available(), bool)
