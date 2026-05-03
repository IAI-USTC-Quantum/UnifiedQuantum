"""Unified configuration management for task backends.

Cloud API tokens are loaded from the shared ``~/.uniqc/config.yaml`` file
written by ``uniqc config set``. The active profile is selected by
``active_profile`` in that file, with ``UNIQC_PROFILE`` supported only as a
profile selector.
"""

from __future__ import annotations

__all__ = [
    "load_originq_config",
    "load_quafu_config",
    "load_quark_config",
    "load_ibm_config",
    "load_dummy_config",
]

from typing import Any


def _load_platform_config(platform: str) -> dict[str, Any]:
    """Load ``platform`` config from the active YAML profile.

    Args:
        platform: One of ``originq``, ``quafu``, ``quark``, ``ibm``.

    Returns:
        Platform configuration dictionary.
    """
    try:
        from uniqc.backend_adapter.config import get_active_profile, get_platform_config

        profile = get_active_profile()
        return get_platform_config(platform, profile)
    except Exception as exc:
        raise ImportError(
            f"{platform} config not found. "
            f"Run `uniqc config set {platform}.token <TOKEN>` or edit ~/.uniqc/config.yaml."
        ) from exc


# ---------------------------------------------------------------------------
# OriginQ Cloud
# ---------------------------------------------------------------------------

def load_originq_config() -> dict[str, Any]:
    """Load OriginQ Cloud configuration from the active YAML profile.

    Returns:
        dict with keys: api_key, task_group_size, available_qubits

    Raises:
        ImportError: If required configuration is not found.
    """
    config = _load_platform_config("originq")
    api_key = config.get("token", "") or None

    if api_key:
        return {
            "api_key": api_key,
            "task_group_size": int(config.get("task_group_size", 200) or 200),
            "available_qubits": config.get("available_qubits", []),
        }

    raise ImportError(
        "OriginQ Cloud config not found. "
        "Run `uniqc config set originq.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


# ---------------------------------------------------------------------------
# Quafu
# ---------------------------------------------------------------------------

def load_quafu_config() -> dict[str, Any]:
    """Load Quafu configuration from the active YAML profile.

    Returns:
        dict with key: api_token

    Raises:
        ImportError: If the configuration is not found.
    """
    config = _load_platform_config("quafu")
    api_token = config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "Quafu config not found. "
        "Run `uniqc config set quafu.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


# ---------------------------------------------------------------------------
# QuarkStudio / Quafu-SQC
# ---------------------------------------------------------------------------

def load_quark_config() -> dict[str, Any]:
    """Load QuarkStudio configuration from the active YAML profile.

    Returns:
        dict with key: api_token

    Raises:
        ImportError: If the configuration is not found.
    """
    config = _load_platform_config("quark")
    api_token = config.get("QUARK_API_KEY", "") or config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "QuarkStudio config not found. "
        "Run `uniqc config set quark.QUARK_API_KEY <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


# ---------------------------------------------------------------------------
# IBM Quantum
# ---------------------------------------------------------------------------

def load_ibm_config() -> dict[str, Any]:
    """Load IBM Quantum configuration from the active YAML profile.

    Returns:
        dict with key: api_token

    Raises:
        ImportError: If the configuration is not found.
    """
    config = _load_platform_config("ibm")
    api_token = config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "IBM Quantum config not found. "
        "Run `uniqc config set ibm.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


# ---------------------------------------------------------------------------
# OriginQ Dummy (local simulation)
# ---------------------------------------------------------------------------

def load_dummy_config() -> dict[str, Any]:
    """Load OriginQ Dummy simulation configuration from the active YAML profile.

    Returns:
        dict with keys: available_qubits, available_topology, task_group_size
    """
    try:
        config = _load_platform_config("originq")
    except ImportError:
        config = {}

    return {
        "available_qubits": config.get("available_qubits", []),
        "available_topology": config.get("available_topology", []),
        "task_group_size": int(config.get("task_group_size", 200) or 200),
    }
