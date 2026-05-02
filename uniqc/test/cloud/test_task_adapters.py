"""Tests for the task adapter layer.

These tests verify that:
1. Each adapter correctly translates OriginIR to provider-native circuits.
2. Config is loaded from environment variables, with YAML config fallback (issue #45).
3. Task modules delegate to adapters.

Cloud tests require real credentials and are marked with @pytest.mark.cloud.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

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
        monkeypatch.setenv("ORIGINQ_AVAILABLE_QUBITS", json.dumps([0, 1, 2, 3]))
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
        """Deprecated JSON file format is not used; empty-token YAML raises ImportError.

        The old ``originq_cloud_config.json`` format is not read.
        Instead, ``~/.uniqc/uniqc.yml`` YAML config is checked as fallback (issue #45 fix).
        With an empty-token YAML config, ImportError is correctly raised.
        """
        monkeypatch.delenv("ORIGINQ_API_KEY", raising=False)
        # Create a YAML config with empty token at the real config location
        config_dir = tmp_path / ".uniqc"
        config_dir.mkdir()
        yaml_config = config_dir / "uniqc.yml"
        yaml_config.write_text(
            "active_profile: default\n"
            "default:\n"
            "  originq:\n"
            "    token: \"\"\n"
        )
        # Patch Path.home() so ~/.uniqc/uniqc.yml points to our temp dir
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Clear module cache
        for mod in list(sys.modules):
            if mod.startswith("uniqc.task.config") or mod.startswith("uniqc.config"):
                del sys.modules[mod]

        from uniqc.task.config import load_originq_config

        # Should raise ImportError since YAML token is empty
        with pytest.raises(ImportError, match="ORIGINQ_API_KEY"):
            load_originq_config()

    def run_test_originq_config_import_error_without_config(self, monkeypatch, tmp_path):
        """ImportError raised when env vars are absent and YAML config has no token.

        After the #45 fix, the YAML config file is checked as fallback.
        With an empty-token YAML, ImportError is correctly raised.
        """
        monkeypatch.delenv("ORIGINQ_API_KEY", raising=False)
        config_dir = tmp_path / ".uniqc"
        config_dir.mkdir()
        yaml_config = config_dir / "uniqc.yml"
        yaml_config.write_text(
            "active_profile: default\n"
            "default:\n"
            "  originq:\n"
            "    token: \"\"\n"
        )
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        for mod in list(sys.modules):
            if mod.startswith("uniqc.task.config") or mod.startswith("uniqc.config"):
                del sys.modules[mod]

        from uniqc.task.config import load_originq_config

        with pytest.raises(ImportError, match="ORIGINQ_API_KEY"):
            load_originq_config()

    def run_test_originq_config_yaml_fallback(self, monkeypatch, tmp_path):
        """After #45, tokens are read from YAML config when env var is absent.

        This test verifies the YAML fallback works correctly.
        """
        monkeypatch.delenv("ORIGINQ_API_KEY", raising=False)
        config_dir = tmp_path / ".uniqc"
        config_dir.mkdir()
        yaml_config = config_dir / "uniqc.yml"
        yaml_config.write_text(
            "active_profile: default\n"
            "default:\n"
            "  originq:\n"
            '    token: "yaml-test-token"\n'
        )
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        for mod in list(sys.modules):
            if mod.startswith("uniqc.task.config") or mod.startswith("uniqc.config"):
                del sys.modules[mod]

        from uniqc.task.config import load_originq_config

        cfg = load_originq_config()
        assert cfg["api_key"] == "yaml-test-token"


# ---------------------------------------------------------------------------
# OriginQ adapter tests (require credentials)
# ---------------------------------------------------------------------------


@pytest.mark.cloud
@pytest.mark.skipif(not os.environ.get("ORIGINQ_API_KEY"), reason="ORIGINQ_API_KEY not set")
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
@pytest.mark.skipif(not os.environ.get("QUAFU_API_TOKEN"), reason="QUAFU_API_TOKEN not set")
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
@pytest.mark.skipif(not os.environ.get("IBM_TOKEN"), reason="IBM_TOKEN not set")
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

        adapter.translate_circuit(ORIGINIR_BELL)
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
        import os

        from uniqc.task.optional_deps import check_qiskit

        if not check_qiskit():
            pytest.skip("qiskit not installed")

        # QiskitRuntimeService validates tokens against IBM servers, so we need
        # a real token — skip if none is available
        real_token = os.environ.get("IBM_TOKEN")
        if not real_token:
            pytest.skip("IBM_TOKEN not set")

        monkeypatch.setenv("IBM_TOKEN", real_token)

        from uniqc.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        assert isinstance(adapter.is_available(), bool)


# ---------------------------------------------------------------------------
# OriginQ adapter unit tests (mock-based)
# ---------------------------------------------------------------------------


class TestOriginQAdapterUnit:
    """Unit tests for OriginQ adapter using mocks."""

    def run_test_format_counts_returns_dict(self, monkeypatch):
        """_format_counts returns {bitstring: shots} dict, not list of dicts."""
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key_123")
        from uniqc.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = None
        adapter._QCloudOptions = None
        adapter._QCloudJob = None
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._convert_originir = None

        # dict input
        result = adapter._format_counts({"00": 512, "11": 488})
        assert isinstance(result, dict)
        assert result == {"00": 512, "11": 488}

        # list of dicts (batch) — counts should be merged
        result = adapter._format_counts([{"00": 256}, {"00": 256, "11": 488}])
        assert isinstance(result, dict)
        assert result == {"00": 512, "11": 488}

        # non-dict/list fallback
        result = adapter._format_counts("something")
        assert isinstance(result, dict)
        assert result == {"something": 1}

    def run_test_get_chip_characterization_double_qubits_no_uv_accessor(self, monkeypatch):
        """get_chip_characterization falls back to topology index when dq lacks u/v accessors.

        Some pyqpanda3 chip_info() implementations return double_qubits_info() objects
        that have get_fidelity() but lack get_qubit_u() / get_qubit_v(). The adapter
        must use the topology index to look up the qubit pair instead of crashing.
        """
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key_123")

        # Minimal mock objects
        mock_sq = type("MockSQ", (), {
            "get_qubit_id": lambda self: 0,
            "get_t1": lambda self: 50.0,
            "get_t2": lambda self: 80.0,
            "get_single_gate_fidelity": lambda self: 0.99,
            "get_readout_fidelity": lambda self: 0.95,
            "get_readout_fidelity_0": lambda self: 0.97,
            "get_readout_fidelity_1": lambda self: 0.93,
        })()

        mock_dq = type("MockDQ", (), {
            # No get_qubit_u / get_qubit_v — this is the case being tested
            "get_fidelity": lambda self: 0.85,
        })()

        mock_ci = type("MockCI", (), {
            "qubits_num": lambda self: 5,
            "get_chip_topology": lambda self: [(0, 1), (1, 2), (2, 3)],
            "available_qubits": lambda self: [0, 1, 2, 3, 4],
            "single_qubit_info": lambda self: [mock_sq],
            "double_qubits_info": lambda self: [mock_dq],
        })()

        mock_backend = type("MockBackend", (), {
            "chip_info": lambda self: mock_ci,
            "configuration": lambda self: type("MockCfg", (), {
                "supported_gates": lambda self: ["x", "h", "cx", "cz"],
                "single_qubit_gate_time": lambda self: 20.0,
                "two_qubit_gate_time": lambda self: 300.0,
            })(),
        })()

        mock_service = type("MockService", (), {
            "backend": lambda self, name: mock_backend,
        })()

        from uniqc.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = mock_service
        adapter._QCloudOptions = None
        adapter._QCloudJob = None
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._QCloudSimulator = None
        adapter._convert_originir = None

        chip = adapter.get_chip_characterization("wuyuan:d5")

        assert chip is not None
        assert len(chip.two_qubit_data) == 1
        # Fallback to topology: index 0 → (0, 1)
        assert chip.two_qubit_data[0].qubit_u == 0
        assert chip.two_qubit_data[0].qubit_v == 1
        # Fidelity was available even without u/v accessors
        assert chip.two_qubit_data[0].gates[0].fidelity == 0.85
