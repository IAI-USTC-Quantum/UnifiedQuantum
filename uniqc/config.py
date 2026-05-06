"""Project-wide configuration and platform credentials helpers.

This module is the canonical source of truth for ``CONFIG_FILE`` and all
configuration management functions (``load_config``, ``save_config``,
``get_active_profile``, …).  ``uniqc.backend_adapter.config`` re-exports from here
so that patching ``uniqc.config.CONFIG_FILE`` propagates to every import path.

All credentials and cache settings are persisted in ``~/.uniqc/config.yaml``.

Example configuration structure::

    always_ai_hints: false
    active_profile: default
    default:
      originq:
        token: xxx
      quafu:
        token: xxx
      quark:
        QUARK_API_KEY: xxx
      ibm:
        token: xxx
        proxy:
          http: http://proxy:8080
          https: https://proxy:8080
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Top-level symbols (defined here so that uniqc.backend_adapter.config can
# import them and both modules reference the same objects after patching)
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".uniqc"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "always_ai_hints": False,
    "default": {
        "originq": {
            "token": "",
            "available_qubits": [],
            "available_topology": [],
            "task_group_size": 200,
        },
        "quafu": {
            "token": "",
        },
        "quark": {
            "QUARK_API_KEY": "",
        },
        "ibm": {
            "token": "",
            "proxy": {
                "http": "",
                "https": "",
            },
        },
    },
}

SUPPORTED_PLATFORMS = ["originq", "quafu", "quark", "ibm"]

META_KEYS = frozenset({"active_profile", "always_ai_hints"})

PLATFORM_REQUIRED_FIELDS = {
    "originq": ["token"],
    "quafu": ["token"],
    "quark": ["QUARK_API_KEY"],
    "ibm": ["token"],
}

PLATFORM_KNOWN_FIELDS = {
    "originq": {"token", "task_group_size", "available_qubits"},
    "quafu": {"token", "chip_id", "auto_mapping", "task_name", "group_name", "wait", "shots"},
    "quark": {"QUARK_API_KEY", "token"},
    "ibm": {"token", "proxy", "chip_id", "auto_mapping", "circuit_optimize", "task_name", "shots"},
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    pass


class ConfigValidationError(ConfigError):
    pass


class PlatformNotFoundError(ConfigError):
    pass


class ProfileNotFoundError(ConfigError):
    pass


# ---------------------------------------------------------------------------
# Core functions (also used by uniqc.backend_adapter.config via re-export)
# ---------------------------------------------------------------------------

def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else CONFIG_FILE

    if not path.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config is None:
            return DEFAULT_CONFIG.copy()
        return config
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}") from e
    except OSError as e:
        raise ConfigError(f"Failed to read configuration file: {e}") from e


def save_config(config: dict[str, Any], config_path: str | Path | None = None) -> None:
    path = Path(config_path) if config_path else CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
    except OSError as e:
        raise ConfigError(f"Failed to write configuration file: {e}") from e


def get_platform_config(
    platform_name: str,
    profile: str = "default",
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    if platform_name not in SUPPORTED_PLATFORMS:
        raise PlatformNotFoundError(
            f"Unsupported platform: {platform_name}. "
            f"Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}"
        )

    config = load_config(config_path)

    if profile not in config:
        raise ProfileNotFoundError(
            f"Profile '{profile}' not found in configuration. "
            f"Available profiles: {', '.join(config.keys())}"
        )

    profile_config = config[profile]

    if platform_name not in profile_config:
        raise ConfigError(
            f"Platform '{platform_name}' not found in profile '{profile}'"
        )

    return profile_config[platform_name]


def validate_config(
    config: dict[str, Any] | None = None,
    config_path: str | Path | None = None,
) -> list[str]:
    errors: list[str] = []

    try:
        cfg = config if config is not None else load_config(config_path)
    except ConfigError as e:
        return [str(e)]

    if not isinstance(cfg, dict):
        return ["Configuration must be a dictionary"]

    if not cfg:
        return ["Configuration is empty"]

    for profile_name, profile_config in cfg.items():
        if profile_name in META_KEYS:
            continue
        if not isinstance(profile_config, dict):
            errors.append(f"Profile '{profile_name}' must be a dictionary")
            continue

        for platform_name in SUPPORTED_PLATFORMS:
            if platform_name not in profile_config:
                continue

            platform_config = profile_config[platform_name]

            if not isinstance(platform_config, dict):
                errors.append(
                    f"Platform '{platform_name}' in profile '{profile_name}' "
                    "must be a dictionary"
                )
                continue

            if platform_name == "quark":
                if "QUARK_API_KEY" not in platform_config and "token" not in platform_config:
                    errors.append(
                        "Missing required field 'QUARK_API_KEY' for platform "
                        f"'{platform_name}' in profile '{profile_name}'"
                    )
            else:
                required_fields = PLATFORM_REQUIRED_FIELDS.get(platform_name, [])
                for field in required_fields:
                    if field not in platform_config:
                        errors.append(
                            f"Missing required field '{field}' for platform "
                            f"'{platform_name}' in profile '{profile_name}'"
                        )

            # Warn about unknown keys (likely typos)
            known = PLATFORM_KNOWN_FIELDS.get(platform_name, set())
            unknown = set(platform_config.keys()) - known
            for key in sorted(unknown):
                errors.append(
                    f"Warning: unknown field '{key}' for platform "
                    f"'{platform_name}' in profile '{profile_name}'"
                )

            if platform_name == "ibm" and "proxy" in platform_config:
                proxy = platform_config["proxy"]
                if not isinstance(proxy, dict):
                    errors.append(
                        f"Proxy configuration for IBM in profile '{profile_name}' "
                        "must be a dictionary"
                    )
                else:
                    for proxy_type in ["http", "https"]:
                        if proxy_type in proxy and not isinstance(proxy[proxy_type], str):
                            errors.append(
                                f"Proxy '{proxy_type}' for IBM in profile "
                                f"'{profile_name}' must be a string"
                            )

    return errors


def create_default_config(config_path: str | Path | None = None) -> None:
    path = Path(config_path) if config_path else CONFIG_FILE
    if path.exists():
        return
    _ensure_config_dir()
    save_config(DEFAULT_CONFIG, path)


def update_platform_config(
    platform_name: str,
    platform_config: dict[str, Any],
    profile: str = "default",
    config_path: str | Path | None = None,
) -> None:
    if platform_name not in SUPPORTED_PLATFORMS:
        raise PlatformNotFoundError(
            f"Unsupported platform: {platform_name}. "
            f"Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}"
        )

    config = load_config(config_path)

    if profile not in config:
        config[profile] = {}

    config[profile][platform_name] = platform_config
    save_config(config, config_path)


def get_active_profile(config_path: str | Path | None = None) -> str:
    env_profile = os.environ.get("UNIQC_PROFILE")
    if env_profile:
        return env_profile

    config = load_config(config_path)
    if "active_profile" in config:
        return config["active_profile"]

    return "default"


def set_active_profile(
    profile: str,
    config_path: str | Path | None = None,
) -> None:
    config = load_config(config_path)

    if profile not in config:
        raise ProfileNotFoundError(
            f"Profile '{profile}' not found in configuration. "
            f"Available profiles: {', '.join(k for k in config if k not in META_KEYS)}"
        )

    config["active_profile"] = profile
    save_config(config, config_path)


def get_always_ai_hints(config_path: str | Path | None = None) -> bool:
    config = load_config(config_path)
    return bool(config.get("always_ai_hints", False))


def set_always_ai_hints(
    enabled: bool,
    config_path: str | Path | None = None,
) -> None:
    config = load_config(config_path)
    config["always_ai_hints"] = bool(enabled)
    save_config(config, config_path)


def get_originq_config(profile: str | None = None) -> dict[str, Any]:
    if profile is None:
        profile = get_active_profile()
    return get_platform_config("originq", profile)


def get_quafu_config(profile: str | None = None) -> dict[str, Any]:
    if profile is None:
        profile = get_active_profile()
    return get_platform_config("quafu", profile)


def get_quark_config(profile: str | None = None) -> dict[str, Any]:
    if profile is None:
        profile = get_active_profile()
    return get_platform_config("quark", profile)


def get_ibm_config(profile: str | None = None) -> dict[str, Any]:
    if profile is None:
        profile = get_active_profile()
    return get_platform_config("ibm", profile)


# ---------------------------------------------------------------------------
# Platform-specific credential loaders
# ---------------------------------------------------------------------------

def _load_platform_config(platform: str) -> dict[str, Any]:
    profile = get_active_profile()
    return get_platform_config(platform, profile)


def load_originq_config() -> dict[str, Any]:
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
    config = _load_platform_config("quafu")
    api_token = config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "Quafu config not found. "
        "Run `uniqc config set quafu.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


def load_quark_config() -> dict[str, Any]:
    config = _load_platform_config("quark")
    api_token = config.get("QUARK_API_KEY", "") or config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "QuarkStudio config not found. "
        "Run `uniqc config set quark.QUARK_API_KEY <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


def load_ibm_config() -> dict[str, Any]:
    config = _load_platform_config("ibm")
    api_token = config.get("token", "") or None

    if api_token:
        return {"api_token": api_token}

    raise ImportError(
        "IBM Quantum config not found. "
        "Run `uniqc config set ibm.token <TOKEN>` or edit ~/.uniqc/config.yaml."
    )


def has_platform_credentials(platform: str) -> bool:
    """Check whether credentials exist for a platform without raising.

    Returns True if the platform section exists in the active profile
    and contains a non-empty token/key field.  Returns False otherwise
    (including when the config file does not exist or the platform is
    not configured at all).
    """
    try:
        config = _load_platform_config(platform)
    except (ConfigError, ProfileNotFoundError, PlatformNotFoundError):
        return False
    if platform == "quark":
        token = config.get("QUARK_API_KEY", "") or config.get("token", "")
    else:
        token = config.get("token", "")
    return bool(token)


def load_dummy_config() -> dict[str, Any]:
    try:
        config = _load_platform_config("originq")
    except Exception:
        config = {}

    return {
        "available_qubits": config.get("available_qubits", []),
        "available_topology": config.get("available_topology", []),
        "task_group_size": int(config.get("task_group_size", 200) or 200),
    }
