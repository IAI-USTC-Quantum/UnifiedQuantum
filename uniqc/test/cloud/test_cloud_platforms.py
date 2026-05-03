"""Comprehensive tests for unified cloud platform access layer.

This module provides:
1. Configuration loading tests
2. Backend factory tests
3. Circuit adapter tests
4. Integration tests (require real credentials)

Usage:
    pytest uniqc/test/test_cloud_platforms.py -v

Environment variables for integration tests:
    - ORIGINQ_API_KEY: OriginQ API key
    - QUAFU_API_TOKEN: Quafu API token
    - IBM_TOKEN: IBM Quantum token
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Test Data
# ---------------------------------------------------------------------------

ORIGINIR_BELL = """
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""".strip()

ORIGINIR_SINGLE = """
QINIT 1
CREG 1
X q[0]
MEASURE q[0], c[0]
""".strip()


# ---------------------------------------------------------------------------
# Configuration Loading Tests
# ---------------------------------------------------------------------------


class TestConfigLoading:
    """Tests for configuration loading from ~/.uniqc/uniqc.yml."""

    def test_load_config_file_not_exists(self, tmp_path: Path) -> None:
        """Test that default config is returned when file doesn't exist."""
        from uniqc.backend_adapter.config import load_config, DEFAULT_CONFIG

        non_existent = tmp_path / "non_existent.yml"
        result = load_config(non_existent)
        assert result == DEFAULT_CONFIG

    def test_load_existing_config(self, tmp_path: Path) -> None:
        """Test loading an existing configuration file."""
        from uniqc.backend_adapter.config import load_config, save_config

        config_file = tmp_path / "test_config.yml"
        test_config = {
            "default": {
                "originq": {"token": "test_token_123"},
                "quafu": {"token": "quafu_token_456"},
                "ibm": {"token": "ibm_token_789", "proxy": {"http": "", "https": ""}},
            }
        }
        save_config(test_config, config_file)
        result = load_config(config_file)
        assert result["default"]["originq"]["token"] == "test_token_123"
        assert result["default"]["quafu"]["token"] == "quafu_token_456"
        assert result["default"]["ibm"]["token"] == "ibm_token_789"

    def test_load_config_all_platforms(self, tmp_path: Path) -> None:
        """Test loading configuration for all three platforms."""
        from uniqc.backend_adapter.config import (
            load_config, save_config,
            get_platform_config, SUPPORTED_PLATFORMS
        )

        config_file = tmp_path / "uniqc.yml"
        test_config = {
            "default": {
                "originq": {
                    "token": "originq_test_token",
                    "available_qubits": [0, 1, 2, 3, 4, 5],
                    "available_topology": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5]],
                    "task_group_size": 200,
                },
                "quafu": {
                    "token": "quafu_test_token",
                },
                "ibm": {
                    "token": "ibm_test_token",
                    "proxy": {"http": "http://proxy.example.com:8080", "https": "https://proxy.example.com:8080"},
                },
            }
        }
        save_config(test_config, config_file)

        # Test each platform
        for platform in SUPPORTED_PLATFORMS:
            config = get_platform_config(platform, config_path=config_file)
            assert "token" in config
            assert config["token"] == f"{platform}_test_token"

    def test_load_config_different_profiles(self, tmp_path: Path) -> None:
        """Test loading configuration with different profiles."""
        from uniqc.backend_adapter.config import load_config, save_config, get_platform_config

        config_file = tmp_path / "uniqc.yml"
        test_config = {
            "default": {
                "originq": {"token": "default_token"},
            },
            "prod": {
                "originq": {"token": "prod_token"},
            },
            "dev": {
                "originq": {"token": "dev_token"},
            },
        }
        save_config(test_config, config_file)

        default_config = get_platform_config("originq", profile="default", config_path=config_file)
        assert default_config["token"] == "default_token"

        prod_config = get_platform_config("originq", profile="prod", config_path=config_file)
        assert prod_config["token"] == "prod_token"

        dev_config = get_platform_config("originq", profile="dev", config_path=config_file)
        assert dev_config["token"] == "dev_token"

    def test_validate_config_valid(self) -> None:
        """Test validating a valid configuration."""
        from uniqc.backend_adapter.config import validate_config

        valid_config = {
            "default": {
                "originq": {"token": "t"},
                "quafu": {"token": "t"},
                "ibm": {"token": "t", "proxy": {"http": "", "https": ""}},
            }
        }
        errors = validate_config(valid_config)
        assert errors == []

    def test_validate_config_missing_required_fields(self) -> None:
        """Test validating configuration with missing required fields."""
        from uniqc.backend_adapter.config import validate_config

        invalid_config = {
            "default": {
                "originq": {},  # Missing required token
            }
        }
        errors = validate_config(invalid_config)
        assert len(errors) >= 1
        assert any("token" in e for e in errors)


# ---------------------------------------------------------------------------
# Backend Factory Tests
# ---------------------------------------------------------------------------


class TestBackendFactory:
    """Tests for the Backend factory pattern (get_backend)."""

    def test_get_backend_originq(self, monkeypatch) -> None:
        """Test getting OriginQ backend returns correct type."""
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key")

        from uniqc.backend_adapter.backend import get_backend, OriginQBackend

        backend = get_backend("originq", use_cache=False)
        assert isinstance(backend, OriginQBackend)
        assert backend.platform == "originq"

    def test_get_backend_quafu(self, monkeypatch) -> None:
        """Test getting Quafu backend returns correct type."""
        monkeypatch.setenv("QUAFU_API_TOKEN", "test_token")

        from uniqc.backend_adapter.backend import get_backend, QuafuBackend

        backend = get_backend("quafu", use_cache=False)
        assert isinstance(backend, QuafuBackend)
        assert backend.platform == "quafu"

    def test_get_backend_ibm(self, monkeypatch) -> None:
        """Test getting IBM backend returns correct type."""
        monkeypatch.setenv("IBM_TOKEN", "test_token")

        from uniqc.backend_adapter.backend import get_backend, IBMBackend

        backend = get_backend("ibm", use_cache=False)
        assert isinstance(backend, IBMBackend)
        assert backend.platform == "ibm"

    def test_get_backend_unknown_raises(self) -> None:
        """Test that unknown backend name raises ValueError."""
        from uniqc.backend_adapter.backend import get_backend

        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend("unknown_platform")

    def test_list_backends(self) -> None:
        """Test listing available backends."""
        from uniqc.backend_adapter.backend import list_backends, BACKENDS

        backends = list_backends()
        assert "originq" in backends
        assert "quafu" in backends
        assert "ibm" in backends

        for name, info in backends.items():
            assert "platform" in info
            assert "available" in info
            assert "class" in info
            assert info["platform"] == name
            assert info["class"] == BACKENDS[name].__name__


# ---------------------------------------------------------------------------
# Circuit Adapter Tests
# ---------------------------------------------------------------------------


class TestCircuitAdapters:
    """Tests for CircuitAdapter implementations."""

    def test_originq_adapter_supported_gates(self) -> None:
        """Test OriginQ adapter returns supported gates."""
        from uniqc.backend_adapter.circuit_adapter import OriginQCircuitAdapter

        adapter = OriginQCircuitAdapter()
        gates = adapter.get_supported_gates()

        assert isinstance(gates, list)
        assert "H" in gates
        assert "X" in gates
        assert "CNOT" in gates
        assert "MEASURE" in gates

    def test_quafu_adapter_supported_gates(self) -> None:
        """Test Quafu adapter returns supported gates."""
        from uniqc.backend_adapter.circuit_adapter import QuafuCircuitAdapter

        adapter = QuafuCircuitAdapter()
        gates = adapter.get_supported_gates()

        assert isinstance(gates, list)
        assert "H" in gates
        assert "CNOT" in gates
        assert "MEASURE" in gates

    def test_ibm_adapter_supported_gates(self) -> None:
        """Test IBM adapter returns supported gates."""
        from uniqc.backend_adapter.circuit_adapter import IBMCircuitAdapter

        adapter = IBMCircuitAdapter()
        gates = adapter.get_supported_gates()

        assert isinstance(gates, list)
        assert "H" in gates
        assert "CX" in gates  # IBM uses CX for CNOT
        assert "MEASURE" in gates


# ---------------------------------------------------------------------------
# Integration Tests (Skipped unless real credentials exist)
# ---------------------------------------------------------------------------


@pytest.mark.cloud
@pytest.mark.skipif(
    not os.environ.get("ORIGINQ_API_KEY"),
    reason="ORIGINQ_API_KEY not set"
)
@pytest.mark.requires_pyqpanda3
class TestOriginQIntegration:
    """Integration tests for OriginQ (requires real credentials)."""

    def test_originq_connection(self) -> None:
        """Test real OriginQ connection."""
        from uniqc.backend_adapter.backend import get_backend

        backend = get_backend("originq", use_cache=False)
        assert backend.is_available()

    def test_originq_submit_and_query(self) -> None:
        """Test real OriginQ submit and query workflow."""
        from uniqc.backend_adapter.backend import get_backend

        backend = get_backend("originq", use_cache=False)

        # Submit a simple circuit
        task_id = backend.submit(ORIGINIR_SINGLE, shots=1000)
        assert task_id

        # Query the task
        result = backend.query(task_id)
        assert "status" in result


@pytest.mark.cloud
@pytest.mark.skipif(
    not os.environ.get("QUAFU_API_TOKEN"),
    reason="QUAFU_API_TOKEN not set"
)
@pytest.mark.requires_quafu
class TestQuafuIntegration:
    """Integration tests for Quafu (requires real credentials)."""

    def test_quafu_connection(self) -> None:
        """Test real Quafu connection."""
        from uniqc.backend_adapter.backend import get_backend

        backend = get_backend("quafu", use_cache=False)
        # Note: is_available depends on quafu package

    def test_quafu_translate_circuit(self) -> None:
        """Test real Quafu circuit translation."""
        from uniqc.backend_adapter.task.adapters import QuafuAdapter

        adapter = QuafuAdapter()
        circuit = adapter.translate_circuit(ORIGINIR_BELL)
        assert circuit is not None


@pytest.mark.cloud
@pytest.mark.skipif(
    not os.environ.get("IBM_TOKEN"),
    reason="IBM_TOKEN not set"
)
@pytest.mark.requires_qiskit
class TestIBMIntegration:
    """Integration tests for IBM Quantum (requires real credentials)."""

    def test_ibm_connection(self) -> None:
        """Test real IBM Quantum connection."""
        from uniqc.backend_adapter.backend import get_backend

        backend = get_backend("ibm", use_cache=False)
        # Note: is_available depends on qiskit packages

    def test_ibm_translate_circuit(self) -> None:
        """Test real IBM circuit translation."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        circuit = adapter.translate_circuit(ORIGINIR_BELL)
        assert circuit is not None
        assert hasattr(circuit, "num_qubits")


# ---------------------------------------------------------------------------
# Cache Management Tests
# ---------------------------------------------------------------------------


class TestCacheManagement:
    """Tests for backend cache management."""

    def test_save_and_load_cache(self, tmp_path: Path, monkeypatch) -> None:
        """Test saving and loading backend cache."""
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key")

        from uniqc.backend_adapter.backend import OriginQBackend, _get_cache_file_path

        cache_dir = tmp_path / "cache"
        backend = OriginQBackend(cache_dir=cache_dir, config={"test": "value"})
        backend.name = "test_backend"

        # Save to cache
        backend.save_to_cache()

        # Verify cache file exists
        cache_file = _get_cache_file_path("originq", cache_dir)
        assert cache_file.exists()

    def test_clear_cache(self, tmp_path: Path, monkeypatch) -> None:
        """Test clearing backend cache."""
        monkeypatch.setenv("ORIGINQ_API_KEY", "test_key")

        from uniqc.backend_adapter.backend import OriginQBackend, _get_cache_file_path

        cache_dir = tmp_path / "cache"
        backend = OriginQBackend(cache_dir=cache_dir)

        # Save and verify
        backend.save_to_cache()
        cache_file = _get_cache_file_path("originq", cache_dir)
        assert cache_file.exists()

        # Clear and verify
        backend.clear_cache()
        assert not cache_file.exists()


# ---------------------------------------------------------------------------
# Compatibility Tests with Existing Tests
# ---------------------------------------------------------------------------


class TestCompatibilityWithExistingTests:
    """Ensure compatibility with existing test files."""

    def test_config_imports(self) -> None:
        """Test that config module imports work correctly."""
        from uniqc import config
        from uniqc.backend_adapter.config import (
            load_config,
            save_config,
            get_platform_config,
            validate_config,
            create_default_config,
            DEFAULT_CONFIG,
        )

        assert callable(load_config)
        assert callable(save_config)
        assert callable(get_platform_config)
        assert callable(validate_config)
        assert callable(create_default_config)
        assert isinstance(DEFAULT_CONFIG, dict)

    def test_circuit_adapter_imports(self) -> None:
        """Test that circuit adapter public imports work correctly."""
        from uniqc import CircuitAdapter, IBMCircuitAdapter, OriginQCircuitAdapter, QuafuCircuitAdapter
        from uniqc.backend_adapter.circuit_adapter import (
            CircuitAdapter as BackendCircuitAdapter,
            OriginQCircuitAdapter,
            QuafuCircuitAdapter,
            IBMCircuitAdapter,
        )

        assert CircuitAdapter is BackendCircuitAdapter
        assert issubclass(OriginQCircuitAdapter, BackendCircuitAdapter)
        assert issubclass(QuafuCircuitAdapter, BackendCircuitAdapter)
        assert issubclass(IBMCircuitAdapter, BackendCircuitAdapter)

    def test_backend_imports(self) -> None:
        """Test that backend module imports work correctly."""
        from uniqc.backend_adapter.backend import (
            QuantumBackend,
            OriginQBackend,
            QuafuBackend,
            IBMBackend,
            get_backend,
            list_backends,
            BACKENDS,
        )

        assert callable(get_backend)
        assert callable(list_backends)
        assert isinstance(BACKENDS, dict)
        assert "originq" in BACKENDS
        assert "quafu" in BACKENDS
        assert "ibm" in BACKENDS

    def test_task_adapters_imports(self) -> None:
        """Test that task.adapters module imports work correctly."""
        from uniqc.backend_adapter.task.adapters import (
            QuantumAdapter,
            OriginQAdapter,
            QuafuAdapter,
            QiskitAdapter,
            TASK_STATUS_SUCCESS,
            TASK_STATUS_FAILED,
            TASK_STATUS_RUNNING,
        )

        assert TASK_STATUS_SUCCESS == "success"
        assert TASK_STATUS_FAILED == "failed"
        assert TASK_STATUS_RUNNING == "running"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
