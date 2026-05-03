"""Circuit SVG rendering API — /api/circuits/{task_id}/svg."""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from uniqc.backend_adapter.task.store import TaskStore
from uniqc.gateway.db.archive_store import ArchiveStore

router = APIRouter()

_CIRCUIT_KEYS = {
    "source": (
        "circuit_ir",
        "source_circuit_ir",
        "submitted_circuit_ir",
        "originir",
        "origin_ir",
        "qasm",
        "qasm2",
        "openqasm",
        "circuit",
        "source_circuit",
        "submitted_circuit",
    ),
    "compiled": (
        "compiled_circuit_ir",
        "compiled_originir",
        "compiled_origin_ir",
        "compiled_qasm",
        "transpiled_qasm",
        "compiled_circuit",
        "transpiled_circuit",
    ),
    "executed": (
        "executed_circuit_ir",
        "execution_circuit_ir",
        "scheduled_circuit_ir",
        "executed_originir",
        "executed_qasm",
        "executed_circuit",
        "scheduled_circuit",
    ),
}


def _looks_like_circuit(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    upper = text.upper()
    return (
        upper.startswith("QINIT")
        or "OPENQASM" in upper
        or "QREG " in upper
        or "CREG " in upper
        or "MEASURE" in upper
    )


def _find_string_by_keys(data: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if _looks_like_circuit(value):
                return value
        for value in data.values():
            found = _find_string_by_keys(value, keys)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _find_string_by_keys(value, keys)
            if found:
                return found
    return None


def _detect_language(circuit_ir: str, fallback: str = "OriginIR") -> str:
    text = circuit_ir.lstrip().upper()
    if text.startswith("OPENQASM") or "QREG " in text:
        return "OpenQASM"
    return fallback


def _fallback_html(task_id: str, format: str, message: str, circuit_ir: str | None = None) -> HTMLResponse:
    pre = ""
    if circuit_ir:
        pre = f'<pre style="white-space:pre-wrap;margin:0;">{escape(circuit_ir)}</pre>'
    html = f"""
    <div style="font-family: system-ui, -apple-system, Segoe UI, sans-serif; color:#0f172a;">
      <div style="border:1px solid #cbd5e1;border-radius:8px;padding:14px;background:#f8fafc;">
        <strong>Task {escape(task_id)} · {escape(format)}</strong>
        <p style="margin:8px 0 12px;color:#475569;">{escape(message)}</p>
        {pre}
      </div>
    </div>
    """
    return HTMLResponse(content=html)


@router.get("/{task_id}/svg")
def circuit_svg(
    task_id: str,
    format: str = "source",
) -> HTMLResponse:
    """Render a task's quantum circuit as an inline SVG HTML response.

    Query params:
        format: ``source`` (default) | ``compiled`` | ``executed``
            - source:    the originally submitted circuit IR
            - compiled:  the compiled-to-basis circuit (if stored in metadata)
            - executed:  the scheduled execution timeline (if stored)
    """
    store = TaskStore()
    task = store.get(task_id)
    if task is None:
        task = ArchiveStore().get_archived(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    metadata = task.metadata or {}
    result = task.result or {}

    if format == "source":
        circuit_ir = _find_string_by_keys(metadata, _CIRCUIT_KEYS["source"]) or _find_string_by_keys(result, _CIRCUIT_KEYS["source"]) or ""
        language = metadata.get("circuit_language", "OriginIR")
    elif format == "compiled":
        circuit_ir = _find_string_by_keys(metadata, _CIRCUIT_KEYS["compiled"]) or _find_string_by_keys(result, _CIRCUIT_KEYS["compiled"]) or ""
        language = metadata.get("compiled_language", "OriginIR")
        if not circuit_ir:
            source = _find_string_by_keys(metadata, _CIRCUIT_KEYS["source"]) or _find_string_by_keys(result, _CIRCUIT_KEYS["source"])
            return _fallback_html(
                task_id,
                format,
                "Compiled circuit was not stored for this task. Showing source circuit when available.",
                source,
            )
    elif format == "executed":
        circuit_ir = _find_string_by_keys(metadata, _CIRCUIT_KEYS["executed"]) or _find_string_by_keys(result, _CIRCUIT_KEYS["executed"]) or ""
        language = metadata.get("executed_language", "OriginIR")
        if not circuit_ir:
            # Fall back to compiled
            circuit_ir = (
                _find_string_by_keys(metadata, _CIRCUIT_KEYS["compiled"])
                or _find_string_by_keys(result, _CIRCUIT_KEYS["compiled"])
                or _find_string_by_keys(metadata, _CIRCUIT_KEYS["source"])
                or _find_string_by_keys(result, _CIRCUIT_KEYS["source"])
                or ""
            )
            language = metadata.get("compiled_language", "OriginIR")
            if not circuit_ir:
                return _fallback_html(
                    task_id,
                    format,
                    "Executed/compiled circuit was not stored for this task.",
                )
    else:
        raise HTTPException(
            status_code=400,
            detail="format must be one of: source, compiled, executed",
        )

    if not circuit_ir:
        return _fallback_html(
            task_id,
            format,
            "No circuit metadata was stored for this task. Older tasks cannot be reconstructed from results alone; newly submitted tasks are captured automatically.",
        )

    language = _detect_language(circuit_ir, fallback=str(language))

    try:
        from uniqc.visualization.circuit import draw_html
    except ImportError as exc:
        html = f"""
        <div style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace;">
          <p style="color:#64748b;margin:0 0 12px;">
            Circuit visualization dependency is not installed: {escape(str(exc))}
          </p>
          <pre style="white-space:pre-wrap;margin:0;">{escape(circuit_ir)}</pre>
        </div>
        """
        return HTMLResponse(content=html)

    try:
        html = draw_html(
            circuit_ir,
            language=language,
            title=f"[{format.upper()}] {task_id}",
        )
        return HTMLResponse(content=html)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render circuit: {exc}",
        ) from exc
