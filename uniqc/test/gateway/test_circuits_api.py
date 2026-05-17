"""Tests for ``uniqc.gateway.api.circuits`` — circuit SVG rendering endpoint."""

from __future__ import annotations

from uniqc.backend_adapter.task.store import TaskInfo, TaskStatus, TaskStore
from uniqc.gateway.api import circuits as circuits_api
from uniqc.gateway.db.archive_store import ArchiveStore

BELL_IR = """QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
"""

COMPILED_IR = """QINIT 2
CREG 2
RX q[0], 1.5707963
CNOT q[0], q[1]
MEASURE q[0], c[0]
"""


def _save_task_with_circuit(task_id: str, *, metadata: dict | None = None) -> None:
    TaskStore().save(
        TaskInfo(
            task_id=task_id,
            backend="dummy:local:simulator",
            status=TaskStatus.SUCCESS,
            shots=100,
            result={"00": 50, "11": 50},
            metadata=metadata or {"circuit_ir": BELL_IR},
        )
    )


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_looks_like_circuit_detects_originir():
    assert circuits_api._looks_like_circuit("QINIT 2\nH q[0]")
    assert circuits_api._looks_like_circuit("OPENQASM 2.0;\nqreg q[2];")
    assert not circuits_api._looks_like_circuit("")
    assert not circuits_api._looks_like_circuit(None)
    assert not circuits_api._looks_like_circuit({"key": "value"})


def test_find_string_by_keys_walks_nested_dicts():
    data = {"metadata": {"nested": {"circuit_ir": BELL_IR}}}
    found = circuits_api._find_string_by_keys(data, ("circuit_ir",))
    assert found == BELL_IR


def test_find_string_by_keys_walks_lists():
    data = {"items": [{"qasm": "OPENQASM 2.0; qreg q[1];"}]}
    found = circuits_api._find_string_by_keys(data, ("qasm",))
    assert found is not None


def test_find_string_by_keys_missing_returns_none():
    assert circuits_api._find_string_by_keys({"foo": "bar"}, ("circuit_ir",)) is None


def test_detect_language_originir():
    assert circuits_api._detect_language("QINIT 2\nH q[0]") == "OriginIR"


def test_detect_language_openqasm():
    assert circuits_api._detect_language("OPENQASM 2.0;\nqreg q[2];") == "OpenQASM"


def test_detect_language_fallback():
    assert circuits_api._detect_language("not a circuit", fallback="OriginIR") == "OriginIR"


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


def test_circuit_svg_source_renders(fastapi_client, isolated_task_db):
    _save_task_with_circuit("t1")
    r = fastapi_client.get("/api/circuits/t1/svg?format=source")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")


def test_circuit_svg_missing_task_returns_404(fastapi_client, isolated_task_db):
    r = fastapi_client.get("/api/circuits/ghost/svg")
    assert r.status_code == 404


def test_circuit_svg_invalid_format(fastapi_client, isolated_task_db):
    _save_task_with_circuit("t1")
    r = fastapi_client.get("/api/circuits/t1/svg?format=garbage")
    assert r.status_code == 400


def test_circuit_svg_compiled_fallback_when_missing(fastapi_client, isolated_task_db):
    # No compiled IR stored → fallback HTML with source shown
    _save_task_with_circuit("t2", metadata={"circuit_ir": BELL_IR})
    r = fastapi_client.get("/api/circuits/t2/svg?format=compiled")
    assert r.status_code == 200
    body = r.text
    # Should mention "Compiled" or show the source fallback message
    assert "Compiled" in body or "source" in body.lower()


def test_circuit_svg_compiled_uses_stored_ir(fastapi_client, isolated_task_db):
    _save_task_with_circuit(
        "t3",
        metadata={"circuit_ir": BELL_IR, "compiled_circuit_ir": COMPILED_IR},
    )
    r = fastapi_client.get("/api/circuits/t3/svg?format=compiled")
    assert r.status_code == 200


def test_circuit_svg_executed_falls_back_to_compiled(fastapi_client, isolated_task_db):
    _save_task_with_circuit(
        "t4",
        metadata={"circuit_ir": BELL_IR, "compiled_circuit_ir": COMPILED_IR},
    )
    r = fastapi_client.get("/api/circuits/t4/svg?format=executed")
    assert r.status_code == 200


def test_circuit_svg_no_circuit_stored(fastapi_client, isolated_task_db):
    TaskStore().save(
        TaskInfo(
            task_id="empty",
            backend="dummy:local:simulator",
            status=TaskStatus.SUCCESS,
            shots=100,
            result={"00": 1},
            metadata={},
        )
    )
    r = fastapi_client.get("/api/circuits/empty/svg")
    assert r.status_code == 200
    assert "No circuit metadata" in r.text or "fallback" in r.text.lower() or "stored" in r.text.lower()


def test_circuit_svg_archived_task_lookup(fastapi_client, isolated_task_db):
    _save_task_with_circuit("arch1")
    ArchiveStore().archive_task("arch1")
    # Live task is gone — endpoint must consult archive
    r = fastapi_client.get("/api/circuits/arch1/svg")
    assert r.status_code == 200
