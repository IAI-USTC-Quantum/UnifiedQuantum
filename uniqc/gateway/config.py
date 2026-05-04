"""Gateway server configuration — reads gateway.port/host from config.yaml."""

from __future__ import annotations

from typing import Any

from uniqc import config as _base_config

# Gateway-specific default values
DEFAULT_GATEWAY_PORT = 18765
DEFAULT_GATEWAY_HOST = "127.0.0.1"


def load_gateway_config() -> dict[str, Any]:
    """Load the [gateway] section from ~/.uniqc/config.yaml.

    If the key is absent the defaults apply:
        port: 18765
        host: 127.0.0.1  (localhost-only for security)
    """
    cfg = _base_config.load_config()
    gateway_cfg = cfg.get("gateway", {})
    return {
        "port": gateway_cfg.get("port", DEFAULT_GATEWAY_PORT),
        "host": gateway_cfg.get("host", DEFAULT_GATEWAY_HOST),
    }


def save_gateway_config(*, port: int | None = None, host: str | None = None) -> None:
    """Persist gateway settings into config.yaml, preserving all other keys."""
    cfg = _base_config.load_config()
    if "gateway" not in cfg:
        cfg["gateway"] = {}
    if port is not None:
        cfg["gateway"]["port"] = port
    if host is not None:
        cfg["gateway"]["host"] = host
    _base_config.save_config(cfg)
