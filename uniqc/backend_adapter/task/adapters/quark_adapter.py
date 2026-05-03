"""QuarkStudio / Quafu-SQC backend adapter.

QuarkStudio replaces the deprecated pyquafu client for the BAQIS Quafu-SQC
platform. Its public SDK accepts OpenQASM 2.0 text inside a task dictionary:

    {"chip": "Baihua", "name": "...", "circuit": qasm2, "shots": 1024, ...}

This adapter keeps that SDK boundary intact and exposes the same
``QuantumAdapter`` interface used by the rest of UnifiedQuantum.
"""

from __future__ import annotations

__all__ = ["QuarkAdapter"]

import os
from typing import Any

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
from uniqc.backend_adapter.task.optional_deps import MissingDependencyError, check_quark
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
    import re

    match = re.search(r"\bqreg\s+\w+\[(\d+)\]\s*;", qasm)
    return int(match.group(1)) if match else None


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
            return [
                {
                    "name": str(name),
                    "status": _normalise_backend_status(queue),
                    "task_in_queue": queue,
                }
                for name, queue in raw.items()
            ]
        if isinstance(raw, list):
            return raw
        return []

    def get_backend_info(self, chip: str = _DEFAULT_CHIP) -> dict[str, Any]:
        """Fetch detailed backend information when quarkcircuit is installed."""
        info = self._get_task_client().backend(chip)
        return info if isinstance(info, dict) else {}

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
