"""Tests for the task adapter layer.

These tests verify that:
1. Each adapter correctly translates OriginIR to provider-native circuits.
2. Config is loaded from ``~/.uniqc/config.yaml`` via the active profile.
3. Task modules delegate to adapters.

Cloud tests require real credentials and are marked with @pytest.mark.cloud.
"""

from __future__ import annotations

import pytest

from uniqc.test.cloud._config_helpers import write_uniqc_config

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


class RunTestConfigYaml:
    """Config loading from the active YAML profile."""

    def run_test_originq_config_from_yaml(self, monkeypatch, tmp_path):
        """OriginQ config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(
            tmp_path,
            {"originq": {"token": "test_key_123", "task_group_size": 100}},
        )
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_originq_config

        config = load_originq_config()
        assert config["api_key"] == "test_key_123"
        assert config["task_group_size"] == 100

    def run_test_quafu_config_from_yaml(self, monkeypatch, tmp_path):
        """Quafu config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(tmp_path, {"quafu": {"token": "quafu_secret_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_quafu_config

        config = load_quafu_config()
        assert config["api_token"] == "quafu_secret_token"

    def run_test_quark_config_from_yaml(self, monkeypatch, tmp_path):
        """QuarkStudio config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(tmp_path, {"quark": {"token": "quark_secret_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_quark_config

        config = load_quark_config()
        assert config["api_token"] == "quark_secret_token"

    def run_test_ibm_config_from_yaml(self, monkeypatch, tmp_path):
        """IBM config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(tmp_path, {"ibm": {"token": "ibm_secret_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_ibm_config

        config = load_ibm_config()
        assert config["api_token"] == "ibm_secret_token"

    def run_test_dummy_config_from_yaml(self, monkeypatch, tmp_path):
        """OriginQ Dummy config is read from the OriginQ YAML section."""
        write_uniqc_config(
            tmp_path,
            {
                "originq": {
                    "token": "",
                    "available_qubits": [0, 1, 2, 3],
                    "available_topology": [[0, 1], [1, 2], [2, 3]],
                    "task_group_size": 50,
                }
            },
        )
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_dummy_config

        config = load_dummy_config()
        assert config["available_qubits"] == [0, 1, 2, 3]
        assert config["available_topology"] == [[0, 1], [1, 2], [2, 3]]
        assert config["task_group_size"] == 50

    def run_test_originq_config_import_error_without_token(self, monkeypatch, tmp_path):
        """ImportError is raised when the active YAML config has no OriginQ token."""
        write_uniqc_config(tmp_path, {"originq": {"token": ""}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_originq_config

        with pytest.raises(ImportError, match="originq.token"):
            load_originq_config()

    def run_test_active_profile_is_used(self, monkeypatch, tmp_path):
        """Task config respects active_profile from ~/.uniqc/config.yaml."""
        from uniqc.backend_adapter.config import save_config

        config_file = tmp_path / ".uniqc" / "config.yaml"
        save_config(
            {
                "active_profile": "prod",
                "default": {"originq": {"token": "default-token"}},
                "prod": {"originq": {"token": "prod-token"}},
            },
            config_file,
        )
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", config_file)

        from uniqc.config import load_originq_config

        cfg = load_originq_config()
        assert cfg["api_key"] == "prod-token"


# ---------------------------------------------------------------------------
# OriginQ adapter tests (require credentials)
# ---------------------------------------------------------------------------


@pytest.mark.cloud
@pytest.mark.requires_pyqpanda3
class RunTestOriginQAdapterIntegration:
    """Integration tests for OriginQ adapter with real pyqpanda3 and credentials."""

    def run_test_translate_circuit(self):
        """Test that translate_circuit converts OriginIR to QProg."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        result = adapter.translate_circuit(ORIGINIR_BELL)
        assert result is not None

    @pytest.mark.real_cloud_execution
    def run_test_submit_and_query(self):
        """Test submit and query with real service."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        task_id = adapter.submit(ORIGINIR_BELL, shots=1000)
        assert task_id is not None

        result = adapter.query(task_id)
        assert "status" in result

    @pytest.mark.real_cloud_execution
    def run_test_submit_batch(self):
        """Test submit_batch with real service."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        circuits = [ORIGINIR_BELL] * 2
        task_ids = adapter.submit_batch(circuits, shots=1000)
        assert len(task_ids) >= 1


# ---------------------------------------------------------------------------
# Quafu adapter tests (require credentials)
# ---------------------------------------------------------------------------


@pytest.mark.cloud
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

        from uniqc.backend_adapter.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        result = adapter.translate_circuit(originir)
        assert result is not None

    @pytest.mark.real_cloud_execution
    def run_test_submit_and_query(self):
        """Test submit and query with real service."""
        from uniqc.backend_adapter.task.adapters import QuafuAdapter

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
@pytest.mark.requires_qiskit
class RunTestIBMAdapterIntegration:
    """Integration tests for IBM adapter with real qiskit and credentials."""

    def run_test_translate_circuit(self):
        """Test circuit translation with real qiskit."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        result = adapter.translate_circuit(ORIGINIR_BELL)
        assert result is not None
        assert hasattr(result, "num_qubits")

    def run_test_service_init_and_translate(self):
        """Test real IBM service initialisation and circuit translation."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()

        adapter.translate_circuit(ORIGINIR_BELL)
        # Note: IBM submission requires backend selection
        # This test may need adjustment based on available backends


# ---------------------------------------------------------------------------
# Adapter availability tests
# ---------------------------------------------------------------------------


class RunTestAdapterAvailability:
    """Each adapter reports availability based on installed packages / config."""

    def run_test_originq_adapter_available_with_config(self, monkeypatch, tmp_path):
        """Test OriginQ adapter availability with config."""
        write_uniqc_config(tmp_path, {"originq": {"token": "test_key"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        assert adapter.is_available() is True

    @pytest.mark.requires_quafu
    def run_test_quafu_adapter_available_with_config(self, monkeypatch, tmp_path):
        """Test Quafu adapter availability with config."""
        write_uniqc_config(tmp_path, {"quafu": {"token": "test_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.backend_adapter.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        assert isinstance(adapter.is_available(), bool)

    def run_test_ibm_adapter_available_with_config(self, monkeypatch, tmp_path):
        """Test IBM adapter availability with config."""
        write_uniqc_config(tmp_path, {"ibm": {"token": "test_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", lambda **_kwargs: object())

        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        assert isinstance(adapter.is_available(), bool)


# ---------------------------------------------------------------------------
# OriginQ adapter unit tests (mock-based)
# ---------------------------------------------------------------------------


class TestOriginQAdapterUnit:
    """Unit tests for OriginQ adapter using mocks."""

    def run_test_format_counts_returns_dict(self):
        """_format_counts returns {bitstring: shots} dict, not list of dicts."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

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

    def run_test_get_chip_characterization_double_qubits_no_uv_accessor(self):
        """get_chip_characterization falls back to topology index when dq lacks u/v accessors.

        Some pyqpanda3 chip_info() implementations return double_qubits_info() objects
        that have get_fidelity() but lack get_qubit_u() / get_qubit_v(). The adapter
        must use the topology index to look up the qubit pair instead of crashing.
        """
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

        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = mock_service
        adapter._QCloudOptions = None
        adapter._QCloudJob = None
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._convert_originir = None

        chip = adapter.get_chip_characterization("wuyuan:d5")

        assert chip is not None
        assert len(chip.two_qubit_data) == 1
        # Fallback to topology: index 0 → (0, 1)
        assert chip.two_qubit_data[0].qubit_u == 0
        assert chip.two_qubit_data[0].qubit_v == 1
        # Fidelity was available even without u/v accessors
        assert chip.two_qubit_data[0].gates[0].fidelity == 0.85
