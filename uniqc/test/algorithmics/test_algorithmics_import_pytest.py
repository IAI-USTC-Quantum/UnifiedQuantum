"""Pytest tests for algorithmics package imports."""

import builtins
import importlib
import sys
from unittest.mock import patch


def _clear_modules(prefixes):
    """Remove cached modules so import behavior can be re-evaluated."""
    for name in list(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)


def _block_simulator_imports():
    """Raise if ansatz imports accidentally pull simulator dependencies."""
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "uniqc_cpp" or name.startswith("uniqc.simulator"):
            raise ModuleNotFoundError(f"blocked simulator import during test: {name}", name=name)
        return original_import(name, globals, locals, fromlist, level)

    return patch("builtins.__import__", side_effect=guarded_import)


class TestAlgorithmicsImport:
    """Tests for algorithmics import behavior."""

    def test_ansatz_import_does_not_require_simulator_stack(self):
        """Importing ansatz should not eagerly load measurement or simulator modules."""
        _clear_modules(
            [
                "uniqc.algorithmics",
                "uniqc.algorithmics.ansatz",
                "uniqc.algorithmics.measurement",
                "uniqc.simulator",
            ]
        )

        with _block_simulator_imports():
            module = importlib.import_module("uniqc.algorithmics.ansatz")

        assert module.hea is not None
