"""Project-wide configuration and platform credentials helpers.

This module intentionally exposes the top-level API used by CLI and adapters:

- Shared project config APIs (`load_config`, `save_config`, `get_platform_config`, ...)
- Platform credential loaders used by cloud adapters (`load_originq_config`, ...)

All credentials and cache settings are persisted in ``~/.uniqc/config.yaml``.
"""

from typing import Any

from uniqc.backend_adapter.config import *  # noqa: F401,F403


def _load_platform_config(platform: str) -> dict[str, Any]:
    """Load ``platform`` config from the active YAML profile."""

    profile = get_active_profile()
    return get_platform_config(platform, profile)


def load_originq_config() -> dict[str, Any]:
    """Load OriginQ Cloud configuration from the active YAML profile."""
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


def load_quafu_config() -> dict[str, Any]:
    """Load Quafu configuration from the active YAML profile."""
    config = _load_platform_config("quafu")
    api_token = config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "Quafu config not found. "
        "Run `uniqc config set quafu.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


def load_quark_config() -> dict[str, Any]:
    """Load QuarkStudio configuration from the active YAML profile."""
    config = _load_platform_config("quark")
    api_token = config.get("QUARK_API_KEY", "") or config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "QuarkStudio config not found. "
        "Run `uniqc config set quark.QUARK_API_KEY <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


def load_ibm_config() -> dict[str, Any]:
    """Load IBM Quantum configuration from the active YAML profile."""
    config = _load_platform_config("ibm")
    api_token = config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "IBM Quantum config not found. "
        "Run `uniqc config set ibm.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


def load_dummy_config() -> dict[str, Any]:
    """Load OriginQ dummy execution config from the active YAML profile."""
    try:
        config = _load_platform_config("originq")
    except Exception:
        config = {}

    return {
        "available_qubits": config.get("available_qubits", []),
        "available_topology": config.get("available_topology", []),
        "task_group_size": int(config.get("task_group_size", 200) or 200),
    }
