"""Central registry for error documentation links and troubleshooting hints.

This module provides a single source of truth for enriching error messages
with links to the relevant API documentation, possible error causes, and
actionable troubleshooting steps.

Usage::

    from uniqc._error_hints import format_enriched_message

    # Enrich an error message before raising
    msg = format_enriched_message("Invalid token", "auth")
    raise ValueError(msg)
"""

from __future__ import annotations

__all__ = [
    "DOCS_BASE_URL",
    "GITHUB_URL",
    "HINTS",
    "format_enriched_message",
    "get_hint",
]

DOCS_BASE_URL = "https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/"
GITHUB_URL = "https://github.com/IAI-USTC-Quantum/UnifiedQuantum"

HINTS: dict[str, dict[str, list[str] | str]] = {
    "auth": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Invalid or expired API token",
            "Token lacks required permissions",
            "Token not configured in ~/.uniqc/config.yaml",
        ],
        "troubleshooting": [
            "Run: uniqc config validate",
            "Set token: uniqc config set originq.token <YOUR_TOKEN>",
            "Token URLs: OriginQ: q.本源量子.com | Quafu: quafu.baike.scut.cn | IBM: quantum.ibm.com",
        ],
    },
    "backend_not_found": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Backend name misspelled or incorrect case",
            "Backend not registered in the backend registry",
            "Backend list cache is stale",
        ],
        "troubleshooting": [
            "Run: uniqc backend list --platform <PLATFORM> to see available backends",
            "Run: uniqc backend update to refresh the backend cache",
            "Backend names are case-sensitive (e.g. 'originq', not 'OriginQ')",
        ],
    },
    "config": {
        "doc_url": "cli.html#uniqc-config",
        "causes": [
            "Missing or malformed config file",
            "Invalid YAML syntax in ~/.uniqc/config.yaml",
            "Platform name not recognized",
            "Profile not found in configuration",
        ],
        "troubleshooting": [
            "Run: uniqc config init to create a default config",
            "Run: uniqc config validate to check your configuration",
            "Config file location: ~/.uniqc/config.yaml",
            "Supported platforms: originq, quafu, quark, ibm",
        ],
    },
    "task_submission": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Circuit incompatible with target backend",
            "Backend service temporarily unavailable",
            "Task ID does not exist or is inaccessible",
            "Task execution exceeded the timeout period",
        ],
        "troubleshooting": [
            "Run a dry-run first: submit_task(circuit, ..., dummy=True)",
            "Check task status: uniqc task list",
            "Get task result: uniqc result <TASK_ID>",
            "Increase timeout: wait_for_result(task_id, timeout=600)",
        ],
    },
    "credits_quota": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Account balance too low to execute the task",
            "Daily or monthly usage quota has been exceeded",
            "Rate limit hit due to too many requests",
        ],
        "troubleshooting": [
            "Top up your account on the platform's web portal",
            "Wait and retry if rate-limited",
            "Use dummy mode for testing: backend='dummy'",
        ],
    },
    "network": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "No internet connection",
            "DNS resolution failure",
            "Backend service is down or unreachable",
            "Proxy misconfigured (especially for IBM Quantum)",
        ],
        "troubleshooting": [
            "Check your internet connection",
            "For IBM proxy: uniqc config set ibm.proxy.https http://127.0.0.1:7890",
            "Run: uniqc config validate",
            "Check proxy env vars: HTTP_PROXY, HTTPS_PROXY",
        ],
    },
    "compilation": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Circuit contains gates unsupported by the target backend",
            "Qiskit dependencies not installed",
            "No topology information available for routing",
            "Failed to convert between circuit formats (OriginIR / QASM)",
        ],
        "troubleshooting": [
            "Install Qiskit: pip install unified-quantum[qiskit]",
            "Provide backend_info or chip_characterization for topology",
            "Check supported gates for your target backend",
            "Use compile_to_basis=True when scheduling timelines",
        ],
    },
    "circuit_validation": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Invalid parameter values (negative, zero, out of range)",
            "Qubit index out of range for the circuit",
            "Incorrect number of parameters for a variational circuit",
            "Gate requires more qubits than available",
        ],
        "troubleshooting": [
            "Check qubit indices are within 0..(n_qubits-1)",
            "Verify parameter values are numeric and within valid ranges",
            "Ensure parameter count matches n_qubits * n_layers for variational circuits",
            "See: https://iai-ustc-quantum.github.io/UnifiedQuantum/docs/source/uniqc_api.html",
        ],
    },
    "measurement": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "shots is not a positive integer",
            "Qubit indices out of range",
            "Invalid measurement basis (must be I/X/Y/Z)",
            "Pauli string length mismatch with qubit count",
        ],
        "troubleshooting": [
            "Ensure shots is a positive integer (e.g. 1024)",
            "Check qubit indices are within circuit range",
            "Supported bases: I, X, Y, Z",
            "Pauli string length must match the number of qubits",
        ],
    },
    "calibration": {
        "doc_url": "source/cli/calibrate.html",
        "causes": [
            "Calibration data is stale or missing",
            "No calibration cache for the specified backend/qubit",
            "Calibration data exceeds the maximum allowed age",
        ],
        "troubleshooting": [
            "Run: uniqc calibrate readout --backend <BACKEND> --qubits <QUBITS>",
            "Run: uniqc calibrate xeb --backend <BACKEND> --type 1q --qubits <QUBITS>",
            "Check cache: ~/.uniqc/calibration_cache/",
            "Use --update to force re-fetch calibration data",
        ],
    },
    "visualization": {
        "doc_url": "source/uniqc_api.html",
        "causes": [
            "Gate duration not specified for timeline visualization",
            "Circuit not compiled to basis gates before scheduling",
            "Unsupported gate in the circuit for timeline generation",
        ],
        "troubleshooting": [
            "Provide gate_durations parameter for timeline visualization",
            "Use compile_to_basis=True when calling schedule_circuit",
            "Compile the circuit first: compile(circuit, backend_info=info)",
        ],
    },
}


def get_hint(hint_key: str) -> dict | None:
    """Look up a hint entry by key."""
    return HINTS.get(hint_key)


def format_enriched_message(message: str, hint_key: str) -> str:
    """Append doc link, causes, and troubleshooting to an error message."""
    hint = get_hint(hint_key)
    if hint is None:
        return message

    parts: list[str] = []
    if message:
        parts.append(message)

    doc_url = hint.get("doc_url", "")
    if doc_url:
        full_url = f"{DOCS_BASE_URL}{doc_url}"
        parts.append(f"\nDocs: {full_url}")

    causes = hint.get("causes", [])
    if causes:
        parts.append("\nPossible causes:")
        for cause in causes:
            parts.append(f"  - {cause}")

    troubleshooting = hint.get("troubleshooting", [])
    if troubleshooting:
        parts.append("\nTroubleshooting:")
        for step in troubleshooting:
            parts.append(f"  - {step}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Exception-type-to-hint-key mapping (used by UnifiedQuantumError.__str__)
# ---------------------------------------------------------------------------
_EXCEPTION_TYPE_HINTS_CACHE: dict[type, str] | None = None


def _get_exception_type_hints() -> dict[type, str]:
    """Return the exception-type-to-hint-key mapping, building it lazily."""
    global _EXCEPTION_TYPE_HINTS_CACHE
    if _EXCEPTION_TYPE_HINTS_CACHE is not None:
        return _EXCEPTION_TYPE_HINTS_CACHE

    from uniqc.exceptions import (
        AuthenticationError,
        BackendError,
        BackendNotAvailableError,
        BackendNotFoundError,
        CircuitError,
        CircuitTranslationError,
        InsufficientCreditsError,
        NetworkError,
        QuotaExceededError,
        TaskFailedError,
        TaskNotFoundError,
        TaskTimeoutError,
        UnsupportedGateError,
    )

    _EXCEPTION_TYPE_HINTS_CACHE = {
        AuthenticationError: "auth",
        InsufficientCreditsError: "credits_quota",
        QuotaExceededError: "credits_quota",
        NetworkError: "network",
        TaskFailedError: "task_submission",
        TaskTimeoutError: "task_submission",
        TaskNotFoundError: "task_submission",
        BackendError: "backend_not_found",
        BackendNotAvailableError: "backend_not_found",
        BackendNotFoundError: "backend_not_found",
        CircuitError: "circuit_validation",
        CircuitTranslationError: "compilation",
        UnsupportedGateError: "compilation",
    }
    return _EXCEPTION_TYPE_HINTS_CACHE


def get_hint_key_for_exception(exc_type: type) -> str | None:
    """Look up the default hint key for an exception type."""
    return _get_exception_type_hints().get(exc_type)
