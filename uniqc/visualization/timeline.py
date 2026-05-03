"""Compiled circuit timeline analysis and visualization.

The timeline can be built from either backend pulse data that already carries
start times or from a logical circuit/OriginIR program.  When start times are
missing, the schedule is computed from backend/calibration gate-duration data
and per-qubit resource availability.
"""

from __future__ import annotations

__all__ = ["format_result", "create_time_line_table", "plot_time_line"]

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

try:
    import pandas as pd
except ImportError:
    pd = None

_DEFAULT_DURATIONS = {
    "1q": 30.0,
    "2q": 40.0,
    "measure": 1000.0,
    "barrier": 0.0,
}

_TWO_QUBIT_GATES = {"CNOT", "CX", "CZ", "SWAP", "ISWAP", "ECR", "XX", "YY", "ZZ", "XY"}
_MEASURE_GATES = {"MEASURE", "MEAS", "MEASUREMENT"}


def format_result(
    compiled_prog: Any,
    *,
    backend_info: Any | None = None,
    chip_characterization: Any | None = None,
    gate_durations: dict[str, float] | None = None,
):
    """Format a compiled program into gate layers, qubits, and start times.

    Args:
        compiled_prog: JSON pulse data, OriginIR text, a Circuit-like object,
            or a list of gate dictionaries.
        backend_info: Optional backend metadata. ``extra`` may contain
            ``gate_durations``, ``single_qubit_gate_time``,
            ``two_qubit_gate_time``, or ``measure_time``.
        chip_characterization: Optional calibration object. Its
            ``global_info.single_qubit_gate_time`` and
            ``global_info.two_qubit_gate_time`` are used when present.
        gate_durations: Explicit duration overrides keyed by gate name.

    Returns:
        tuple: ``(gate_layers, qubit_list, time_line)``.
    """
    entries = _normalise_program(compiled_prog)
    durations = _resolve_gate_durations(
        backend_info=backend_info,
        chip_characterization=chip_characterization,
        gate_durations=gate_durations,
    )

    layer_by_start: dict[float, int] = {}
    gate_layers: dict[int, list[tuple[str, int | list[int], float, float]]] = {}
    qubits_seen: set[int] = set()
    start_times: set[float] = set()
    qubit_available_at: dict[int, float] = {}

    for entry in entries:
        gate_name, qubits, angle, explicit_start = _parse_entry(entry)
        if not qubits:
            continue

        duration = _duration_for_gate(gate_name, qubits, durations)
        start_time = (
            float(explicit_start)
            if explicit_start is not None
            else max((qubit_available_at.get(q, 0.0) for q in qubits), default=0.0)
        )
        finish_time = start_time + duration
        for q in qubits:
            qubit_available_at[q] = finish_time
            qubits_seen.add(q)
        start_times.add(start_time)

        if start_time not in layer_by_start:
            layer_by_start[start_time] = len(layer_by_start)
        layer = layer_by_start[start_time]
        gate_layers.setdefault(layer, []).append(
            (gate_name, qubits[0] if len(qubits) == 1 else qubits, angle, _format_time(start_time))
        )

    time_line = [_format_time(t) for t in sorted(start_times)]
    return gate_layers, sorted(qubits_seen), time_line


def create_time_line_table(layer_dict, qubit_list, time_line):
    """Create a pandas DataFrame timeline table."""
    if pd is not None:
        time_line_table = pd.DataFrame(columns=time_line, index=[f"qubit {i}" for i in qubit_list])
    else:
        time_line_table = _SimpleTimelineTable(columns=time_line, index=[f"qubit {i}" for i in qubit_list])

    for gates in layer_dict.values():
        for gate_name, qubit, angle, time in gates:
            label = gate_name if gate_name in _MEASURE_GATES else f"{gate_name} {round(angle, 3)}"
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
):
    """Plot the quantum circuit timeline and save PDF files."""
    format_prog, qubit_list, time_line = format_result(
        compiled_prog,
        backend_info=backend_info,
        chip_characterization=chip_characterization,
        gate_durations=gate_durations,
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


def _normalise_program(compiled_prog: Any) -> list[Any]:
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
        return parsed if isinstance(parsed, list) else [parsed]
    if isinstance(compiled_prog, list):
        return compiled_prog
    return [compiled_prog]


def _originir_to_entries(originir: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
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
        if op == "BARRIER":
            continue
        qubits = qubit if isinstance(qubit, list) else [qubit]
        if op == "MEASURE" and isinstance(qubit, int):
            entries.append({"MEASURE": [qubits]})
        else:
            values: list[Any] = qubits[:]
            if param is not None:
                values.extend(param if isinstance(param, list) else [param])
            entries.append({op: values})
    return entries


def _parse_entry(entry: Any) -> tuple[str, list[int], float, float | None]:
    if not isinstance(entry, dict) or not entry:
        return "UNKNOWN", [], 0.0, None
    gate_name = str(next(iter(entry.keys())))
    params = next(iter(entry.values()))
    params = params if isinstance(params, list) else [params]
    upper = gate_name.upper()

    if upper == "RPHI":
        qubit = int(params[0])
        angle = float(params[1]) if len(params) > 1 else 0.0
        theta = float(params[2]) if len(params) > 2 else 0.0
        start = float(params[3]) if len(params) > 3 and _is_number(params[3]) else None
        if theta == 90.0:
            gate_name = "RPhi90"
        elif theta == 180.0:
            gate_name = "RPhi180"
        return gate_name, [qubit], angle, start

    if upper in _MEASURE_GATES:
        qubit_param = params[0] if params else []
        qubits = [int(q) for q in qubit_param] if isinstance(qubit_param, list) else [int(qubit_param)]
        start = float(params[1]) if len(params) > 1 and _is_number(params[1]) else None
        return "MEASURE", qubits, 0.0, start

    arity = 2 if upper in _TWO_QUBIT_GATES else 1
    qubits = [int(q) for q in params[:arity]]
    start = None
    if len(params) > arity and _is_number(params[-1]):
        maybe_start = float(params[-1])
        if upper in _TWO_QUBIT_GATES or len(params) > arity + 1:
            start = maybe_start
    return gate_name, qubits, 0.0, start


def _resolve_gate_durations(
    *,
    backend_info: Any | None,
    chip_characterization: Any | None,
    gate_durations: dict[str, float] | None,
) -> dict[str, float]:
    durations = dict(_DEFAULT_DURATIONS)

    if backend_info is not None:
        extra = getattr(backend_info, "extra", {}) or {}
        durations.update({k.upper(): float(v) for k, v in extra.get("gate_durations", {}).items()})
        if extra.get("single_qubit_gate_time") is not None:
            durations["1q"] = float(extra["single_qubit_gate_time"])
        if extra.get("two_qubit_gate_time") is not None:
            durations["2q"] = float(extra["two_qubit_gate_time"])
        if extra.get("measure_time") is not None:
            durations["measure"] = float(extra["measure_time"])

    if chip_characterization is not None:
        global_info = getattr(chip_characterization, "global_info", None)
        one_q = getattr(global_info, "single_qubit_gate_time", None)
        two_q = getattr(global_info, "two_qubit_gate_time", None)
        if one_q is not None:
            durations["1q"] = float(one_q)
        if two_q is not None:
            durations["2q"] = float(two_q)

    if gate_durations:
        durations.update({str(k).upper(): float(v) for k, v in gate_durations.items()})

    return durations


def _duration_for_gate(gate_name: str, qubits: list[int], durations: dict[str, float]) -> float:
    upper = gate_name.upper()
    if upper in durations:
        return durations[upper]
    if upper in _MEASURE_GATES:
        return durations["measure"]
    if len(qubits) >= 2 or upper in _TWO_QUBIT_GATES:
        return durations["2q"]
    return durations["1q"]


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float)


def _format_time(value: float) -> int | float:
    return int(value) if float(value).is_integer() else value


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
