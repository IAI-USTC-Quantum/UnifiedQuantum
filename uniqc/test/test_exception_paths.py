from __future__ import annotations

import pytest


def test_malformed_ibm_properties_warn_and_keep_best_effort_result():
    from uniqc.backend_adapter.task.adapters.ibm_adapter import _compute_ibm_fidelity

    class MalformedProperties:
        def gate_error(self, _gate, _qubits):
            return "not-a-number"

        def readout_error(self, _qubit):
            raise ValueError("invalid readout calibration")

    class MissingTargetOperations:
        def __getitem__(self, _gate):
            raise KeyError

    class MalformedQubitProperties:
        t1 = "invalid-t1"
        t2 = None

    class Backend:
        target = MissingTargetOperations()
        num_qubits = 1
        coupling_map = []

        def properties(self, refresh=False):
            return MalformedProperties()

        def qubit_properties(self, _qubit):
            return MalformedQubitProperties()

    with pytest.warns(RuntimeWarning) as recorded:
        result = _compute_ibm_fidelity(Backend())

    messages = [str(item.message) for item in recorded]
    assert any("properties sx(0,) error value" in message for message in messages)
    assert any("qubit 0 coherence" in message for message in messages)
    assert any("qubit 0 readout error" in message for message in messages)
    assert result == {
        "avg_1q_fidelity": None,
        "avg_2q_fidelity": None,
        "avg_readout_fidelity": None,
        "coherence_t1": None,
        "coherence_t2": None,
    }


def test_ambiguous_circuit_text_reports_both_parser_diagnostics():
    from uniqc.circuit_builder.normalize import normalize_circuit_input

    with pytest.raises(ValueError) as exc_info:
        normalize_circuit_input("H q[0]")

    message = str(exc_info.value)
    assert "both parsers rejected" in message
    assert "OriginIR:" in message
    assert "OpenQASM 2.0:" in message
    assert "QINIT" in message


def test_explicit_qasm_failure_preserves_parser_diagnostic():
    from uniqc.circuit_builder.normalize import normalize_circuit_input

    with pytest.raises(ValueError, match="Failed to parse circuit input as OpenQASM 2.0") as exc_info:
        normalize_circuit_input("OPENQASM 2.0;\ninvalid;")

    assert "Register is empty" in str(exc_info.value)


def test_backend_validation_cache_read_failure_warns_and_returns_none(monkeypatch):
    from uniqc.backend_adapter import backend_cache
    from uniqc.backend_adapter.task_manager import _resolve_backend_info_for_validation

    def fail_cache_read(_platform):
        raise OSError("cache is unreadable")

    monkeypatch.setattr(backend_cache, "get_cached_backends", fail_cache_read)

    with pytest.warns(RuntimeWarning, match="originq:WK_C180.*cache is unreadable"):
        result = _resolve_backend_info_for_validation("originq:WK_C180", {})

    assert result is None


def test_backend_validation_freshness_failure_marks_cached_entry_stale(monkeypatch):
    from uniqc.backend_adapter import backend_cache
    from uniqc.backend_adapter.backend_info import BackendInfo, Platform
    from uniqc.backend_adapter.task_manager import _resolve_backend_info_for_validation

    cached = BackendInfo(platform=Platform.IBM, name="ibm_test")
    monkeypatch.setattr(backend_cache, "get_cached_backends", lambda _platform: [cached])
    monkeypatch.setattr(backend_cache, "is_stale", lambda _platform: (_ for _ in ()).throw(ValueError("bad timestamp")))

    with pytest.warns(RuntimeWarning, match="cache freshness.*bad timestamp"):
        result = _resolve_backend_info_for_validation("ibm:ibm_test", {})

    assert result is not None
    assert result.extra["_uniqc_topology_stale"] is True
