"""Optional dependency management with clear error messages.

This module provides utilities for handling optional dependencies across
different quantum cloud platforms. When a dependency is not installed,
users receive clear instructions on how to install it.

Usage::

    # Check if dependency is available
    from uniqc.backend_adapter.task.optional_deps import QUAFU_AVAILABLE
    if QUAFU_AVAILABLE:
        from uniqc.backend_adapter.task.adapters.quafu_adapter import QuafuAdapter

    # Require dependency with error message
    from uniqc.backend_adapter.task.optional_deps import require
    quafu = require("quafu", "quafu")  # Raises MissingDependencyError if not installed
"""

from __future__ import annotations

import importlib

from uniqc.exceptions import MissingDependencyError  # noqa: F401 — re-export

__all__ = [
    "MissingDependencyError",
    "require",
    "check_quafu",
    "check_quark",
    "check_quarkcircuit",
    "check_qiskit",
    "check_pyqpanda3",
    "check_uniqc_cpp",
    "check_qutip",
    "check_simulation",
    "QUAFU_AVAILABLE",
    "QUARK_AVAILABLE",
    "QUARKCIRCUIT_AVAILABLE",
    "QISKIT_AVAILABLE",
    "PYQPANDA3_AVAILABLE",
    "UNIQC_CPP_AVAILABLE",
    "QUTIP_AVAILABLE",
    "SIMULATION_AVAILABLE",
]


def require(name: str, extra: str):
    """Import an optional module with a clear error message if missing.

    Args:
        name: The module name to import (e.g., 'quafu', 'qiskit').
        extra: The pip extras name for installation (e.g., 'quafu', 'qiskit').

    Returns:
        The imported module.

    Raises:
        MissingDependencyError: If the module cannot be imported.

    Example:
        >>> quafu = require("quafu", "quafu")
        >>> # If quafu is not installed:
        >>> # MissingDependencyError: Package 'quafu' is required...
    """
    try:
        return importlib.import_module(name)
    except ImportError as e:
        raise MissingDependencyError(name, extra) from e
    except Exception as e:
        raise MissingDependencyError(
            name,
            extra,
            install_hint=(
                f"The package is installed but failed to import cleanly: {e!r}. "
                f"Upgrade or reinstall with: pip install --upgrade unified-quantum[{extra}]"
            ),
        ) from e


def _can_import(*names: str) -> bool:
    """Return ``True`` only if all optional modules import cleanly."""
    try:
        for name in names:
            importlib.import_module(name)
        return True
    except Exception:
        return False


def check_quafu() -> bool:
    """Check if the quafu package is available.

    Returns:
        True if quafu can be imported, False otherwise.
    """
    return _can_import("quafu")


def check_quark() -> bool:
    """Check if the QuarkStudio package is available.

    Returns:
        True if ``from quark import Task`` succeeds, False otherwise.
    """
    try:
        module = importlib.import_module("quark")
        _ = module.Task
        return True
    except Exception:
        return False


def check_quarkcircuit() -> bool:
    """Check if QuarkStudio's circuit metadata module is available."""
    return _can_import("quark.circuit.backend")


def check_qiskit() -> bool:
    """Check if the qiskit and qiskit_ibm_runtime packages are available.

    Returns:
        True if both packages can be imported, False otherwise.
    """
    return _can_import("qiskit", "qiskit_ibm_runtime")


def check_pyqpanda3() -> bool:
    """Check if the pyqpanda3 package is available.

    Returns:
        True if pyqpanda3 can be imported, False otherwise.
    """
    return _can_import("pyqpanda3")


def check_uniqc_cpp() -> bool:
    """Check if the uniqc_cpp C++ simulator extension is available.

    Returns:
        True if uniqc_cpp can be imported, False otherwise.
    """
    return _can_import("uniqc_cpp")


def check_qutip() -> bool:
    """Check if the QuTiP-based simulation stack is available.

    Returns:
        True if qutip and qutip_qip can be imported, False otherwise.
    """
    return _can_import("qutip", "qutip_qip")


def check_simulation(target: str = "cpp") -> bool:
    """Check simulation support for a specific backend family.

    Args:
        target: Which simulation capability to check.
            - ``"cpp"``: built-in C++ simulator extension (default)
            - ``"qutip"``: QuTiP-based simulation stack
            - ``"all"``: both C++ simulator and QuTiP stack

    Returns:
        True if the requested simulation target is available, False otherwise.

    Raises:
        ValueError: If ``target`` is not one of ``"cpp"``, ``"qutip"``, or ``"all"``.
    """
    if target == "cpp":
        return check_uniqc_cpp()
    if target == "qutip":
        return check_qutip()
    if target == "all":
        return check_uniqc_cpp() and check_qutip()
    raise ValueError(f"Unsupported simulation target: {target}")


# Pre-computed availability flags (evaluated at module load time)
QUAFU_AVAILABLE = check_quafu()
QUARK_AVAILABLE = check_quark()
QUARKCIRCUIT_AVAILABLE = check_quarkcircuit()
QISKIT_AVAILABLE = check_qiskit()
PYQPANDA3_AVAILABLE = check_pyqpanda3()
UNIQC_CPP_AVAILABLE = check_uniqc_cpp()
QUTIP_AVAILABLE = check_qutip()
SIMULATION_AVAILABLE = UNIQC_CPP_AVAILABLE
