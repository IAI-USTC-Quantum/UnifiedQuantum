"""Custom exceptions for UnifiedQuantum.

This module is the single source of truth for **all** custom exceptions in the
package.  Sub-modules re-export from here so that legacy import paths continue
to work, but every exception class is defined in this file.

Exception hierarchy::

    UnifiedQuantumError
    ├── AuthenticationError
    ├── InsufficientCreditsError
    ├── QuotaExceededError
    ├── NetworkError
    ├── TaskFailedError
    ├── TaskTimeoutError
    ├── TaskNotFoundError
    ├── BackendError
    │   ├── BackendNotAvailableError
    │   └── BackendNotFoundError
    ├── CircuitError
    │   ├── CircuitTranslationError
    │   ├── UnsupportedGateError
    │   ├── NotSupportedGateError
    │   ├── RegisterNotFoundError
    │   ├── RegisterOutOfRangeError
    │   ├── RegisterDefinitionError
    │   ├── NotMatrixableError
    │   └── TimelineDurationError
    ├── ConfigError
    │   ├── ConfigValidationError
    │   ├── PlatformNotFoundError
    │   └── ProfileNotFoundError
    ├── CompilationFailedError
    ├── TopologyError
    ├── StaleCalibrationError
    ├── BackendOptionsError  (also ValueError)
    └── MissingDependencyError  (also ImportError)
"""

from __future__ import annotations

__all__ = [
    # Base exception
    "UnifiedQuantumError",
    # Authentication errors
    "AuthenticationError",
    # Credit/Quota errors
    "InsufficientCreditsError",
    "QuotaExceededError",
    # Network errors
    "NetworkError",
    # Task errors
    "TaskFailedError",
    "TaskTimeoutError",
    "TaskNotFoundError",
    # Backend errors
    "BackendError",
    "BackendNotAvailableError",
    "BackendNotFoundError",
    "BackendOptionsError",
    # Circuit errors
    "CircuitError",
    "CircuitTranslationError",
    "UnsupportedGateError",
    "NotSupportedGateError",
    "RegisterNotFoundError",
    "RegisterOutOfRangeError",
    "RegisterDefinitionError",
    "NotMatrixableError",
    "TimelineDurationError",
    # Compilation errors
    "CompilationFailedError",
    # Config errors
    "ConfigError",
    "ConfigValidationError",
    "PlatformNotFoundError",
    "ProfileNotFoundError",
    # Simulator errors
    "TopologyError",
    # Calibration errors
    "StaleCalibrationError",
    # Dependency errors
    "MissingDependencyError",
]


class UnifiedQuantumError(Exception):
    """Base exception for all UnifiedQuantum errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


# -----------------------------------------------------------------------------
# Authentication Errors
# -----------------------------------------------------------------------------

class AuthenticationError(UnifiedQuantumError):
    """Raised when authentication fails (invalid token, expired credentials, etc.).

    This error indicates that the provided API token or credentials are invalid,
    expired, or do not have the required permissions.
    """
    pass


# -----------------------------------------------------------------------------
# Credit and Quota Errors
# -----------------------------------------------------------------------------

class InsufficientCreditsError(UnifiedQuantumError):
    """Raised when the account has insufficient credits to run a task.

    This error indicates that the user's account balance is too low to
    execute the requested quantum computation.
    """
    pass


class QuotaExceededError(UnifiedQuantumError):
    """Raised when the user has exceeded their usage quota.

    This error indicates that the user has reached their daily, monthly,
    or total usage limit for the quantum computing service.
    """
    pass


# -----------------------------------------------------------------------------
# Network Errors
# -----------------------------------------------------------------------------

class NetworkError(UnifiedQuantumError):
    """Raised when a network operation fails.

    This error covers connection failures, timeouts, DNS errors,
    and other network-related issues when communicating with
    quantum computing backends.
    """

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.url = url
        self.status_code = status_code


# -----------------------------------------------------------------------------
# Task Errors
# -----------------------------------------------------------------------------

class TaskFailedError(UnifiedQuantumError):
    """Raised when a quantum task fails on the backend.

    This error indicates that the task was submitted successfully but
    failed during execution on the quantum computer or simulator.
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        backend: str | None = None,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.task_id = task_id
        self.backend = backend
        self.error_code = error_code


class TaskTimeoutError(UnifiedQuantumError):
    """Raised when waiting for a task result exceeds the timeout.

    This error indicates that the task did not complete within the
    specified timeout period. The task may still be running.
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        timeout: float | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.task_id = task_id
        self.timeout = timeout


class TaskNotFoundError(UnifiedQuantumError):
    """Raised when a task cannot be found.

    This error indicates that the specified task ID does not exist
    or the user does not have permission to access it.
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.task_id = task_id


# -----------------------------------------------------------------------------
# Backend Errors
# -----------------------------------------------------------------------------

class BackendError(UnifiedQuantumError):
    """Raised when a backend operation fails.

    This is the base class for all backend-related errors.
    """
    pass


class BackendNotAvailableError(BackendError):
    """Raised when a backend is not available.

    This error indicates that the backend is offline, not configured,
    or cannot be accessed due to missing dependencies.
    """
    pass


class BackendNotFoundError(BackendError):
    """Raised when a requested backend is not found.

    This error indicates that the specified backend name is not
    registered in the backend registry.
    """
    pass


class BackendOptionsError(UnifiedQuantumError, ValueError):
    """Raised when :class:`BackendOptions` construction, validation, or normalisation fails."""
    pass


# -----------------------------------------------------------------------------
# Circuit Errors
# -----------------------------------------------------------------------------

class CircuitError(UnifiedQuantumError):
    """Base class for all circuit-related errors."""
    pass


class CircuitTranslationError(CircuitError):
    """Raised when circuit translation or IR conversion fails.

    This covers failures converting between OriginIR, OpenQASM 2, and
    other intermediate representations.
    """

    def __init__(
        self,
        message: str,
        *,
        source_format: str | None = None,
        target_format: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.source_format = source_format
        self.target_format = target_format


class UnsupportedGateError(CircuitError):
    """Raised when a circuit contains an unsupported gate.

    This error indicates that the target backend does not support
    one or more gates present in the circuit.
    """

    def __init__(
        self,
        message: str,
        *,
        gate_name: str | None = None,
        backend: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.gate_name = gate_name
        self.backend = backend


class NotSupportedGateError(CircuitError):
    """Raised when an unsupported gate is encountered in OpenQASM 2."""
    pass


class RegisterNotFoundError(CircuitError):
    """Raised when a quantum or classical register is not found."""
    pass


class RegisterOutOfRangeError(CircuitError):
    """Raised when a register index exceeds its defined size."""
    pass


class RegisterDefinitionError(CircuitError):
    """Raised when a register definition is invalid (e.g., duplicate name, empty)."""
    pass


class NotMatrixableError(CircuitError):
    """Raised when a circuit or gate has no unitary matrix representation."""
    pass


class TimelineDurationError(CircuitError):
    """Raised when a logical circuit cannot be scheduled without gate durations."""
    pass


# -----------------------------------------------------------------------------
# Compilation Errors
# -----------------------------------------------------------------------------

class CompilationFailedError(UnifiedQuantumError):
    """Raised when quantum circuit compilation fails."""
    pass


# -----------------------------------------------------------------------------
# Config Errors
# -----------------------------------------------------------------------------

class ConfigError(UnifiedQuantumError):
    """Base exception for configuration-related errors."""
    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""
    pass


class PlatformNotFoundError(ConfigError):
    """Raised when an unsupported platform is referenced."""
    pass


class ProfileNotFoundError(ConfigError):
    """Raised when a configuration profile is not found."""
    pass


# -----------------------------------------------------------------------------
# Simulator Errors
# -----------------------------------------------------------------------------

class TopologyError(UnifiedQuantumError):
    """Raised when an invalid qubit or topology is used."""
    pass


# -----------------------------------------------------------------------------
# Calibration Errors
# -----------------------------------------------------------------------------

class StaleCalibrationError(UnifiedQuantumError):
    """Raised when calibration data exceeds the allowed age (TTL)."""
    pass


# -----------------------------------------------------------------------------
# Dependency Errors
# -----------------------------------------------------------------------------

class MissingDependencyError(UnifiedQuantumError, ImportError):
    """Raised when an optional dependency is not installed.

    Inherits from both :class:`UnifiedQuantumError` and :class:`ImportError`
    so that it can be caught by either.

    Attributes:
        package: The name of the missing package.
        extra: The pip extras name to install the package, if applicable.
        install_hint: An explicit install or recovery hint, if applicable.
    """

    def __init__(self, package: str, extra: str | None = None, install_hint: str | None = None) -> None:
        self.package = package
        self.extra = extra
        self.install_hint = install_hint
        if install_hint is not None:
            msg = f"Package '{package}' is required for this feature. {install_hint}"
        elif extra is not None:
            msg = (
                f"Package '{package}' is required for this feature. "
                f"Install it with: pip install unified-quantum[{extra}]"
            )
        else:
            msg = f"Package '{package}' is required for this feature."
        super().__init__(msg)
