"""Canonical dummy backend identifiers and local backend fixtures."""

from __future__ import annotations

import dataclasses
import re
from typing import Any

from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology

_VIRTUAL_LINE_RE = re.compile(r"^virtual-line-(\d+)$")
_VIRTUAL_GRID_RE = re.compile(r"^virtual-grid-(\d+)x(\d+)$")


@dataclasses.dataclass(frozen=True, slots=True)
class DummyBackendSpec:
    """Resolved configuration for one dummy backend identifier."""

    identifier: str
    name: str
    description: str
    available_qubits: list[int] | None = None
    available_topology: list[list[int]] | None = None
    chip_characterization: Any | None = None
    source_platform: Platform | None = None
    source_name: str | None = None
    noise_source: str = "none"


def _normalise_available_qubits(value: Any) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, int):
        return list(range(value))
    return [int(q) for q in value]


def _normalise_topology(value: Any) -> list[list[int]] | None:
    if value is None:
        return None
    return [[int(edge[0]), int(edge[1])] for edge in value]


def virtual_line_topology(num_qubits: int) -> list[list[int]]:
    if num_qubits < 1:
        raise ValueError("virtual-line-N requires N >= 1")
    return [[i, i + 1] for i in range(num_qubits - 1)]


def virtual_grid_topology(rows: int, cols: int) -> list[list[int]]:
    if rows < 1 or cols < 1:
        raise ValueError("virtual-grid-RxC requires R >= 1 and C >= 1")
    edges: list[list[int]] = []
    for r in range(rows):
        for c in range(cols):
            q = r * cols + c
            if c + 1 < cols:
                edges.append([q, q + 1])
            if r + 1 < rows:
                edges.append([q, q + cols])
    return edges


def _originq_alias(name: str) -> str:
    aliases = {
        "wk180": "WK_C180",
        "wk-c180": "WK_C180",
        "wk_c180": "WK_C180",
        "wuyuan:wk180": "WK_C180",
        "pqpumesh8": "PQPUMESH8",
    }
    return aliases.get(name.lower(), name)


def _normalise_source_name(platform: Platform, name: str) -> str:
    cleaned = name.strip()
    if platform == Platform.ORIGINQ:
        cleaned = _originq_alias(cleaned)
    return cleaned


def _find_cached_chip(platform: Platform, name: str) -> Any | None:
    from uniqc.cli.chip_cache import get_chip, list_cached_chips

    candidates = [name]
    if platform == Platform.ORIGINQ:
        candidates.append(_originq_alias(name))
    for candidate in candidates:
        chip = get_chip(platform, candidate)
        if chip is not None:
            return chip

    wanted = {candidate.lower() for candidate in candidates}
    wanted.update(candidate.replace("-", "_").lower() for candidate in candidates)
    for chip in list_cached_chips(platform):
        names = {
            chip.chip_name.lower(),
            chip.full_id.lower(),
            chip.chip_name.replace("-", "_").lower(),
        }
        if names & wanted:
            return chip
    return None


def _fetch_chip_characterization(platform: Platform, name: str) -> Any | None:
    if platform == Platform.ORIGINQ:
        from uniqc.backend_adapter.task.adapters.originq_adapter import OriginQAdapter
        from uniqc.cli.chip_cache import save_chip

        chip = OriginQAdapter().get_chip_characterization(name)
        if chip is not None:
            save_chip(chip)
        return chip
    return None


def resolve_dummy_backend(
    identifier: str = "dummy",
    *,
    allow_fetch: bool = True,
    **overrides: Any,
) -> DummyBackendSpec:
    """Resolve a canonical dummy backend identifier.

    Supported identifiers:
      - ``dummy``: unconstrained noiseless local simulator.
      - ``dummy:virtual-line-N``: noiseless N-qubit line topology.
      - ``dummy:virtual-grid-RxC``: noiseless R by C grid topology.
      - ``dummy:<platform>:<backend>``: noisy simulator using cached/fetched
        chip characterization for a real backend.
    """
    identifier = (identifier or "dummy").strip()
    if identifier == "dummy":
        spec = DummyBackendSpec(
            identifier="dummy",
            name="dummy",
            description="Unconstrained noiseless local simulator",
        )
    elif identifier.startswith("dummy:"):
        suffix = identifier.split(":", 1)[1].strip()
        line_match = _VIRTUAL_LINE_RE.match(suffix)
        grid_match = _VIRTUAL_GRID_RE.match(suffix)
        if line_match:
            n = int(line_match.group(1))
            spec = DummyBackendSpec(
                identifier=identifier,
                name=suffix,
                description=f"Noiseless virtual {n}-qubit line topology",
                available_qubits=list(range(n)),
                available_topology=virtual_line_topology(n),
            )
        elif grid_match:
            rows = int(grid_match.group(1))
            cols = int(grid_match.group(2))
            n = rows * cols
            spec = DummyBackendSpec(
                identifier=identifier,
                name=suffix,
                description=f"Noiseless virtual {rows}x{cols} grid topology",
                available_qubits=list(range(n)),
                available_topology=virtual_grid_topology(rows, cols),
            )
        else:
            parts = suffix.split(":", 1)
            if len(parts) != 2:
                raise ValueError(
                    "Dummy backend must be 'dummy', 'dummy:virtual-line-N', "
                    "'dummy:virtual-grid-RxC', or 'dummy:<platform>:<backend>'."
                )
            try:
                source_platform = Platform(parts[0])
            except ValueError:
                raise ValueError(f"Unknown dummy source platform: {parts[0]}") from None
            if source_platform == Platform.DUMMY:
                raise ValueError("Nested dummy backend identifiers are not supported")
            source_name = _normalise_source_name(source_platform, parts[1])
            chip = overrides.get("chip_characterization") or _find_cached_chip(source_platform, source_name)
            if chip is None and allow_fetch:
                chip = _fetch_chip_characterization(source_platform, source_name)
            if chip is None:
                raise ValueError(
                    f"No chip characterization available for {source_platform.value}:{source_name}. "
                    "Run 'uniqc backend chip-display <platform>/<backend> --update' first, "
                    "or pass chip_characterization explicitly."
                )
            available_qubits = list(int(q) for q in getattr(chip, "available_qubits", ()))
            available_topology = [[int(e.u), int(e.v)] for e in getattr(chip, "connectivity", ())]
            spec = DummyBackendSpec(
                identifier=f"dummy:{source_platform.value}:{source_name}",
                name=f"{source_platform.value}:{source_name}",
                description=f"Noisy local simulator calibrated from {source_platform.value}:{source_name}",
                available_qubits=available_qubits,
                available_topology=available_topology,
                chip_characterization=chip,
                source_platform=source_platform,
                source_name=source_name,
                noise_source="chip_characterization",
            )
    else:
        raise ValueError(f"Not a dummy backend identifier: {identifier}")

    available_qubits_override = overrides.get("available_qubits")
    available_topology_override = overrides.get("available_topology")
    chip_override = overrides.get("chip_characterization")

    available_qubits = _normalise_available_qubits(
        spec.available_qubits if available_qubits_override is None else available_qubits_override
    )
    available_topology = _normalise_topology(
        spec.available_topology if available_topology_override is None else available_topology_override
    )
    chip_characterization = spec.chip_characterization if chip_override is None else chip_override
    noise_source = spec.noise_source
    if chip_characterization is not None:
        noise_source = "chip_characterization"
    elif overrides.get("noise_model") is not None:
        noise_source = "noise_model"

    return dataclasses.replace(
        spec,
        available_qubits=available_qubits,
        available_topology=available_topology,
        chip_characterization=chip_characterization,
        noise_source=noise_source,
    )


def dummy_adapter_kwargs(identifier: str, **overrides: Any) -> dict[str, Any]:
    spec = resolve_dummy_backend(identifier, **overrides)
    return {
        "backend_id": spec.identifier,
        "chip_characterization": spec.chip_characterization,
        "noise_model": overrides.get("noise_model"),
        "available_qubits": spec.available_qubits,
        "available_topology": spec.available_topology,
    }


def _chip_averages(chip: Any) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    def avg(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    oneq = [
        float(q.single_gate_fidelity)
        for q in chip.single_qubit_data
        if q.single_gate_fidelity is not None
    ]
    readout = [
        float(q.avg_readout_fidelity)
        for q in chip.single_qubit_data
        if q.avg_readout_fidelity is not None
    ]
    t1 = [float(q.t1) for q in chip.single_qubit_data if q.t1 is not None]
    t2 = [float(q.t2) for q in chip.single_qubit_data if q.t2 is not None]
    twoq = [
        float(g.fidelity)
        for pair in chip.two_qubit_data
        for g in pair.gates
        if g.fidelity is not None
    ]
    return avg(oneq), avg(twoq), avg(readout), avg(t1), avg(t2)


def _info_from_spec(spec: DummyBackendSpec) -> BackendInfo:
    topology = tuple(QubitTopology(u=edge[0], v=edge[1]) for edge in (spec.available_topology or []))
    num_qubits = len(spec.available_qubits or [])
    avg_1q = avg_2q = avg_readout = t1 = t2 = None
    if spec.chip_characterization is not None:
        avg_1q, avg_2q, avg_readout, t1, t2 = _chip_averages(spec.chip_characterization)
    return BackendInfo(
        platform=Platform.DUMMY,
        name=spec.name,
        description=spec.description,
        num_qubits=num_qubits,
        topology=topology,
        status="available",
        is_simulator=True,
        is_hardware=False,
        extra={
            "available": True,
            "dummy_backend_id": spec.identifier,
            "dummy_kind": "hardware-noisy" if spec.source_platform else ("virtual" if topology else "ideal"),
            "noise_source": spec.noise_source,
            "source_platform": spec.source_platform.value if spec.source_platform else None,
            "source_name": spec.source_name,
            "available_qubits": spec.available_qubits or [],
        },
        avg_1q_fidelity=avg_1q,
        avg_2q_fidelity=avg_2q,
        avg_readout_fidelity=avg_readout,
        coherence_t1=t1,
        coherence_t2=t2,
    )


def list_dummy_backend_infos() -> list[BackendInfo]:
    """Return dummy backends that should be shown in backend lists.

    Chip-backed identifiers such as ``dummy:originq:WK_C180`` are intentionally
    not listed here. They are rule-based submission targets documented for
    users, not standalone backend cards in the management UI.
    """
    specs = [
        resolve_dummy_backend("dummy", allow_fetch=False),
        resolve_dummy_backend("dummy:virtual-line-3", allow_fetch=False),
        resolve_dummy_backend("dummy:virtual-grid-2x2", allow_fetch=False),
    ]

    seen: set[str] = set()
    infos: list[BackendInfo] = []
    for spec in specs:
        if spec.identifier in seen:
            continue
        seen.add(spec.identifier)
        infos.append(_info_from_spec(spec))
    return infos
