"""QuarkStudio / Quafu-SQC backend adapter.

QuarkStudio replaces the deprecated pyquafu client for the BAQIS Quafu-SQC
platform. Its public SDK accepts OpenQASM 2.0 text inside a task dictionary:

    {"chip": "Baihua", "name": "...", "circuit": qasm2, "shots": 1024, ...}

This adapter keeps that SDK boundary intact and exposes the same
``QuantumAdapter`` interface used by the rest of UnifiedQuantum.
"""

from __future__ import annotations

__all__ = ["QuarkAdapter"]

import contextlib
import io
import os
import re
from typing import Any

from uniqc.backend_adapter.backend_info import QubitTopology
from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
    _dry_run_failed,
    _dry_run_success,
)
from uniqc.backend_adapter.task.config import load_quark_config
from uniqc.backend_adapter.task.optional_deps import MissingDependencyError, check_quark, check_quarkcircuit
from uniqc.cli.chip_info import ChipGlobalInfo, SingleQubitData, TwoQubitData, TwoQubitGateData
from uniqc.compile.converter import convert_oir_to_qasm

_DEFAULT_CHIP = "Baihua"
_DEFAULT_TASK_NAME = "UniqcQuantumTask"
_TERMINAL_SUCCESS = {"finished", "success", "succeeded", "done", "completed"}
_TERMINAL_FAILED = {"failed", "failure", "error", "cancelled", "canceled"}
_BACKEND_STATUS_MAP = {
    "online": "available",
    "available": "available",
    "offline": "unavailable",
    "unavailable": "unavailable",
    "maintenance": "maintenance",
    "maintaining": "maintenance",
    "calibrating": "maintenance",
    "calibration": "maintenance",
}


def _normalise_status(value: Any, *, has_counts: bool = False) -> str:
    if has_counts:
        return TASK_STATUS_SUCCESS
    if isinstance(value, dict):
        for key in ("status", "taskStatus", "state"):
            if key in value:
                return _normalise_status(value[key])
        if "count" in value or "counts" in value:
            return TASK_STATUS_SUCCESS
    text = str(value or "").strip().lower()
    if text in _TERMINAL_SUCCESS:
        return TASK_STATUS_SUCCESS
    if text in _TERMINAL_FAILED:
        return TASK_STATUS_FAILED
    return TASK_STATUS_RUNNING


def _counts_from_result(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    counts = result.get("count", result.get("counts"))
    return counts if isinstance(counts, dict) else None


def _task_id(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("tid", "task_id", "taskId", "id"):
            if key in value:
                return str(value[key])
    return str(value)


def _qasm_qubit_count(qasm: str) -> int | None:
    match = re.search(r"\bqreg\s+\w+\[(\d+)\]\s*;", qasm)
    return int(match.group(1)) if match else None


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _seconds_to_nanoseconds(value: Any) -> float | None:
    result = _number(value)
    if result is None:
        return None
    return result * 1_000_000_000 if abs(result) < 1 else result


def _parse_quark_qubit_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def _quark_gate_basis(chip_info: dict[str, Any]) -> tuple[list[str], str]:
    basis = [str(g).strip().lower() for g in chip_info.get("basis_gates") or [] if str(g).strip()]
    two_qubit_basis = str((chip_info.get("global_info") or {}).get("two_qubit_gate_basis") or "").strip().lower()
    if two_qubit_basis and two_qubit_basis not in basis:
        basis.append(two_qubit_basis)
    return basis, two_qubit_basis or "cz"


def _extract_quark_backend_details(chip_info: dict[str, Any]) -> dict[str, Any]:
    """Normalize QuarkStudio ``quarkcircuit`` chip metadata."""
    global_info = chip_info.get("global_info") if isinstance(chip_info.get("global_info"), dict) else {}
    qubits_info = chip_info.get("qubits_info") if isinstance(chip_info.get("qubits_info"), dict) else {}
    couplers_info = chip_info.get("couplers_info") if isinstance(chip_info.get("couplers_info"), dict) else {}
    basis_gates, two_qubit_basis = _quark_gate_basis(chip_info)

    single_qubit_data: list[SingleQubitData] = []
    available_qubits: set[int] = set()
    readout_fidelities: list[float] = []
    for key, qdata in qubits_info.items():
        qid = _parse_quark_qubit_id((qdata or {}).get("index") if isinstance(qdata, dict) else key)
        if qid is None:
            qid = _parse_quark_qubit_id(key)
        if qid is None:
            continue
        available_qubits.add(qid)
        qdata = qdata if isinstance(qdata, dict) else {}
        readout_0 = _number(qdata.get("readout g_fidelity"))
        readout_1 = _number(qdata.get("readout e_fidelity"))
        readout_values = [v for v in (readout_0, readout_1) if v is not None]
        avg_readout = _avg(readout_values)
        if avg_readout is not None:
            readout_fidelities.append(avg_readout)
        single_qubit_data.append(
            SingleQubitData(
                qubit_id=qid,
                t1=_number(qdata.get("T1")),
                t2=_number(qdata.get("T2")),
                single_gate_fidelity=_number(qdata.get("fidelity")),
                readout_fidelity_0=readout_0,
                readout_fidelity_1=readout_1,
                avg_readout_fidelity=avg_readout,
            )
        )

    topology: list[QubitTopology] = []
    two_qubit_data: list[TwoQubitData] = []
    two_qubit_fidelities: list[float] = []
    seen_edges: set[tuple[int, int]] = set()
    for cdata in couplers_info.values():
        if not isinstance(cdata, dict):
            continue
        qubits = cdata.get("qubits_index") or cdata.get("qubits") or cdata.get("qubit")
        if not isinstance(qubits, (list, tuple)) or len(qubits) != 2:
            continue
        u = _parse_quark_qubit_id(qubits[0])
        v = _parse_quark_qubit_id(qubits[1])
        if u is None or v is None or u == v:
            continue
        available_qubits.update((u, v))
        key = tuple(sorted((u, v)))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        topology.append(QubitTopology(u=key[0], v=key[1]))
        fidelity = _number(cdata.get("fidelity"))
        if fidelity is not None and fidelity <= 0:
            fidelity = None
        if fidelity is not None:
            two_qubit_fidelities.append(fidelity)
        two_qubit_data.append(
            TwoQubitData(
                qubit_u=key[0],
                qubit_v=key[1],
                gates=(TwoQubitGateData(gate=two_qubit_basis, fidelity=fidelity),),
            )
        )

    if not available_qubits:
        nqubits = global_info.get("nqubits_available")
        if isinstance(nqubits, int) and nqubits > 0:
            available_qubits.update(range(nqubits))

    single_qubit_gates = tuple(g for g in basis_gates if g != two_qubit_basis)
    two_qubit_gates = (two_qubit_basis,) if two_qubit_basis else ()
    avg_1q = _number(global_info.get("single_qubit_gate_fidelity_average"))
    avg_2q = _number(global_info.get("two_qubit_gate_fidelity_average"))
    return {
        "num_qubits": int(global_info.get("nqubits_available") or len(available_qubits) or 0),
        "topology": [[edge.u, edge.v] for edge in sorted(topology, key=lambda edge: (edge.u, edge.v))],
        "available_qubits": sorted(available_qubits),
        "valid_gates": basis_gates,
        "per_qubit_calibration": [
            item.to_dict() for item in sorted(single_qubit_data, key=lambda item: item.qubit_id)
        ],
        "per_pair_calibration": [
            item.to_dict() for item in sorted(two_qubit_data, key=lambda item: (item.qubit_u, item.qubit_v))
        ],
        "global_info": ChipGlobalInfo(
            single_qubit_gates=single_qubit_gates,
            two_qubit_gates=two_qubit_gates,
            single_qubit_gate_time=_seconds_to_nanoseconds(global_info.get("one_qubit_gate_length")),
            two_qubit_gate_time=_seconds_to_nanoseconds(global_info.get("two_qubit_gate_length")),
        ).to_dict(),
        "calibrated_at": chip_info.get("calibration_time"),
        "avg_1q_fidelity": avg_1q,
        "avg_2q_fidelity": avg_2q if avg_2q is not None else _avg(two_qubit_fidelities),
        "avg_readout_fidelity": _avg(readout_fidelities),
        "coherence_t1": _number(global_info.get("T1_average")),
        "coherence_t2": _number(global_info.get("T2_average")),
    }


def _normalise_backend_status(value: Any) -> str:
    if isinstance(value, int):
        return "available"
    text = str(value or "").strip().lower()
    return _BACKEND_STATUS_MAP.get(text, "unknown" if text else "unknown")


class QuarkAdapter(QuantumAdapter):
    """Adapter for QuarkStudio's Quafu-SQC ``Task`` API."""

    name = "quark"

    def __init__(self, token: str | None = None, task_client: Any | None = None) -> None:
        self._token = token
        self._task_client = task_client
        if self._token is None:
            self._token = os.getenv("QUARK_API_KEY") or os.getenv("QPU_API_TOKEN")
        if self._token is None:
            try:
                self._token = load_quark_config()["api_token"]
            except Exception:
                self._token = None

    def _get_task_client(self) -> Any:
        if self._task_client is None:
            if not check_quark():
                raise MissingDependencyError("quarkstudio", "quark")
            if not self._token:
                raise ImportError(
                    "QuarkStudio config not found. "
                    "Run `uniqc config set quark.QUARK_API_KEY <TOKEN>` or set QUARK_API_KEY."
                )
            from quark import Task

            self._task_client = Task(self._token)
        return self._task_client

    def is_available(self) -> bool:
        """Return True when the SDK is importable and a token is configured."""
        return check_quark() and bool(self._token)

    def translate_circuit(self, originir: str) -> str:
        """Translate OriginIR text to OpenQASM 2.0."""
        qasm = convert_oir_to_qasm(originir)
        # Validate with Qiskit when available because QuarkStudio delegates this
        # payload to OpenQASM2-capable tooling server-side.
        try:
            from qiskit import qasm2

            qasm2.loads(qasm)
        except ImportError:
            pass
        return qasm

    def _task_payload(self, circuit: Any, *, shots: int, **kwargs: Any) -> dict[str, Any]:
        qasm = str(circuit)
        task: dict[str, Any] = {
            "chip": kwargs.get("chip_id") or kwargs.get("backend_name") or kwargs.get("chip") or _DEFAULT_CHIP,
            "name": kwargs.get("task_name") or kwargs.get("name") or _DEFAULT_TASK_NAME,
            "circuit": qasm,
            "shots": int(shots),
            "compile": bool(kwargs.get("compile", True)),
        }

        options = dict(kwargs.get("options") or {})
        for key in ("compiler", "correct", "open_dd", "target_qubits"):
            if key in kwargs:
                options[key] = kwargs[key]
        if "clientip" not in options and os.getenv("CLIENT_REAL_IP"):
            options["clientip"] = os.getenv("CLIENT_REAL_IP", "")
        if options:
            task["options"] = options
        return task

    def submit(self, circuit: Any, *, shots: int = 1024, **kwargs: Any) -> str:
        """Submit a single OpenQASM 2.0 circuit to QuarkStudio."""
        task = self._task_payload(circuit, shots=shots, **kwargs)
        tid = self._get_task_client().run(task, repeat=max(1, int(shots) // 1024))
        return _task_id(tid)

    def submit_batch(self, circuits: list[Any], *, shots: int = 1024, **kwargs: Any) -> list[str]:
        """Submit circuits one-by-one because the public SDK exposes single-task run()."""
        return [self.submit(circuit, shots=shots, **kwargs) for circuit in circuits]

    def query(self, taskid: str) -> dict[str, Any]:
        """Query task status and return normalised status/result fields."""
        client = self._get_task_client()
        tid = int(taskid) if str(taskid).isdigit() else taskid
        result = client.result(tid)
        counts = _counts_from_result(result)
        if counts is not None:
            return {
                "status": _normalise_status(result, has_counts=True),
                "result": {
                    "counts": counts,
                    "raw_result": result,
                },
            }

        status_payload = client.status(tid)
        status = _normalise_status(status_payload)
        response: dict[str, Any] = {"status": status}
        if status != TASK_STATUS_RUNNING:
            response["result"] = result if result else status_payload
        return response

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        """Query multiple task IDs and merge their statuses."""
        results = [self.query(taskid) for taskid in taskids]
        statuses = [r.get("status", TASK_STATUS_RUNNING) for r in results]
        if TASK_STATUS_FAILED in statuses:
            status = TASK_STATUS_FAILED
        elif TASK_STATUS_RUNNING in statuses:
            status = TASK_STATUS_RUNNING
        else:
            status = TASK_STATUS_SUCCESS
        return {"status": status, "result": [r.get("result") for r in results]}

    def list_backends(self) -> list[dict[str, Any]]:
        """Return backend status entries from ``Task.status()``."""
        raw = self._get_task_client().status()
        if isinstance(raw, dict):
            return [self._backend_entry(str(name), queue) for name, queue in raw.items()]
        if isinstance(raw, list):
            return [
                self._backend_entry(
                    str(entry.get("name", "")),
                    entry.get("task_in_queue", entry.get("queue", 0)),
                    entry,
                )
                if isinstance(entry, dict) else entry
                for entry in raw
            ]
        return []

    def get_backend_info(self, chip: str = _DEFAULT_CHIP) -> dict[str, Any]:
        """Fetch detailed backend information when quarkcircuit is installed."""
        info = self._load_chip_basic_info(chip)
        return info if isinstance(info, dict) else {}

    def _backend_entry(self, name: str, queue: Any, base: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = dict(base or {})
        entry.update(
            {
                "name": name,
                "status": _normalise_backend_status(entry.get("status", queue)),
                "task_in_queue": queue,
            }
        )
        chip_info = self._load_chip_basic_info(name)
        if isinstance(chip_info, dict) and chip_info.get("qubits_info"):
            entry.update(_extract_quark_backend_details(chip_info))
            entry["backend_info_available"] = True
        elif isinstance(chip_info, dict):
            entry["backend_info_available"] = False
        return entry

    def _load_chip_basic_info(self, chip: str) -> dict[str, Any] | None:
        if not check_quarkcircuit():
            return None
        try:
            from quark.circuit.backend import load_chip_basic_info

            with contextlib.redirect_stdout(io.StringIO()):
                info = load_chip_basic_info(chip)
            return info if isinstance(info, dict) else None
        except Exception:
            return None

    def dry_run(self, originir: str, *, shots: int = 1024, **kwargs: Any) -> DryRunResult:
        """Validate OriginIR -> OpenQASM 2.0 locally without network calls."""
        backend_name = kwargs.get("chip_id") or kwargs.get("backend_name") or kwargs.get("chip") or _DEFAULT_CHIP
        try:
            qasm = self.translate_circuit(originir)
        except Exception as exc:
            return _dry_run_failed(
                str(exc),
                details=f"Failed to translate OriginIR to OpenQASM 2.0 for QuarkStudio: {exc}",
                backend_name=backend_name,
            )

        warnings: list[str] = []
        if shots <= 0:
            return _dry_run_failed(
                "shots must be positive",
                details=f"Invalid shots value for QuarkStudio: {shots}",
                backend_name=backend_name,
            )
        if shots % 1024 != 0:
            warnings.append("QuarkStudio documentation recommends shots as an integer multiple of 1024.")

        return _dry_run_success(
            "OriginIR translated to OpenQASM 2.0 and is structurally valid for QuarkStudio submission.",
            backend_name=backend_name,
            circuit_qubits=_qasm_qubit_count(qasm),
            supported_gates=(
                "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg",
                "rx", "ry", "rz", "u1", "u2", "u3", "cx", "cz", "swap",
                "ccx", "measure", "barrier",
            ),
            warnings=tuple(warnings),
        )
