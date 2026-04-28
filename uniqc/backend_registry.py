"""Backend registry: fetches, normalises, and caches platform backends.

This module is the central orchestrator for the ``uniqc backend`` command.
It:
1. Calls each platform's ``list_backends()`` adapter method (or cache).
2. Normalises the raw platform data into ``BackendInfo`` objects.
3. Persists the normalised list to the disk cache.
4. Provides query helpers (``get_backend_info``, ``find_backend``).
"""

from __future__ import annotations

import logging
from typing import Any

from uniqc.backend_cache import get_cached_backends, update_cache
from uniqc.backend_info import BackendInfo, Platform, QubitTopology
from uniqc.exceptions import BackendError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simulators that appear in OriginQ's backend list but carry no qubits.
# ---------------------------------------------------------------------------
_ORIGINQ_SIMULATOR_NAMES = frozenset({
    "full_amplitude",
    "partial_amplitude",
    "single_amplitude",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_quafu_gates(gates: list[str]) -> list[str]:
    """Strip artefacts from Quafu's ``get_valid_gates()`` output.

    The quafu package returns gate names with literal ``[ "`` prefix and ``"``
    suffix characters embedded in the strings (e.g. ``'[ "cx"'``).  This
    function removes those artefacts.
    """
    cleaned: list[str] = []
    for g in gates:
        g = g.lstrip('[ "').rstrip('" ]')
        if g:
            cleaned.append(g)
    return cleaned


# ---------------------------------------------------------------------------
# Normalisers
# ---------------------------------------------------------------------------

def _normalise_originq(raw: list[dict[str, Any]]) -> list[BackendInfo]:
    """Convert OriginQ ``list_backends()`` output to ``BackendInfo`` objects."""
    results: list[BackendInfo] = []
    for entry in raw:
        name = entry.get("name", "")
        available: bool = entry.get("available", False)
        is_sim = name in _ORIGINQ_SIMULATOR_NAMES
        # chip_info() raises for simulators, so is_sim is reliable from the name list
        results.append(BackendInfo(
            platform=Platform.ORIGINQ,
            name=name,
            description="OriginQ Cloud simulator" if is_sim else "OriginQ Cloud chip",
            num_qubits=0,
            topology=(),
            status="available" if available else "unavailable",
            is_simulator=is_sim,
            is_hardware=not is_sim,
            extra={"available": available},
        ))
    return results


def _normalise_quafu(raw: list[dict[str, Any]]) -> list[BackendInfo]:
    """Convert Quafu ``list_backends()`` output to ``BackendInfo`` objects."""
    # Names that indicate a simulator rather than real hardware
    _QUAFU_SIM_PATTERNS = ("sim", "Sim", "SIM")
    results: list[BackendInfo] = []
    for entry in raw:
        name = entry.get("name", "")
        status_str: str = entry.get("status", "unknown")
        num_qubits: int = entry.get("num_qubits", 0)
        is_sim = any(p in name for p in _QUAFU_SIM_PATTERNS)
        # Map Quafu status to our canonical status
        status_map = {
            "Online": "available",
            "Offline": "unavailable",
            "Obsolete": "deprecated",
        }
        mapped_status = status_map.get(status_str, status_str)
        results.append(BackendInfo(
            platform=Platform.QUAFU,
            name=name,
            description=f"BAQIS Quafu {num_qubits}-qubit chip",
            num_qubits=num_qubits,
            topology=(),
            status=mapped_status,
            is_simulator=is_sim,
            is_hardware=not is_sim,
            extra={
                "task_in_queue": entry.get("task_in_queue", 0),
                "qv": entry.get("qv", 0),
                "valid_gates": _clean_quafu_gates(entry.get("valid_gates", [])),
            },
        ))
    return results


def _normalise_ibm(raw: list[dict[str, Any]]) -> list[BackendInfo]:
    """Convert IBM Quantum REST API output to ``BackendInfo`` objects."""
    results: list[BackendInfo] = []
    for entry in raw:
        name: str = entry.get("name", "")
        cfg: dict[str, Any] = entry.get("configuration", {})
        n_qubits: int = cfg.get("num_qubits", 0)
        is_sim: bool = entry.get("simulator", False)
        is_hardware = not is_sim
        status_str: str = entry.get("status", "unknown")
        # Map IBM status to our canonical
        status_map = {
            "online": "available",
            "offline": "unavailable",
            "maintenance": "maintenance",
            "deferred": "deprecated",
        }
        # Parse topology edges
        topology_edges: list[dict[str, int]] = cfg.get("coupling_map", [])
        topology = tuple(
            QubitTopology(u=int(e[0]), v=int(e[1])) for e in topology_edges
        )
        results.append(BackendInfo(
            platform=Platform.IBM,
            name=name,
            description=entry.get("description", ""),
            num_qubits=n_qubits,
            topology=topology,
            status=status_map.get(status_str.lower(), status_str),
            is_simulator=is_sim,
            is_hardware=is_hardware,
            extra={
                "max_shots": cfg.get("max_shots"),
                "basis_gates": cfg.get("basis_gates", []),
                "memory": cfg.get("memory", False),
                "qobd": cfg.get("qobd", False),
                "supported_instructions": cfg.get("supported_instructions", []),
            },
        ))
    return results


_NORMALISERS = {
    Platform.ORIGINQ: _normalise_originq,
    Platform.QUAFU: _normalise_quafu,
    Platform.IBM: _normalise_ibm,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _build_adapter(platform: Platform):
    """Instantiate the correct adapter for ``platform``."""
    # Sync YAML tokens → env vars so adapters that read from env work correctly.
    from uniqc.config import sync_tokens_to_env
    sync_tokens_to_env()
    if platform == Platform.ORIGINQ:
        from uniqc.task.adapters import OriginQAdapter
        return OriginQAdapter()
    elif platform == Platform.QUAFU:
        from uniqc.task.adapters import QuafuAdapter
        return QuafuAdapter()
    elif platform == Platform.IBM:
        from uniqc.task.adapters.ibm_adapter import IBMAdapter
        return IBMAdapter()
    raise ValueError(f"No adapter for platform {platform}")


def fetch_platform_backends(
    platform: Platform,
    force_refresh: bool = False,
) -> tuple[list[BackendInfo], bool]:
    """Fetch and normalise backends for one platform.

    Args:
        platform: The platform to fetch backends for.
        force_refresh: If True, bypass the cache TTL check.

    Returns:
        A tuple of (backends, fetched_newly) where fetched_newly is True
        if the data was fetched from the network (vs. served from cache).
    """
    from uniqc.backend_cache import is_stale  # noqa: PLC0415

    fetched_newly = False

    if not force_refresh and not is_stale(platform.value):
        backends = get_cached_backends(platform)
        if backends:
            return backends, False

    # Cache miss or forced refresh — call the platform API
    try:
        adapter = _build_adapter(platform)
        raw = adapter.list_backends()
        normaliser = _NORMALISERS[platform]
        backends = normaliser(raw)
        update_cache(platform, backends)
        fetched_newly = True
        logger.debug("Fetched %d %s backends from API", len(backends), platform.value)
    except BackendError:
        logger.warning("Platform %s not configured — skipping", platform.value)
        backends = []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch %s backends: %s", platform.value, exc)
        # Try to serve stale cache as a fallback
        backends = get_cached_backends(platform)
        if not backends:
            raise

    return backends, fetched_newly


def fetch_all_backends(
    force_refresh: bool = False,
) -> dict[Platform, list[BackendInfo]]:
    """Fetch backends from all configured platforms.

    Args:
        force_refresh: Bypass the cache TTL for all platforms.

    Returns:
        Dict mapping Platform to its list of BackendInfo objects.
        Platforms that fail are omitted with a warning.
    """
    results: dict[Platform, list[BackendInfo]] = {}
    for platform in Platform:
        try:
            backends, _ = fetch_platform_backends(platform, force_refresh=force_refresh)
            if backends:
                results[platform] = backends
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping %s: %s", platform.value, exc)
    return results


def find_backend(identifier: str) -> BackendInfo:
    """Find a backend by its identifier.

    Supports two forms:
        - ``platform:name``  (e.g. ``originq:HanYuan_01``)
        - bare ``name``      (searches all platforms)

    Args:
        identifier: Backend identifier.

    Returns:
        The matching BackendInfo object.

    Raises:
        ValueError: If the backend is not found or the identifier format
            is invalid.
    """
    from uniqc.backend_info import parse_backend_id

    try:
        platform, name = parse_backend_id(identifier)
        backends, _ = fetch_platform_backends(platform)
        for backend in backends:
            if backend.name == name:
                return backend
        available = ", ".join(b.name for b in backends) or "(none)"
        raise ValueError(
            f"Backend '{name}' not found on platform '{platform.value}'. "
            f"Available backends: {available}"
        )
    except ValueError:
        # Bare name — search all platforms
        for plat in Platform:
            try:
                backends, _ = fetch_platform_backends(plat)
            except Exception:  # noqa: BLE001
                continue
            for backend in backends:
                if backend.name == identifier:
                    return backend
        raise ValueError(
            f"Backend '{identifier}' not found on any platform. "
            f"Use 'uniqc backend list' to see available backends."
        ) from None
