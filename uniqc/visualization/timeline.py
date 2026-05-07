"""Circuit scheduling and timeline visualization.

This module computes a left-compacted schedule from a compiled circuit and can
render both the existing table-style PDF timeline and static HTML/SVG views.
Logical circuits require gate-duration data from backend metadata,
chip-characterization data, or explicit ``gate_durations`` overrides.  Pulse
data that already carries start times remains supported without duration data.
"""

from __future__ import annotations

__all__ = [
    "TimelineDurationError",
    "TimelineGate",
    "TimelineSchedule",
    "circuit_to_html",
    "create_time_line_table",
    "format_result",
    "plot_time_line",
    "plot_time_line_html",
    "schedule_circuit",
]

from dataclasses import dataclass
import html
import json
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ImportError:
    pd = None

_TWO_QUBIT_GATES = {"CNOT", "CX", "CZ", "SWAP", "ISWAP", "ECR", "XX", "YY", "ZZ", "XY", "PHASE2Q"}
_MEASURE_GATES = {"MEASURE", "MEAS", "MEASUREMENT"}
_ZERO_DURATION_GATES = {"I", "ID", "BARRIER"}
_VIRTUAL_Z_GATES = {"Z", "RZ", "U1", "P", "PHASE", "S", "T", "SDG", "TDG"}
_DEFAULT_BASIS_GATES = ["cz", "sx", "rz"]


class TimelineDurationError(ValueError):
    """Raised when a logical circuit cannot be scheduled without durations."""

# Re-export from central module (local name kept for backward compat within this file)
from uniqc.exceptions import TimelineDurationError as TimelineDurationError  # noqa: F401, E501


@dataclass(frozen=True, slots=True)
class TimelineGate:
    """One scheduled operation."""

    index: int
    name: str
    qubits: tuple[int, ...]
    params: tuple[Any, ...] = ()
    cbits: tuple[int, ...] = ()
    control_qubits: tuple[int, ...] = ()
    start: float = 0.0
    duration: float = 0.0
    end: float = 0.0
    layer: int = 0
    raw: str | None = None

    @property
    def resources(self) -> tuple[int, ...]:
        """Return all quantum resources touched by this operation."""
        return _unique_ints((*self.control_qubits, *self.qubits))

    @property
    def is_barrier(self) -> bool:
        return self.name.upper() == "BARRIER"

    @property
    def is_virtual(self) -> bool:
        return self.name.upper() in _VIRTUAL_Z_GATES

    def tooltip(self, *, unit: str = "ns") -> str:
        lines = [
            f"gate: {self.name}",
            f"qubits: {list(self.qubits)}",
            f"start: {_format_time(self.start)} {unit}",
            f"duration: {_format_time(self.duration)} {unit}",
            f"end: {_format_time(self.end)} {unit}",
        ]
        if self.control_qubits:
            lines.append(f"controls: {list(self.control_qubits)}")
        if self.cbits:
            lines.append(f"cbits: {list(self.cbits)}")
        if self.params:
            lines.append(f"params: {list(self.params)}")
        if self.raw:
            lines.append(f"raw: {self.raw}")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class TimelineSchedule:
    """Scheduled circuit timeline."""

    gates: tuple[TimelineGate, ...]
    qubits: tuple[int, ...]
    total_duration: float
    unit: str = "ns"
    gate_durations: dict[str, float] | None = None

    @property
    def time_points(self) -> tuple[int | float, ...]:
        return tuple(_format_time(t) for t in sorted({gate.start for gate in self.gates}))


@dataclass(frozen=True, slots=True)
class _ProgramEntry:
    name: str
    qubits: tuple[int, ...]
    params: tuple[Any, ...] = ()
    cbits: tuple[int, ...] = ()
    control_qubits: tuple[int, ...] = ()
    explicit_start: float | None = None
    raw: str | None = None

    @property
    def resources(self) -> tuple[int, ...]:
        return _unique_ints((*self.control_qubits, *self.qubits))

    @property
    def is_barrier(self) -> bool:
        return self.name.upper() == "BARRIER"


def schedule_circuit(
    compiled_prog: Any,
    *,
    backend_info: Any | None = None,
    chip_characterization: Any | None = None,
    gate_durations: dict[str, float] | None = None,
    compile_to_basis: bool = True,
    basis_gates: list[str] | None = None,
    unit: str = "ns",
) -> TimelineSchedule:
    """Schedule a compiled circuit by left-compacting gates on qubit resources.

    .. important::
       Whenever ``compile_to_basis=True`` (the default), this function calls
       :func:`uniqc.compile.compile`, which **requires** the ``[qiskit]`` extra:
       ``pip install "unified-quantum[qiskit]"``.  There is no native-only
       bypass: even if the input circuit already uses only chip-native gates
       (e.g. CZ/SX/RZ), ``schedule_circuit`` will still call ``compile()`` to
       collect timing data unless every entry already carries an explicit
       ``start`` time.  To skip ``compile()`` entirely you must pass pulse /
       timeline data where every entry has ``start_time`` set, and pass
       ``compile_to_basis=False`` (otherwise ``TimelineDurationError`` is
       raised).

    Parameters
    ----------
    compiled_prog:
        A ``Circuit``-like object, OriginIR text, JSON pulse data, or a list of
        gate dictionaries.
    backend_info, chip_characterization:
        Backend metadata used to resolve gate durations. ``BackendInfo.extra``
        may contain ``gate_durations``, ``single_qubit_gate_time``,
        ``two_qubit_gate_time``, and ``measure_time``.
    gate_durations:
        Explicit duration overrides. Gate names are case-insensitive. Generic
        keys ``"1q"``, ``"2q"``, and ``"measure"`` are supported.
    compile_to_basis:
        Logical circuits must be compiled to basis gates before scheduling.
        This flag defaults to ``True`` and may only be disabled for inputs that
        already carry explicit start times.
    basis_gates:
        Basis gate override forwarded to ``compile()`` when
        ``compile_to_basis=True``.
    unit:
        Display unit label for renderers. Numeric values are not converted.

    Raises
    ------
    TimelineDurationError
        If the circuit lacks explicit start times and a non-virtual operation
        cannot be assigned a duration from backend metadata or overrides.
    """
    entries = _normalise_program(compiled_prog)
    has_explicit_start_times = any(entry.explicit_start is not None for entry in entries)
    if not has_explicit_start_times:
        if not compile_to_basis:
            raise TimelineDurationError(
                "Timeline scheduling requires compiling logical circuits to basis gates first. "
                "Use compile_to_basis=True, or pass pulse/timeline data with explicit start times."
            )
        compiled_prog = _compile_to_basis_for_timeline(
            compiled_prog,
            entries,
            backend_info=backend_info,
            chip_characterization=chip_characterization,
            basis_gates=basis_gates,
        )
        entries = _normalise_program(compiled_prog)
    durations = _resolve_gate_durations(
        backend_info=backend_info,
        chip_characterization=chip_characterization,
        gate_durations=gate_durations,
    )
    needs_duration_data = any(entry.explicit_start is None for entry in entries if not entry.is_barrier)

    all_qubits = sorted({q for entry in entries for q in entry.resources})
    available_at: dict[int, float] = {q: 0.0 for q in all_qubits}
    scheduled: list[TimelineGate] = []
    start_to_layer: dict[float, int] = {}

    for index, entry in enumerate(entries):
        resources = entry.resources
        if entry.is_barrier:
            barrier_qubits = resources or tuple(all_qubits)
            boundary = max((available_at.get(q, 0.0) for q in barrier_qubits), default=0.0)
            for q in barrier_qubits:
                available_at[q] = boundary
            layer = _layer_for_start(start_to_layer, boundary)
            scheduled.append(
                TimelineGate(
                    index=index,
                    name="BARRIER",
                    qubits=barrier_qubits,
                    start=boundary,
                    duration=0.0,
                    end=boundary,
                    layer=layer,
                    raw=entry.raw,
                )
            )
            continue

        if not resources:
            continue
        duration = _duration_for_gate(entry.name, resources, durations, strict=needs_duration_data)
        start = (
            float(entry.explicit_start)
            if entry.explicit_start is not None
            else max((available_at.get(q, 0.0) for q in resources), default=0.0)
        )
        end = start + duration
        for q in resources:
            available_at[q] = end
        layer = _layer_for_start(start_to_layer, start)
        scheduled.append(
            TimelineGate(
                index=index,
                name=_display_gate_name(entry.name),
                qubits=entry.qubits,
                params=entry.params,
                cbits=entry.cbits,
                control_qubits=entry.control_qubits,
                start=start,
                duration=duration,
                end=end,
                layer=layer,
                raw=entry.raw,
            )
        )

    total_duration = max((gate.end for gate in scheduled), default=0.0)
    qubits = tuple(sorted({q for gate in scheduled for q in gate.resources}))
    return TimelineSchedule(
        gates=tuple(scheduled),
        qubits=qubits,
        total_duration=total_duration,
        unit=unit,
        gate_durations=durations,
    )


def format_result(
    compiled_prog: Any,
    *,
    backend_info: Any | None = None,
    chip_characterization: Any | None = None,
    gate_durations: dict[str, float] | None = None,
    compile_to_basis: bool = True,
    basis_gates: list[str] | None = None,
):
    """Format a program into legacy ``(gate_layers, qubits, time_line)`` data."""
    schedule = schedule_circuit(
        compiled_prog,
        backend_info=backend_info,
        chip_characterization=chip_characterization,
        gate_durations=gate_durations,
        compile_to_basis=compile_to_basis,
        basis_gates=basis_gates,
    )

    gate_layers: dict[int, list[tuple[str, int | list[int], float, int | float]]] = {}
    for gate in schedule.gates:
        if gate.is_barrier:
            continue
        qubit: int | list[int] = gate.qubits[0] if len(gate.qubits) == 1 else list(gate.qubits)
        angle = float(gate.params[0]) if gate.params and _is_number(gate.params[0]) else 0.0
        gate_layers.setdefault(gate.layer, []).append((gate.name, qubit, angle, _format_time(gate.start)))
    return gate_layers, list(schedule.qubits), list(schedule.time_points)


def create_time_line_table(layer_dict, qubit_list, time_line):
    """Create a pandas DataFrame-like timeline table from legacy layer data."""
    if pd is not None:
        time_line_table = pd.DataFrame(columns=time_line, index=[f"qubit {i}" for i in qubit_list])
    else:
        time_line_table = _SimpleTimelineTable(columns=time_line, index=[f"qubit {i}" for i in qubit_list])

    for gates in layer_dict.values():
        for gate_name, qubit, angle, time in gates:
            label = gate_name if gate_name.upper() in _MEASURE_GATES else f"{gate_name} {round(angle, 3)}"
            if isinstance(qubit, int):
                time_line_table.loc[f"qubit {qubit}", time] = label
            else:
                for q in qubit:
                    time_line_table.loc[f"qubit {q}", time] = label
    return time_line_table.fillna("idle")


def plot_time_line(
    compiled_prog,
    figure_save_path: str | Path = Path.cwd() / "timeline_plot",
    *,
    backend_info: Any | None = None,
    chip_characterization: Any | None = None,
    gate_durations: dict[str, float] | None = None,
    compile_to_basis: bool = True,
    basis_gates: list[str] | None = None,
):
    """Plot the quantum circuit timeline as table-style PDF files."""
    import matplotlib.pyplot as plt

    format_prog, qubit_list, time_line = format_result(
        compiled_prog,
        backend_info=backend_info,
        chip_characterization=chip_characterization,
        gate_durations=gate_durations,
        compile_to_basis=compile_to_basis,
        basis_gates=basis_gates,
    )
    time_line_table = create_time_line_table(format_prog, qubit_list, time_line)
    depth = len(time_line)
    if depth == 0:
        return

    figure_save_path = Path(figure_save_path)
    figure_save_path.mkdir(parents=True, exist_ok=True)

    split_table = depth // 20 + 1
    width = min(20, depth)
    cmap = {
        "RPhi90": "lightblue",
        "RPhi180": "orange",
        "CZ": "mistyrose",
        "CNOT": "mistyrose",
        "CX": "mistyrose",
        "SWAP": "mistyrose",
        "idle": "white",
        "MEASURE": "gray",
        "Measure": "gray",
    }

    for i in range(1, split_table + 1):
        start = (i - 1) * 20
        end = min(i * 20, depth)
        if start >= end:
            continue
        plt.figure(figsize=(width, max(1.0, len(qubit_list) / 2)))
        plt.axis("off")
        if pd is not None:
            values = time_line_table.values[:, start:end]
        else:
            values = [row[start:end] for row in time_line_table.values]
        columns = time_line_table.columns[start:end]
        cell_colours = [[cmap.get(str(x).split(" ")[0], "white") for x in row] for row in values]
        plt.table(
            cellText=values,
            colLabels=columns,
            colWidths=[0.05] * len(columns),
            rowLabels=time_line_table.index,
            loc="center",
            cellColours=cell_colours,
        )
        plt.savefig(figure_save_path / f"timeline_{i}.pdf")
        plt.close()


def plot_time_line_html(
    compiled_prog: Any,
    output_path: str | Path | None = None,
    *,
    backend_info: Any | None = None,
    chip_characterization: Any | None = None,
    gate_durations: dict[str, float] | None = None,
    compile_to_basis: bool = True,
    basis_gates: list[str] | None = None,
    title: str = "Quantum circuit timeline",
    unit: str = "ns",
) -> str:
    """Render a scheduled timeline as static HTML/SVG.

    Each gate carries an SVG ``title`` tooltip with its qubits, parameters,
    start time, duration, and end time.
    """
    schedule = schedule_circuit(
        compiled_prog,
        backend_info=backend_info,
        chip_characterization=chip_characterization,
        gate_durations=gate_durations,
        compile_to_basis=compile_to_basis,
        basis_gates=basis_gates,
        unit=unit,
    )
    document = _html_document(title, _schedule_to_svg(schedule, use_timing=True), schedule.unit)
    if output_path is not None:
        Path(output_path).write_text(document, encoding="utf-8")
    return document


def circuit_to_html(
    circuit: Any,
    output_path: str | Path | None = None,
    *,
    title: str = "Quantum circuit",
) -> str:
    """Render a static HTML/SVG circuit diagram without timing requirements."""
    schedule = _layered_circuit_schedule(_normalise_program(circuit))
    document = _html_document(title, _schedule_to_svg(schedule, use_timing=False), schedule.unit)
    if output_path is not None:
        Path(output_path).write_text(document, encoding="utf-8")
    return document


def _compile_to_basis_for_timeline(
    compiled_prog: Any,
    entries: list[_ProgramEntry],
    *,
    backend_info: Any | None,
    chip_characterization: Any | None,
    basis_gates: list[str] | None,
) -> Any:
    from uniqc.compile import compile as compile_circuit

    target_backend = backend_info
    if not _has_topology(target_backend) and not _has_connectivity(chip_characterization):
        target_backend = _virtual_all_to_all_backend(entries)

    return compile_circuit(
        compiled_prog,
        backend_info=target_backend,
        basis_gates=basis_gates or _DEFAULT_BASIS_GATES,
        chip_characterization=chip_characterization,
        output_format="circuit",
    )


def _has_topology(backend_info: Any | None) -> bool:
    return bool(getattr(backend_info, "topology", None))


def _has_connectivity(chip_characterization: Any | None) -> bool:
    return bool(getattr(chip_characterization, "connectivity", None))


def _virtual_all_to_all_backend(entries: list[_ProgramEntry]) -> Any:
    from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology

    qubits = sorted({q for entry in entries for q in entry.resources})
    if not qubits:
        qubits = [0]

    if len(qubits) == 1:
        topology = (QubitTopology(qubits[0], qubits[0]),)
    else:
        topology = tuple(QubitTopology(u, v) for u in qubits for v in qubits if u != v)

    return BackendInfo(
        platform=Platform.DUMMY,
        name="timeline-virtual-all-to-all",
        num_qubits=max(qubits) + 1,
        topology=topology,
        is_simulator=True,
        extra={"basis_gates": list(_DEFAULT_BASIS_GATES)},
    )


def _normalise_program(compiled_prog: Any) -> list[_ProgramEntry]:
    if hasattr(compiled_prog, "opcode_list"):
        return _opcode_list_to_entries(compiled_prog)
    if hasattr(compiled_prog, "originir"):
        return _originir_to_entries(compiled_prog.originir)
    if isinstance(compiled_prog, str):
        text = compiled_prog.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return _originir_to_entries(text)
        if isinstance(parsed, list):
            return [_json_gate_to_entry(entry) for entry in parsed]
        if isinstance(parsed, dict):
            return [_json_gate_to_entry(parsed)]
        return []
    if isinstance(compiled_prog, list):
        return [_json_gate_to_entry(entry) for entry in compiled_prog]
    if isinstance(compiled_prog, dict):
        return [_json_gate_to_entry(compiled_prog)]
    return []


def _opcode_list_to_entries(circuit: Any) -> list[_ProgramEntry]:
    entries: list[_ProgramEntry] = []
    for opcode in getattr(circuit, "opcode_list", []):
        operation, qubits, cbits, params, _dagger, control_qubits = opcode
        all_qubits = _to_int_tuple(qubits)
        entries.append(
            _ProgramEntry(
                name=str(operation),
                qubits=all_qubits,
                params=_to_tuple(params),
                cbits=_to_int_tuple(cbits),
                control_qubits=_to_int_tuple(control_qubits),
                raw=str(opcode),
            )
        )
    measure_list = getattr(circuit, "measure_list", None) or []
    for cbit, qubit in enumerate(measure_list):
        entries.append(
            _ProgramEntry(
                name="MEASURE",
                qubits=(int(qubit),),
                cbits=(cbit,),
                raw=f"MEASURE q[{int(qubit)}], c[{cbit}]",
            )
        )
    return entries


def _originir_to_entries(originir: str) -> list[_ProgramEntry]:
    entries: list[_ProgramEntry] = []
    try:
        from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser
    except ImportError:
        return entries

    for line in originir.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            op, qubit, cbit, param, dagger, ctrl = OriginIR_LineParser.parse_line(stripped)
        except Exception:
            continue
        if op is None or op in {"QINIT", "CREG", "CONTROL", "ENDCONTROL", "DAGGER", "ENDDAGGER", "DEF", "ENDDEF"}:
            continue
        entries.append(
            _ProgramEntry(
                name=str(op),
                qubits=_to_int_tuple(qubit),
                params=_to_tuple(param),
                cbits=_to_int_tuple(cbit),
                control_qubits=_to_int_tuple(ctrl),
                raw=stripped,
            )
        )
    return entries


def _json_gate_to_entry(entry: Any) -> _ProgramEntry:
    if not isinstance(entry, dict) or not entry:
        return _ProgramEntry("UNKNOWN", ())

    if "gate" in entry or "name" in entry:
        name = str(entry.get("gate", entry.get("name")))
        return _ProgramEntry(
            name=name,
            qubits=_to_int_tuple(entry.get("qubits", entry.get("q", ()))),
            params=_to_tuple(entry.get("params", ())),
            cbits=_to_int_tuple(entry.get("cbits", entry.get("c", ()))),
            control_qubits=_to_int_tuple(entry.get("controls", entry.get("control_qubits", ()))),
            explicit_start=_optional_float(entry.get("start", entry.get("t", None))),
            raw=json.dumps(entry, ensure_ascii=False),
        )

    gate_name = str(next(iter(entry.keys())))
    values = next(iter(entry.values()))
    values = values if isinstance(values, list) else [values]
    upper = gate_name.upper()

    if upper == "RPHI":
        qubit = int(values[0])
        params: tuple[Any, ...] = tuple(values[1:3])
        start = float(values[3]) if len(values) > 3 and _is_number(values[3]) else None
        name = "RPhi90" if len(values) > 2 and float(values[2]) == 90.0 else "RPhi180"
        return _ProgramEntry(name=name, qubits=(qubit,), params=params, explicit_start=start, raw=str(entry))

    if upper in _MEASURE_GATES:
        qubit_param = values[0] if values else []
        start = float(values[1]) if len(values) > 1 and _is_number(values[1]) else None
        return _ProgramEntry(
            name="MEASURE",
            qubits=_to_int_tuple(qubit_param),
            explicit_start=start,
            raw=str(entry),
        )

    arity = _gate_arity(upper, values)
    qubits = tuple(int(q) for q in values[:arity])
    params = tuple(values[arity:])
    start = None
    if params and _is_number(params[-1]) and (upper in _TWO_QUBIT_GATES or len(params) > 1):
        start = float(params[-1])
        params = params[:-1]
    return _ProgramEntry(name=gate_name, qubits=qubits, params=params, explicit_start=start, raw=str(entry))


def _resolve_gate_durations(
    *,
    backend_info: Any | None,
    chip_characterization: Any | None,
    gate_durations: dict[str, float] | None,
) -> dict[str, float]:
    durations: dict[str, float] = {}

    if backend_info is not None:
        extra = getattr(backend_info, "extra", {}) or {}
        durations.update(_normalise_duration_dict(extra.get("gate_durations", {})))
        if extra.get("single_qubit_gate_time") is not None:
            durations["1Q"] = float(extra["single_qubit_gate_time"])
        if extra.get("two_qubit_gate_time") is not None:
            durations["2Q"] = float(extra["two_qubit_gate_time"])
        if extra.get("measure_time") is not None:
            durations["MEASURE"] = float(extra["measure_time"])

    if chip_characterization is not None:
        global_info = getattr(chip_characterization, "global_info", None)
        one_q = getattr(global_info, "single_qubit_gate_time", None)
        two_q = getattr(global_info, "two_qubit_gate_time", None)
        if one_q is not None:
            durations["1Q"] = float(one_q)
        if two_q is not None:
            durations["2Q"] = float(two_q)

    if gate_durations:
        durations.update(_normalise_duration_dict(gate_durations))

    return durations


def _duration_for_gate(gate_name: str, qubits: tuple[int, ...], durations: dict[str, float], *, strict: bool) -> float:
    upper = gate_name.upper()
    if upper in _ZERO_DURATION_GATES or upper in _VIRTUAL_Z_GATES:
        return 0.0
    if upper in durations:
        return durations[upper]
    if upper in _MEASURE_GATES:
        if "MEASURE" in durations:
            return durations["MEASURE"]
        if strict:
            raise TimelineDurationError(_missing_duration_message(gate_name, "measure"))
        return 0.0
    if len(qubits) >= 2 or upper in _TWO_QUBIT_GATES:
        if "2Q" in durations:
            return durations["2Q"]
        if strict:
            raise TimelineDurationError(_missing_duration_message(gate_name, "2q"))
        return 0.0
    if "1Q" in durations:
        return durations["1Q"]
    if strict:
        raise TimelineDurationError(_missing_duration_message(gate_name, "1q"))
    return 0.0


def _missing_duration_message(gate_name: str, generic_key: str) -> str:
    return (
        f"No duration is available for gate {gate_name!r}. Provide backend_info.extra timing data, "
        "chip_characterization.global_info gate times, or gate_durations with either the exact gate "
        f"name or generic key {generic_key!r}."
    )


def _layered_circuit_schedule(entries: list[_ProgramEntry]) -> TimelineSchedule:
    all_qubits = sorted({q for entry in entries for q in entry.resources})
    available_layer: dict[int, int] = {q: 0 for q in all_qubits}
    gates: list[TimelineGate] = []

    for index, entry in enumerate(entries):
        resources = entry.resources
        if entry.is_barrier:
            barrier_qubits = resources or tuple(all_qubits)
            layer = max((available_layer.get(q, 0) for q in barrier_qubits), default=0)
            for q in barrier_qubits:
                available_layer[q] = layer + 1
            gates.append(
                TimelineGate(index, "BARRIER", barrier_qubits, start=float(layer), end=float(layer + 1), layer=layer)
            )
            continue
        if not resources:
            continue
        layer = max((available_layer.get(q, 0) for q in resources), default=0)
        for q in resources:
            available_layer[q] = layer + 1
        gates.append(
            TimelineGate(
                index=index,
                name=_display_gate_name(entry.name),
                qubits=entry.qubits,
                params=entry.params,
                cbits=entry.cbits,
                control_qubits=entry.control_qubits,
                start=float(layer),
                duration=1.0,
                end=float(layer + 1),
                layer=layer,
                raw=entry.raw,
            )
        )

    total_duration = max((gate.end for gate in gates), default=0.0)
    qubits = tuple(sorted({q for gate in gates for q in gate.resources}))
    return TimelineSchedule(tuple(gates), qubits, total_duration, unit="layer")


def _schedule_to_svg(schedule: TimelineSchedule, *, use_timing: bool) -> str:
    if not schedule.qubits:
        return '<svg class="uniqc-circuit" width="640" height="120"><text x="24" y="64">Empty circuit</text></svg>'

    lane_height = 54
    top = 48
    left = 76
    right = 36
    gate_h = 30
    min_gate_w = 34

    if use_timing:
        span = max(schedule.total_duration, 1.0)
        scale = min(8.0, max(0.8, 920.0 / span))
        x_for = lambda gate: left + gate.start * scale
        w_for = lambda gate: max(min_gate_w, gate.duration * scale if gate.duration > 0 else min_gate_w)
        body_width = max(720, int(left + span * scale + right + min_gate_w))
    else:
        scale = 88.0
        x_for = lambda gate: left + gate.layer * scale
        w_for = lambda gate: min_gate_w
        max_layer = max((gate.layer for gate in schedule.gates), default=0)
        body_width = int(left + (max_layer + 1) * scale + right + min_gate_w)

    q_to_y = {q: top + i * lane_height for i, q in enumerate(schedule.qubits)}
    height = top + (len(schedule.qubits) - 1) * lane_height + 58

    parts = [
        f'<svg class="uniqc-circuit" width="{body_width}" height="{height}" '
        f'viewBox="0 0 {body_width} {height}" xmlns="http://www.w3.org/2000/svg" role="img">',
        "<defs>",
        '<style>.wire{stroke:#677083;stroke-width:1.4}.qlabel{fill:#1f2937;font:13px ui-monospace,monospace}'
        ".gate{stroke:#243047;stroke-width:1.1;rx:5;ry:5}.gate-text{fill:#111827;font:12px Arial,sans-serif;"
        "text-anchor:middle;dominant-baseline:middle}.connector{stroke:#384152;stroke-width:1.2}.barrier{stroke:#7a3e00;"
        "stroke-width:1.5;stroke-dasharray:4 4}.tick{stroke:#d6dbe4;stroke-width:1}.tick-text{fill:#64748b;"
        "font:11px ui-monospace,monospace}.virtual{stroke-dasharray:3 2}</style>",
        "</defs>",
    ]

    if use_timing and schedule.gates:
        ticks = _timeline_ticks(schedule.total_duration)
        for tick in ticks:
            x = left + tick * scale
            parts.append(f'<line class="tick" x1="{x:.2f}" x2="{x:.2f}" y1="20" y2="{height - 18}"/>')
            parts.append(
                f'<text class="tick-text" x="{x:.2f}" y="16" text-anchor="middle">{html.escape(str(_format_time(tick)))}</text>'
            )

    for q, y in q_to_y.items():
        parts.append(f'<text class="qlabel" x="12" y="{y + 4}">q[{q}]</text>')
        parts.append(f'<line class="wire" x1="{left - 8}" x2="{body_width - right}" y1="{y}" y2="{y}"/>')

    for gate in schedule.gates:
        resources = gate.resources
        if not resources:
            continue
        ys = [q_to_y[q] for q in resources if q in q_to_y]
        if not ys:
            continue
        x = x_for(gate)
        width = w_for(gate)
        center_x = x + width / 2
        tooltip = html.escape(gate.tooltip(unit=schedule.unit))
        if gate.is_barrier:
            parts.append(f"<g><title>{tooltip}</title>")
            for y in ys:
                parts.append(f'<line class="barrier" x1="{center_x:.2f}" x2="{center_x:.2f}" y1="{y - 20}" y2="{y + 20}"/>')
            parts.append("</g>")
            continue

        if len(ys) > 1:
            parts.append(f'<line class="connector" x1="{center_x:.2f}" x2="{center_x:.2f}" y1="{min(ys):.2f}" y2="{max(ys):.2f}"/>')

        label = html.escape(_gate_label(gate.name))
        fill = _gate_color(gate)
        css_class = "gate virtual" if gate.is_virtual else "gate"
        for y in ys:
            parts.append(f"<g><title>{tooltip}</title>")
            parts.append(
                f'<rect class="{css_class}" x="{x:.2f}" y="{y - gate_h / 2:.2f}" '
                f'width="{width:.2f}" height="{gate_h}" fill="{fill}"/>'
            )
            parts.append(f'<text class="gate-text" x="{center_x:.2f}" y="{y + 1:.2f}">{label}</text>')
            parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


def _html_document(title: str, svg: str, unit: str) -> str:
    escaped_title = html.escape(title)
    escaped_unit = html.escape(unit)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{ margin: 0; padding: 24px; background: #f8fafc; color: #111827; font-family: Arial, sans-serif; }}
    .uniqc-wrap {{ overflow-x: auto; border: 1px solid #d8dee9; background: #ffffff; border-radius: 6px; padding: 16px; }}
    h1 {{ font-size: 18px; margin: 0 0 12px; font-weight: 600; }}
    .meta {{ color: #64748b; font-size: 12px; margin: 0 0 14px; }}
    svg.uniqc-circuit {{ display: block; max-width: none; }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  <p class="meta">Static render. Hover a gate to inspect parameters and timing ({escaped_unit}).</p>
  <div class="uniqc-wrap">
{svg}
  </div>
</body>
</html>
"""


def _normalise_duration_dict(values: dict[str, Any]) -> dict[str, float]:
    durations: dict[str, float] = {}
    for key, value in values.items():
        durations[_normalise_duration_key(str(key))] = float(value)
    return durations


def _normalise_duration_key(key: str) -> str:
    compact = key.strip().replace("-", "_").replace(" ", "_").upper()
    aliases = {
        "1Q": "1Q",
        "1_Q": "1Q",
        "ONE_QUBIT": "1Q",
        "SINGLE": "1Q",
        "SINGLE_QUBIT": "1Q",
        "SINGLE_QUBIT_GATE_TIME": "1Q",
        "2Q": "2Q",
        "2_Q": "2Q",
        "TWO_QUBIT": "2Q",
        "TWO_QUBIT_GATE_TIME": "2Q",
        "MEAS": "MEASURE",
        "MEASUREMENT": "MEASURE",
        "MEASURE_TIME": "MEASURE",
    }
    return aliases.get(compact, compact)


def _gate_arity(upper: str, values: list[Any]) -> int:
    if upper in _TWO_QUBIT_GATES:
        return 2
    if upper in {"TOFFOLI", "CCX", "CSWAP"}:
        return 3
    return min(1, len(values))


def _display_gate_name(name: str) -> str:
    if name.upper() in _MEASURE_GATES:
        return "MEASURE"
    return name


def _gate_label(name: str) -> str:
    upper = name.upper()
    if upper == "MEASURE":
        return "M"
    if upper == "BARRIER":
        return "|"
    return name[:8]


def _gate_color(gate: TimelineGate) -> str:
    upper = gate.name.upper()
    if upper in _MEASURE_GATES:
        return "#d1d5db"
    if gate.is_virtual:
        return "#ecfdf5"
    if len(gate.resources) >= 2:
        return "#fee2e2"
    return "#dbeafe"


def _timeline_ticks(total_duration: float) -> list[float]:
    if total_duration <= 0:
        return [0.0]
    raw_step = total_duration / 8
    magnitude = 10 ** max(0, len(str(int(raw_step))) - 1)
    step = max(1.0, round(raw_step / magnitude) * magnitude)
    ticks: list[float] = []
    value = 0.0
    while value <= total_duration + 1e-9:
        ticks.append(value)
        value += step
    if ticks[-1] < total_duration:
        ticks.append(total_duration)
    return ticks


def _layer_for_start(layer_by_start: dict[float, int], start: float) -> int:
    if start not in layer_by_start:
        layer_by_start[start] = len(layer_by_start)
    return layer_by_start[start]


def _is_explicit_pulse_data(compiled_prog: Any) -> bool:
    return any(entry.explicit_start is not None for entry in _normalise_program(compiled_prog))


def _to_tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def _to_int_tuple(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, set):
        value = sorted(value)
    if isinstance(value, tuple | list):
        return tuple(int(v) for v in value if v is not None)
    return (int(value),)


def _unique_ints(values: tuple[int, ...]) -> tuple[int, ...]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _optional_float(value: Any) -> float | None:
    return float(value) if _is_number(value) else None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float)


def _format_time(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(float(value), 6)


class _SimpleTimelineTable:
    """Small pandas-like table used when pandas is not installed."""

    def __init__(self, *, columns: list[int | float], index: list[str]) -> None:
        self.columns = list(columns)
        self.index = list(index)
        self._data = [[None for _ in self.columns] for _ in self.index]
        self.loc = _SimpleTimelineLoc(self)

    @property
    def values(self):
        return self._data

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.index), len(self.columns))

    def fillna(self, value: str):
        for r, row in enumerate(self._data):
            for c, cell in enumerate(row):
                if cell is None:
                    self._data[r][c] = value
        return self

    def __len__(self) -> int:
        return len(self.index)


class _SimpleTimelineLoc:
    def __init__(self, table: _SimpleTimelineTable) -> None:
        self._table = table

    def __setitem__(self, key, value) -> None:
        row_key, col_key = key
        row_idx = self._table.index.index(row_key)
        col_idx = self._table.columns.index(col_key)
        self._table.values[row_idx][col_idx] = value
