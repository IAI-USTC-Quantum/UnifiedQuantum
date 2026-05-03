"""Tests for the optional_deps module.

Run with: pytest uniqc/test/test_optional_deps.py --ignore-glob='uniqc/test/__init__.py' -v
"""

from __future__ import annotations

import pytest

from uniqc.backend_adapter.task.optional_deps import (
    MissingDependencyError,
    require,
    check_quafu,
    check_qiskit,
    check_pyqpanda3,
    check_uniqc_cpp,
    check_qutip,
    check_simulation,
    QUAFU_AVAILABLE,
    QISKIT_AVAILABLE,
    PYQPANDA3_AVAILABLE,
    UNIQC_CPP_AVAILABLE,
    QUTIP_AVAILABLE,
    SIMULATION_AVAILABLE,
)


class TestMissingDependencyError:
    """Tests for MissingDependencyError."""

    def test_error_message_format(self):
        """Test that error message includes install instructions."""
        error = MissingDependencyError("quafu", "quafu")
        assert "quafu" in str(error)
        assert "pip install unified-quantum[quafu]" in str(error)

    def test_error_attributes(self):
        """Test error attributes are set correctly."""
        error = MissingDependencyError("qiskit", "qiskit")
        assert error.package == "qiskit"
        assert error.extra == "qiskit"

    def test_is_import_error_subclass(self):
        """Test that MissingDependencyError is an ImportError."""
        error = MissingDependencyError("test", "test")
        assert isinstance(error, ImportError)


class TestRequireFunction:
    """Tests for the require function."""

    def test_require_missing_module(self):
        """Test require raises MissingDependencyError for missing module."""
        with pytest.raises(MissingDependencyError) as exc_info:
            require("nonexistent_module_xyz", "test")
        assert exc_info.value.package == "nonexistent_module_xyz"

    def test_require_existing_module(self):
        """Test require returns module for existing module."""
        import os
        mod = require("os", "test")
        assert mod is os


class TestCheckFunctions:
    """Tests for availability check functions."""

    def test_check_quafu_returns_bool(self):
        """Test check_quafu returns boolean."""
        result = check_quafu()
        assert isinstance(result, bool)

    def test_check_qiskit_returns_bool(self):
        """Test check_qiskit returns boolean."""
        result = check_qiskit()
        assert isinstance(result, bool)

    def test_check_pyqpanda3_returns_bool(self):
        """Test check_pyqpanda3 returns boolean."""
        result = check_pyqpanda3()
        assert isinstance(result, bool)

    def test_check_simulation_returns_bool(self):
        """Test check_simulation returns boolean."""
        result = check_simulation()
        assert isinstance(result, bool)

    def test_check_uniqc_cpp_returns_bool(self):
        """Test check_uniqc_cpp returns boolean."""
        result = check_uniqc_cpp()
        assert isinstance(result, bool)

    def test_check_qutip_returns_bool(self):
        """Test check_qutip returns boolean."""
        result = check_qutip()
        assert isinstance(result, bool)

    def test_check_simulation_all_returns_bool(self):
        """Test check_simulation('all') returns boolean."""
        result = check_simulation("all")
        assert isinstance(result, bool)

    def test_check_simulation_invalid_target_raises(self):
        """Test check_simulation rejects unknown targets."""
        with pytest.raises(ValueError, match="Unsupported simulation target"):
            check_simulation("unknown")


class TestAvailabilityFlags:
    """Tests for pre-computed availability flags."""

    def test_quafu_available_is_bool(self):
        """Test QUAFU_AVAILABLE is boolean."""
        assert isinstance(QUAFU_AVAILABLE, bool)

    def test_qiskit_available_is_bool(self):
        """Test QISKIT_AVAILABLE is boolean."""
        assert isinstance(QISKIT_AVAILABLE, bool)

    def test_pyqpanda3_available_is_bool(self):
        """Test PYQPANDA3_AVAILABLE is boolean."""
        assert isinstance(PYQPANDA3_AVAILABLE, bool)

    def test_simulation_available_is_bool(self):
        """Test SIMULATION_AVAILABLE is boolean."""
        assert isinstance(SIMULATION_AVAILABLE, bool)

    def test_uniqc_cpp_available_is_bool(self):
        """Test UNIQC_CPP_AVAILABLE is boolean."""
        assert isinstance(UNIQC_CPP_AVAILABLE, bool)

    def test_qutip_available_is_bool(self):
        """Test QUTIP_AVAILABLE is boolean."""
        assert isinstance(QUTIP_AVAILABLE, bool)
