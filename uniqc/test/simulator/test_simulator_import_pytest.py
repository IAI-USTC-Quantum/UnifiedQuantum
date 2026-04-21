"""Pytest tests for simulator module imports."""
import builtins
import importlib
import sys
import warnings
from unittest.mock import patch


def _clear_modules(prefixes):
    """Remove cached modules so import behavior can be re-evaluated."""
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)


def _block_optional_qutip_imports():
    """Raise if a test accidentally imports QuTiP-backed optional dependencies."""
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        top_level_name = name.split(".", 1)[0]
        if top_level_name in {"qutip", "qutip_qip"}:
            raise ModuleNotFoundError(f"blocked optional dependency import: {name}", name=name)
        return original_import(name, globals, locals, fromlist, level)

    return patch("builtins.__import__", side_effect=guarded_import)


class TestSimulatorImport:
    """Tests for simulator import behavior."""

    def test_simulator_imports_originir_simulator(self):
        """Test that OriginIR_Simulator is importable."""
        module = importlib.import_module("uniqc.simulator")

        assert module.OriginIR_Simulator is not None
        assert module.OriginIR_NoisySimulator is not None

    def test_simulator_warning_on_missing_cpp(self):
        """Test that a warning is issued when uniqc_cpp is not available."""
        # This test verifies the warning message is correct
        # by re-importing the module with a clean slate
        # Remove the module from cache if present
        if "uniqc.simulator" in sys.modules:
            del sys.modules["uniqc.simulator"]

        # Try to import and check the warning message
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            module = importlib.import_module("uniqc.simulator")

            # Check if a warning was issued (only if C++ backend is missing)
            assert module is not None
            if len(w) > 0:
                assert "uniqc is not installed with UniqcCpp" in str(w[0].message)

    def test_originir_import_does_not_require_qutip(self):
        """Statevector/cpp simulator imports should not eagerly pull in QuTiP."""
        _clear_modules(
            [
                "uniqc.simulator",
                "uniqc.simulator.originir_simulator",
                "uniqc.simulator.opcode_simulator",
                "uniqc.simulator.qutip_sim_impl",
            ]
        )

        with _block_optional_qutip_imports():
            module = importlib.import_module("uniqc.simulator")

        assert module.OriginIR_Simulator is not None
