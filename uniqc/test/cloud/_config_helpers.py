"""Helpers for cloud tests that use the public uniqc YAML config."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def platform_has_token(platform: str) -> bool:
    """Return True when the active YAML profile has a non-empty platform token."""
    try:
        from uniqc.backend_adapter.config import get_active_profile, get_platform_config

        profile = get_active_profile()
        config = get_platform_config(platform, profile)
        return bool(config.get("token"))
    except Exception:
        return False


def write_uniqc_config(home: Path, platforms: dict[str, dict[str, Any]], *, active_profile: str = "default") -> Path:
    """Write a temporary ``~/.uniqc/config.yaml`` style config for tests."""
    from uniqc.backend_adapter.config import save_config

    config_file = home / ".uniqc" / "config.yaml"
    save_config({"active_profile": active_profile, active_profile: platforms}, config_file)
    return config_file
