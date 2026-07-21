"""Gateway server configuration — reads gateway.port/host from config.yaml."""

from __future__ import annotations

import ipaddress
from typing import Any

from uniqc import config as _base_config

# Gateway-specific default values
DEFAULT_GATEWAY_PORT = 18765
DEFAULT_GATEWAY_HOST = "127.0.0.1"


def validate_loopback_host(host: str) -> str:
    """Return a normalized loopback host or raise ``ValueError``."""
    normalized = host.strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]

    if normalized.lower().rstrip(".") == "localhost":
        return "localhost"

    try:
        address = ipaddress.ip_address(normalized)
    except ValueError as exc:
        raise ValueError(f"Gateway host '{host}' is not allowed; use localhost or a loopback IP address.") from exc

    if not address.is_loopback:
        raise ValueError(f"Gateway host '{host}' is not allowed; use localhost or a loopback IP address.")
    return str(address)


def load_gateway_config(*, host_override: str | None = None) -> dict[str, Any]:
    """Load the [gateway] section from ~/.uniqc/config.yaml.

    If the key is absent the defaults apply:
        port: 18765
        host: 127.0.0.1  (localhost-only for security)
    """
    cfg = _base_config.load_config()
    gateway_cfg = cfg.get("gateway", {})
    host = host_override if host_override is not None else gateway_cfg.get("host", DEFAULT_GATEWAY_HOST)
    return {
        "port": gateway_cfg.get("port", DEFAULT_GATEWAY_PORT),
        "host": validate_loopback_host(str(host)),
    }


def save_gateway_config(*, port: int | None = None, host: str | None = None) -> None:
    """Persist gateway settings into config.yaml, preserving all other keys."""
    if host is not None:
        host = validate_loopback_host(host)
    cfg = _base_config.load_config()
    if "gateway" not in cfg:
        cfg["gateway"] = {}
    if port is not None:
        cfg["gateway"]["port"] = port
    if host is not None:
        cfg["gateway"]["host"] = host
    _base_config.save_config(cfg)
