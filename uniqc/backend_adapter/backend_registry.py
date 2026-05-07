"""Backend registry: fetches, normalises, and caches platform backends.

This module is the central orchestrator for the ``uniqc backend`` command.
It:
1. Calls each platform's ``list_backends()`` adapter method (or cache).
2. Normalises the raw platform data into ``BackendInfo`` objects.
3. Persists the normalised list to the disk cache.
4. Provides query helpers (``get_backend_info``, ``find_backend``).
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from typing import Any

from uniqc.backend_adapter.backend_cache import get_cached_backends, update_cache
from uniqc.backend_adapter.backend_info import ORIGINQ_SIMULATOR_NAMES, BackendInfo, Platform, QubitTopology
from uniqc.exceptions import BackendError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackendAuditIssue:
    """One backend metadata issue found by the registry audit."""

    backend_id: str
    severity: str
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Result of fetching backends from all platforms.

    Attributes
    ----------
    backends :
        Per-platform backend descriptors.
    fetch_failures :
        Platforms that had credentials but failed to fetch,
        mapped to the error message.
    """

    backends: dict[Platform, list[BackendInfo]]
    fetch_failures: dict[Platform, str] = dataclasses.field(default_factory=dict)


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


def _topology_from_raw(raw_edges: Any) -> tuple[QubitTopology, ...]:
    """Convert serialised ``[[u, v], ...]`` topology into BackendInfo edges."""
    topology: list[QubitTopology] = []
    if not isinstance(raw_edges, list):
        return ()
    for edge in raw_edges:
        try:
            u = int(edge[0])
            v = int(edge[1])
        except (IndexError, KeyError, TypeError, ValueError):
            continue
        if u == v:
            continue
        topology.append(QubitTopology(u=u, v=v))
    return tuple(topology)


# ---------------------------------------------------------------------------
# Normalisers
# ---------------------------------------------------------------------------


def _normalise_originq(raw: list[dict[str, Any]]) -> list[BackendInfo]:
    """Convert OriginQ ``list_backends()`` output to ``BackendInfo`` objects."""
    results: list[BackendInfo] = []
    for entry in raw:
        name = entry.get("name", "")
        available: bool = entry.get("available", False)
        is_sim = name in ORIGINQ_SIMULATOR_NAMES

        if is_sim:
            # Simulators: no chip_info
            num_qubits = 0
            topology: tuple[QubitTopology, ...] = ()
            extra: dict[str, Any] = {"available": available}
            results.append(
                BackendInfo(
                    platform=Platform.ORIGINQ,
                    name=name,
                    description="OriginQ Cloud simulator",
                    num_qubits=num_qubits,
                    topology=topology,
                    status="available" if available else "unavailable",
                    is_simulator=True,
                    is_hardware=False,
                    extra=extra,
                )
            )
        else:
            # Hardware: use chip_info fetched by the adapter
            num_qubits = entry.get("num_qubits", 0)
            topo_raw: list[list[int]] = entry.get("topology", [])
            topology = tuple(QubitTopology(u=e[0], v=e[1]) for e in topo_raw)
            avail_qubits: list[int] = entry.get("available_qubits", [])
            extra = {
                "available": available,
                "available_qubits": avail_qubits,
            }
            results.append(
                BackendInfo(
                    platform=Platform.ORIGINQ,
                    name=name,
                    description="OriginQ Cloud chip",
                    num_qubits=num_qubits,
                    topology=topology,
                    status="available" if available else "unavailable",
                    is_simulator=False,
                    is_hardware=True,
                    extra=extra,
                    avg_1q_fidelity=entry.get("avg_1q_fidelity"),
                    avg_2q_fidelity=entry.get("avg_2q_fidelity"),
                    avg_readout_fidelity=entry.get("avg_readout_fidelity"),
                    coherence_t1=entry.get("coherence_t1"),
                    coherence_t2=entry.get("coherence_t2"),
                )
            )
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
        topology = _topology_from_raw(entry.get("topology", []))
        results.append(
            BackendInfo(
                platform=Platform.QUAFU,
                name=name,
                description=f"BAQIS Quafu simulator" if is_sim else f"BAQIS Quafu chip",
                num_qubits=num_qubits,
                topology=topology,
                status=mapped_status,
                is_simulator=is_sim,
                is_hardware=not is_sim,
                extra={
                    "task_in_queue": entry.get("task_in_queue", 0),
                    "qv": entry.get("qv", 0),
                    "valid_gates": _clean_quafu_gates(entry.get("valid_gates", [])),
                    "available_qubits": entry.get("available_qubits", []),
                    "per_qubit_calibration": entry.get("per_qubit_calibration", []),
                    "per_pair_calibration": entry.get("per_pair_calibration", []),
                    "global_info": entry.get("global_info", {}),
                    "calibrated_at": entry.get("calibrated_at"),
                },
                avg_1q_fidelity=entry.get("avg_1q_fidelity"),
                avg_2q_fidelity=entry.get("avg_2q_fidelity"),
                avg_readout_fidelity=entry.get("avg_readout_fidelity"),
                coherence_t1=entry.get("coherence_t1"),
                coherence_t2=entry.get("coherence_t2"),
            )
        )
    return results


def _normalise_quark_status(value: Any) -> str:
    if isinstance(value, int):
        return "available"
    text = str(value or "").strip().lower()
    status_map = {
        "online": "available",
        "available": "available",
        "offline": "unavailable",
        "unavailable": "unavailable",
        "maintenance": "maintenance",
        "maintaining": "maintenance",
        "calibrating": "maintenance",
        "calibration": "maintenance",
    }
    return status_map.get(text, "unknown" if text else "unknown")


def _normalise_quark(raw: list[dict[str, Any]]) -> list[BackendInfo]:
    """Convert QuarkStudio ``Task.status()`` output to ``BackendInfo`` objects."""
    results: list[BackendInfo] = []
    for entry in raw:
        name = str(entry.get("name", ""))
        queue = entry.get("task_in_queue", 0)
        status = _normalise_quark_status(entry.get("status", queue))
        results.append(
            BackendInfo(
                platform=Platform.QUARK,
                name=name,
                description="QuarkStudio simulator" if "sim" in name.lower() else "QuarkStudio backend",
                num_qubits=int(entry.get("num_qubits", 0) or 0),
                topology=_topology_from_raw(entry.get("topology", [])),
                status=status,
                is_simulator="sim" in name.lower(),
                is_hardware="sim" not in name.lower(),
                extra={
                    "task_in_queue": queue,
                    "valid_gates": entry.get("valid_gates", []),
                    "available_qubits": entry.get("available_qubits", []),
                    "per_qubit_calibration": entry.get("per_qubit_calibration", []),
                    "per_pair_calibration": entry.get("per_pair_calibration", []),
                    "global_info": entry.get("global_info", {}),
                    "calibrated_at": entry.get("calibrated_at"),
                    "backend_info_available": entry.get("backend_info_available", False),
                },
                avg_1q_fidelity=entry.get("avg_1q_fidelity"),
                avg_2q_fidelity=entry.get("avg_2q_fidelity"),
                avg_readout_fidelity=entry.get("avg_readout_fidelity"),
                coherence_t1=entry.get("coherence_t1"),
                coherence_t2=entry.get("coherence_t2"),
            )
        )
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
        topology = tuple(QubitTopology(u=int(e[0]), v=int(e[1])) for e in topology_edges)
        results.append(
            BackendInfo(
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
                    "per_qubit_calibration": entry.get("per_qubit_calibration", []),
                    "per_pair_calibration": entry.get("per_pair_calibration", []),
                    "global_info": entry.get("global_info", {}),
                    "calibrated_at": entry.get("calibrated_at"),
                },
                avg_1q_fidelity=entry.get("avg_1q_fidelity"),
                avg_2q_fidelity=entry.get("avg_2q_fidelity"),
                avg_readout_fidelity=entry.get("avg_readout_fidelity"),
                coherence_t1=entry.get("coherence_t1"),
                coherence_t2=entry.get("coherence_t2"),
            )
        )
    return results


_NORMALISERS = {
    Platform.ORIGINQ: _normalise_originq,
    Platform.QUAFU: _normalise_quafu,
    Platform.QUARK: _normalise_quark,
    Platform.IBM: _normalise_ibm,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_adapter(platform: Platform):
    """Instantiate the correct adapter for ``platform``."""
    if platform == Platform.ORIGINQ:
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        return OriginQAdapter()
    elif platform == Platform.QUAFU:
        from uniqc.backend_adapter.task.adapters import QuafuAdapter

        return QuafuAdapter()
    elif platform == Platform.QUARK:
        from uniqc.backend_adapter.task.adapters import QuarkAdapter

        return QuarkAdapter()
    elif platform == Platform.IBM:
        from uniqc.backend_adapter.task.adapters.qiskit_adapter import QiskitAdapter

        return QiskitAdapter()
    elif platform == Platform.DUMMY:
        from uniqc.backend_adapter.task.adapters import DummyAdapter

        return DummyAdapter()
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

    Raises:
        BackendError: If the platform has credentials configured but the
            fetch fails (network error, API error, etc.) and no stale
            cache is available as fallback.
    """
    from uniqc.backend_adapter.backend_cache import is_stale  # noqa: PLC0415
    from uniqc.config import has_platform_credentials

    fetched_newly = False

    if platform == Platform.DUMMY:
        from uniqc.backend_adapter.dummy_backend import list_dummy_backend_infos

        backends = list_dummy_backend_infos()
        return backends, True

    # No credentials → skip silently (not an error)
    if not has_platform_credentials(platform.value):
        logger.debug("Platform %s has no credentials configured — skipping", platform.value)
        return [], False

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
    except (ImportError, ModuleNotFoundError):
        # SDK not installed — skip with warning
        logger.warning("Platform %s SDK not installed — skipping", platform.value)
        backends = []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch %s backends: %s", platform.value, exc)
        # Try to serve stale cache as a fallback
        backends = get_cached_backends(platform)
        if not backends:
            raise BackendError(
                f"Failed to fetch {platform.value} backends and no cached data available: {exc}"
            ) from exc

    return backends, fetched_newly


def fetch_all_backends(
    force_refresh: bool = False,
) -> dict[Platform, list[BackendInfo]]:
    """Fetch backends from all configured platforms.

    Args:
        force_refresh: Bypass the cache TTL for all platforms.

    Returns:
        Dict mapping Platform to its list of BackendInfo objects.
        Platforms with no credentials are silently omitted.
        Platforms with credentials but fetch failures are omitted
        with a warning.
    """
    return fetch_all_backends_with_status(force_refresh).backends


def fetch_all_backends_with_status(
    force_refresh: bool = False,
) -> FetchResult:
    """Fetch backends from all platforms, returning fetch failures too.

    Like :func:`fetch_all_backends` but also returns information about
    platforms that had credentials but failed to fetch, so callers can
    surface these as audit issues.
    """
    results: dict[Platform, list[BackendInfo]] = {}
    failures: dict[Platform, str] = {}
    for platform in Platform:
        try:
            backends, _ = fetch_platform_backends(platform, force_refresh=force_refresh)
            if backends:
                results[platform] = backends
        except BackendError as exc:
            logger.warning("Skipping %s: %s", platform.value, exc)
            failures[platform] = str(exc)
    return FetchResult(backends=results, fetch_failures=failures)


def audit_backend_info(backend: BackendInfo) -> list[BackendAuditIssue]:
    """Validate one normalized backend descriptor.

    The audit is intentionally provider-neutral.  It checks only the fields
    UnifiedQuantum relies on internally, so adapters can expose provider-specific
    metadata in ``BackendInfo.extra`` without being rejected.
    """
    issues: list[BackendAuditIssue] = []
    backend_id = backend.full_id()

    def add(severity: str, field: str, message: str) -> None:
        issues.append(BackendAuditIssue(backend_id, severity, field, message))

    if not backend.name:
        add("error", "name", "backend name is empty")
    if backend.num_qubits < 0:
        add("error", "num_qubits", "num_qubits must be non-negative")
    if backend.is_simulator and backend.is_hardware:
        add("error", "kind", "backend cannot be both simulator and hardware")
    if not backend.is_simulator and not backend.is_hardware:
        add("warning", "kind", "backend is neither simulator nor hardware")
    if backend.is_hardware and backend.num_qubits == 0:
        add("warning", "num_qubits", "hardware backend has no qubit count")
    if backend.is_hardware and not backend.topology:
        add("warning", "topology", "hardware backend has no connectivity topology")

    valid_statuses = {"available", "unavailable", "maintenance", "deprecated", "unknown"}
    if backend.status not in valid_statuses:
        add("warning", "status", f"status {backend.status!r} is not one of {sorted(valid_statuses)}")

    for field_name in ("avg_1q_fidelity", "avg_2q_fidelity", "avg_readout_fidelity"):
        value = getattr(backend, field_name)
        if value is not None and not 0.0 <= float(value) <= 1.0:
            add("error", field_name, "fidelity values must be in [0, 1]")

    if backend.num_qubits:
        for edge in backend.topology:
            if edge.u < 0 or edge.v < 0 or edge.u >= backend.num_qubits or edge.v >= backend.num_qubits:
                add("error", "topology", f"edge ({edge.u}, {edge.v}) is outside num_qubits={backend.num_qubits}")

    return issues


def audit_backends(
    backends: list[BackendInfo] | dict[Platform, list[BackendInfo]],
    *,
    fetch_failures: dict[Platform, str] | None = None,
) -> list[BackendAuditIssue]:
    """Validate normalized backend descriptors returned by the registry.

    Parameters
    ----------
    backends :
        Backend descriptors (flat list or per-platform dict).
    fetch_failures :
        Optional mapping of platforms that had credentials but failed
        to fetch, with the error message.  Each entry is emitted as a
        ``BackendAuditIssue(severity="warning")`` so the caller can see
        which platforms were not audited.
    """
    issues: list[BackendAuditIssue] = []

    # Report platforms that had credentials but failed to fetch
    if fetch_failures:
        for platform, error_msg in fetch_failures.items():
            issues.append(
                BackendAuditIssue(
                    backend_id=f"{platform.value}:__platform__",
                    severity="warning",
                    field="platform_fetch",
                    message=f"Failed to fetch {platform.value} backends: {error_msg}",
                )
            )

    if isinstance(backends, dict):
        items = [backend for platform_backends in backends.values() for backend in platform_backends]
    else:
        items = backends
    issues.extend(issue for backend in items for issue in audit_backend_info(backend))
    return issues


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
    from uniqc.backend_adapter.backend_info import parse_backend_id

    try:
        platform, name = parse_backend_id(identifier)
        backends, _ = fetch_platform_backends(platform)
        for backend in backends:
            if backend.name == name:
                return backend
        available = ", ".join(b.name for b in backends) or "(none)"
        raise ValueError(f"Backend '{name}' not found on platform '{platform.value}'. Available backends: {available}")
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
            f"Backend '{identifier}' not found on any platform. Use 'uniqc backend list' to see available backends."
        ) from None
