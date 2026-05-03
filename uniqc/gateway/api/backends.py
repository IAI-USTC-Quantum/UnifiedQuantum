"""Backend listing API — /api/backends.

The gateway UI needs more than the coarse backend cache contains.  BackendInfo
is still the source of truth for what devices exist, but per-qubit and per-edge
calibration details are enriched from the chip-characterization cache when it is
available.  This keeps the listing endpoint fast and avoids cloud API calls from
the web UI request path.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, HTTPException

from uniqc.backend_adapter.backend_cache import get_cached_backends, is_stale
from uniqc.backend_adapter.backend_info import BackendInfo, Platform
from uniqc.backend_adapter.backend_registry import fetch_platform_backends
from uniqc.backend_adapter.dummy_backend import list_dummy_backend_infos
from uniqc.cli.chip_cache import chip_cache_info, get_chip
from uniqc.cli.chip_info import ChipCharacterization, SingleQubitData, TwoQubitData

router = APIRouter()


def _platform_backends(platform: Platform) -> list[dict[str, Any]]:
    """Return cached backends for a platform, serialised for the API."""
    backends = list_dummy_backend_infos() if platform == Platform.DUMMY else get_cached_backends(platform)
    chip_meta = chip_cache_info()
    return [_backend_summary(b, chip_meta=chip_meta) for b in backends]


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _fidelity(value: Any) -> float | None:
    """Normalize fidelity-like values to [0, 1].

    Some platform adapters expose percentages (for example 95.0) while the
    canonical BackendInfo comment says values are probabilities.  The API layer
    normalizes before the UI sees the value.
    """
    result = _number(value)
    if result is None:
        return None
    if 1 < result <= 100:
        result = result / 100.0
    if 0 <= result <= 1:
        return result
    return None


def _microseconds(value: Any) -> float | None:
    result = _number(value)
    if result is None:
        return None
    # Quafu cache entries can arrive in seconds, while BackendInfo documents
    # microseconds.  Values this small are not plausible microsecond coherence
    # times, so treat them as seconds.
    if 0 < abs(result) < 0.01:
        result *= 1_000_000
    return result if result >= 0 else None


def _available(status: str, extra: dict[str, Any]) -> bool:
    if extra.get("available") is False:
        return False
    return status.strip().lower() in {
        "available",
        "online",
        "active",
        "operational",
        "ready",
    }


def _status_kind(status: str, available: bool) -> str:
    if available:
        return "available"
    normalized = status.strip().lower()
    if normalized in {"deprecated", "obsolete"}:
        return "deprecated"
    if normalized in {"busy", "running", "maintenance"}:
        return "busy"
    if normalized in {"unavailable", "offline", "inactive"}:
        return "unavailable"
    return "unknown"


def _chip_for_backend(b: BackendInfo) -> ChipCharacterization | None:
    if b.platform == Platform.DUMMY:
        source_platform = b.extra.get("source_platform")
        source_name = b.extra.get("source_name")
        if source_platform and source_name:
            try:
                return get_chip(Platform(source_platform), str(source_name))
            except ValueError:
                return None
    return get_chip(b.platform, b.name)


def _gate_names(extra: dict[str, Any], chip: ChipCharacterization | None) -> list[str]:
    gates: set[str] = set()
    for key in ("basis_gates", "valid_gates", "supported_gates"):
        raw = extra.get(key) or []
        if isinstance(raw, (list, tuple, set)):
            gates.update(str(g) for g in raw if str(g).strip())
    if chip is not None:
        gates.update(chip.global_info.single_qubit_gates)
        gates.update(chip.global_info.two_qubit_gates)
    return sorted(gates, key=str.lower)


def _single_qubit_map(chip: ChipCharacterization | None) -> dict[int, SingleQubitData]:
    if chip is None:
        return {}
    result: dict[int, SingleQubitData] = {}
    for item in chip.single_qubit_data:
        try:
            result[int(item.qubit_id)] = item
        except (TypeError, ValueError):
            continue
    return result


def _single_qubit_map_from_extra(extra: dict[str, Any]) -> dict[int, SingleQubitData]:
    result: dict[int, SingleQubitData] = {}
    raw = extra.get("per_qubit_calibration") or []
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            q = SingleQubitData.from_dict(item)
            result[int(q.qubit_id)] = q
        except (KeyError, TypeError, ValueError):
            continue
    return result


def _two_qubit_map(chip: ChipCharacterization | None) -> dict[tuple[int, int], TwoQubitData]:
    if chip is None:
        return {}
    result: dict[tuple[int, int], TwoQubitData] = {}
    for item in chip.two_qubit_data:
        u = int(item.qubit_u)
        v = int(item.qubit_v)
        if u == v:
            continue
        key = tuple(sorted((u, v)))
        existing = result.get(key)
        if existing is None:
            result[key] = item
        else:
            result[key] = TwoQubitData(
                qubit_u=existing.qubit_u,
                qubit_v=existing.qubit_v,
                gates=existing.gates + item.gates,
            )
    return result


def _two_qubit_map_from_extra(extra: dict[str, Any]) -> dict[tuple[int, int], TwoQubitData]:
    result: dict[tuple[int, int], TwoQubitData] = {}
    raw = extra.get("per_pair_calibration") or []
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            data = TwoQubitData.from_dict(item)
            u = int(data.qubit_u)
            v = int(data.qubit_v)
        except (KeyError, TypeError, ValueError):
            continue
        if u == v:
            continue
        key = tuple(sorted((u, v)))
        existing = result.get(key)
        if existing is None:
            result[key] = data
        else:
            result[key] = TwoQubitData(
                qubit_u=existing.qubit_u,
                qubit_v=existing.qubit_v,
                gates=existing.gates + data.gates,
            )
    return result


def _node_payload(
    qid: int,
    per_qubit: dict[int, SingleQubitData],
    avg_1q: float | None,
    avg_readout: float | None,
    avg_t1: float | None,
    avg_t2: float | None,
    available_qubits: set[int] | None,
) -> dict[str, Any]:
    q = per_qubit.get(qid)
    t1 = _microseconds(q.t1) if q else None
    t2 = _microseconds(q.t2) if q else None
    single_gate_fidelity = _fidelity(q.single_gate_fidelity) if q else None
    avg_readout_fidelity = _fidelity(q.avg_readout_fidelity) if q else None
    return {
        "id": qid,
        "available": available_qubits is None or qid in available_qubits,
        "t1": t1 if t1 is not None else avg_t1,
        "t2": t2 if t2 is not None else avg_t2,
        "freq": None,
        "single_gate_fidelity": (
            single_gate_fidelity if single_gate_fidelity is not None else avg_1q
        ),
        "avg_readout_fidelity": (
            avg_readout_fidelity if avg_readout_fidelity is not None else avg_readout
        ),
        "readout_fidelity_0": _fidelity(q.readout_fidelity_0) if q else None,
        "readout_fidelity_1": _fidelity(q.readout_fidelity_1) if q else None,
    }


def _edge_payload(
    u: int,
    v: int,
    per_pair: dict[tuple[int, int], TwoQubitData],
    avg_2q: float | None,
) -> dict[str, Any]:
    item = per_pair.get(tuple(sorted((u, v))))
    gates = []
    if item is not None:
        seen: set[tuple[str, float | None]] = set()
        for gate in item.gates:
            payload = (str(gate.gate), _fidelity(gate.fidelity))
            if payload not in seen:
                seen.add(payload)
                gates.append({"gate": payload[0], "fidelity": payload[1]})
    fidelity = None
    if gates:
        values = [g["fidelity"] for g in gates if g["fidelity"] is not None]
        fidelity = sum(values) / len(values) if values else None
    return {
        "u": u,
        "v": v,
        "fidelity": fidelity if fidelity is not None else avg_2q,
        "gates": gates,
    }


def _backend_summary(
    b: BackendInfo,
    *,
    chip_meta: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    chip = _chip_for_backend(b)
    cache_meta = (chip_meta or chip_cache_info()).get(b.full_id(), {})

    avg_1q = _fidelity(b.avg_1q_fidelity)
    avg_2q = _fidelity(b.avg_2q_fidelity)
    avg_readout = _fidelity(b.avg_readout_fidelity)
    avg_t1 = _microseconds(b.coherence_t1)
    avg_t2 = _microseconds(b.coherence_t2)

    per_qubit = _single_qubit_map(chip) or _single_qubit_map_from_extra(b.extra)
    per_pair = _two_qubit_map(chip) or _two_qubit_map_from_extra(b.extra)
    chip_available = {int(q) for q in chip.available_qubits} if chip else None
    if chip_available is None and isinstance(b.extra.get("available_qubits"), list):
        chip_available = set()
        for raw_qid in b.extra.get("available_qubits", []):
            try:
                chip_available.add(int(raw_qid))
            except (TypeError, ValueError):
                continue

    if chip is not None and chip.available_qubits:
        node_ids = sorted({int(q) for q in chip.available_qubits})
    elif chip_available:
        node_ids = sorted(chip_available)
    else:
        node_ids = list(range(max(0, int(b.num_qubits or 0))))

    raw_edges = list(chip.connectivity if chip and chip.connectivity else b.topology)
    seen_edges: set[tuple[int, int]] = set()
    edges: list[dict[str, Any]] = []
    for edge in raw_edges:
        u = int(edge.u)
        v = int(edge.v)
        if u == v:
            continue
        if u < 0 or v < 0:
            continue
        key = tuple(sorted((u, v)))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append(_edge_payload(u, v, per_pair, avg_2q))

    available = _available(b.status, b.extra)
    return {
        "id": b.extra.get("dummy_backend_id") if b.platform == Platform.DUMMY else b.full_id(),
        "name": b.name,
        "platform": b.platform.value,
        "num_qubits": b.num_qubits,
        "status": b.status,
        "status_kind": _status_kind(b.status, available),
        "available": available,
        "cache_stale": False if b.platform == Platform.DUMMY else is_stale(b.platform.value),
        "is_simulator": b.is_simulator,
        "is_hardware": b.is_hardware,
        "topology": {
            "nodes": [
                _node_payload(qid, per_qubit, avg_1q, avg_readout, avg_t1, avg_t2, chip_available)
                for qid in node_ids
            ],
            "edges": edges,
            "has_connectivity": bool(edges),
        },
        "fidelity": {
            "avg_1q": avg_1q,
            "avg_2q": avg_2q,
            "avg_readout": avg_readout,
        },
        "coherence": {
            "t1": avg_t1,
            "t2": avg_t2,
        },
        "queue_size": b.extra.get("task_in_queue"),
        "supported_gates": _gate_names(b.extra, chip),
        "calibration": {
            "available": chip is not None or bool(per_qubit or per_pair),
            "calibrated_at": chip.calibrated_at if chip else b.extra.get("calibrated_at"),
            "cache_age_seconds": cache_meta.get("age_seconds"),
            "cache_stale": cache_meta.get("is_stale"),
            "source": "chip-cache" if chip else "backend-cache",
        },
        "description": b.description or "",
        "extra": b.extra,
    }


@router.get("")
def list_backends() -> dict[str, Any]:
    """List all available backends across all platforms."""
    result: dict[str, Any] = {}
    for platform in Platform:
        result[platform.value] = _platform_backends(platform)
    return result


@router.get("/live")
def list_live_backends() -> list[dict[str, Any]]:
    """Flat list of all backends with their cache staleness."""
    all_backends: list[dict[str, Any]] = []
    chip_meta = chip_cache_info()
    for platform in Platform:
        backends = list_dummy_backend_infos() if platform == Platform.DUMMY else get_cached_backends(platform)
        for b in backends:
            summary = _backend_summary(b, chip_meta=chip_meta)
            summary["cache_stale"] = False if platform == Platform.DUMMY else is_stale(platform.value)
            all_backends.append(summary)
    return all_backends


@router.post("/refresh")
def refresh_backends(platform: str | None = None) -> dict[str, Any]:
    """Force-refresh cached backend information from platform APIs."""
    updated: dict[str, int] = {}
    warnings: list[str] = []

    if platform:
        try:
            target = Platform(platform)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}") from None
        targets = [target]
    else:
        targets = [Platform.ORIGINQ, Platform.QUAFU, Platform.IBM, Platform.DUMMY]

    for target in targets:
        try:
            backends, fetched = fetch_platform_backends(target, force_refresh=True)
            updated[target.value] = len(backends)
            if not fetched:
                warnings.append(f"{target.value}: served existing cache")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{target.value}: {exc}")

    return {
        "updated": updated,
        "warnings": warnings,
        "total": sum(updated.values()),
    }


@router.get("/{backend_id}")
def get_backend(backend_id: str) -> dict[str, Any]:
    """Get a specific backend by its full id (``platform:name``)."""
    if backend_id == "dummy" or backend_id.startswith("dummy:"):
        chip_meta = chip_cache_info()
        for b in list_dummy_backend_infos():
            if b.extra.get("dummy_backend_id") == backend_id:
                summary = _backend_summary(b, chip_meta=chip_meta)
                summary["cache_stale"] = False
                return summary
        raise HTTPException(status_code=404, detail=f"Backend '{backend_id}' not found")

    parts = backend_id.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid backend_id format")
    platform_str, name = parts
    try:
        platform = Platform(platform_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {platform_str}") from None

    backends = get_cached_backends(platform)
    chip_meta = chip_cache_info()
    for b in backends:
        if b.name == name:
            summary = _backend_summary(b, chip_meta=chip_meta)
            summary["cache_stale"] = is_stale(platform_str)
            return summary

    raise HTTPException(status_code=404, detail=f"Backend '{backend_id}' not found")
