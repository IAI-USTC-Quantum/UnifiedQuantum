"""Unified configuration management for task backends.

Configuration is read from environment variables, with a fallback to the
shared ``~/.uniqc/uniqc.yml`` configuration file (written by ``uniqc config set``).

Environment variables
---------------------
OriginQ Cloud:
    ORIGINQ_API_KEY        : API authentication token (required)
    ORIGINQ_TASK_GROUP_SIZE: Max circuits per submission (default: 200)

Quafu:
    QUAFU_API_TOKEN       : Quafu API token (required)

IBM:
    IBM_TOKEN             : IBM Quantum API token (required)

OriginQ Dummy (local simulation):
    ORIGINQ_AVAILABLE_QUBITS   : JSON list of available qubit indices
    ORIGINQ_AVAILABLE_TOPOLOGY: JSON list of [u, v] edge pairs
    ORIGINQ_TASK_GROUP_SIZE    : Max circuits per group (default: 200)

"""

from __future__ import annotations

__all__ = ["load_originq_config", "load_quafu_config", "load_ibm_config", "load_dummy_config"]

import json
import os
from typing import Any


def _load_token_from_yaml(platform: str) -> str | None:
    """Load token for ``platform`` from the shared YAML config file.

    Args:
        platform: One of ``originq``, ``quafu``, ``ibm``.

    Returns:
        Token string, or ``None`` if not found or config file is absent.
    """
    try:
        from uniqc.config import get_active_profile, get_platform_config

        profile = get_active_profile()
        plat_cfg = get_platform_config(platform, profile)
        return plat_cfg.get("token", "") or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# OriginQ Cloud
# ---------------------------------------------------------------------------

def load_originq_config() -> dict[str, Any]:
    """Load OriginQ Cloud configuration from environment variables or YAML config.

    The YAML config is checked as a fallback when ``ORIGINQ_API_KEY`` is not set.
    This allows ``uniqc config set`` to configure both the CLI and Python API.

    Returns:
        dict with keys: api_key, task_group_size, available_qubits

    Raises:
        ImportError: If required configuration is not found.
    """
    api_key = os.getenv("ORIGINQ_API_KEY")
    task_group_size_str = os.getenv("ORIGINQ_TASK_GROUP_SIZE")

    if not api_key:
        api_key = _load_token_from_yaml("originq")

    if api_key:
        return {
            "api_key": api_key,
            "task_group_size": int(task_group_size_str) if task_group_size_str else 200,
            "available_qubits": [],
        }

    raise ImportError(
        "OriginQ Cloud config not found. "
        "Set ORIGINQ_API_KEY environment variable, "
        "or add your token to ~/.uniqc/uniqc.yml under the active profile."
    )


# ---------------------------------------------------------------------------
# Quafu
# ---------------------------------------------------------------------------

def load_quafu_config() -> dict[str, Any]:
    """Load Quafu configuration from environment variables or YAML config.

    The YAML config is checked as a fallback when ``QUAFU_API_TOKEN`` is not set.

    Returns:
        dict with key: api_token

    Raises:
        ImportError: If the configuration is not found.
    """
    api_token = os.getenv("QUAFU_API_TOKEN")

    if not api_token:
        api_token = _load_token_from_yaml("quafu")

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "Quafu config not found. "
        "Set QUAFU_API_TOKEN environment variable, "
        "or add your token to ~/.uniqc/uniqc.yml under the active profile."
    )


# ---------------------------------------------------------------------------
# IBM Quantum
# ---------------------------------------------------------------------------

def load_ibm_config() -> dict[str, Any]:
    """Load IBM Quantum configuration from environment variables or YAML config.

    The YAML config is checked as a fallback when ``IBM_TOKEN`` is not set.

    Returns:
        dict with key: api_token

    Raises:
        ImportError: If the configuration is not found.
    """
    api_token = os.getenv("IBM_TOKEN")

    if not api_token:
        api_token = _load_token_from_yaml("ibm")

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "IBM Quantum config not found. "
        "Set IBM_TOKEN environment variable, "
        "or add your token to ~/.uniqc/uniqc.yml under the active profile."
    )


# ---------------------------------------------------------------------------
# OriginQ Dummy (local simulation)
# ---------------------------------------------------------------------------

def load_dummy_config() -> dict[str, Any]:
    """Load OriginQ Dummy simulation configuration from environment variables.

    Returns:
        dict with keys: available_qubits, available_topology, task_group_size
    """
    qubits_str = os.getenv("ORIGINQ_AVAILABLE_QUBITS")
    topology_str = os.getenv("ORIGINQ_AVAILABLE_TOPOLOGY")
    group_size_str = os.getenv("ORIGINQ_TASK_GROUP_SIZE")

    available_qubits: list[int] = []
    available_topology: list[list[int]] = []

    if qubits_str:
        available_qubits = json.loads(qubits_str)
    if topology_str:
        available_topology = json.loads(topology_str)

    if available_qubits or available_topology:
        return {
            "available_qubits": available_qubits,
            "available_topology": available_topology,
            "task_group_size": int(group_size_str) if group_size_str else 200,
        }

    # No config — use empty defaults (dummy works without chip info)
    return {
        "available_qubits": [],
        "available_topology": [],
        "task_group_size": 200,
    }
