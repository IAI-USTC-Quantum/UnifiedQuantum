"""Regression tests for explicit ``n_qubits`` handling in result normalizers.

Covers H-2: ``normalize_originq`` previously inferred ``n_qubits`` from
``max(outcome).bit_length()`` which silently truncates leading-zero qubits
when the highest qubit always reads 0 in a sparse distribution.
"""

from __future__ import annotations

import warnings
from typing import Any

import pytest

from uniqc.backend_adapter.task.normalizers import normalize_originq
from uniqc.circuit_builder import Circuit

# Sparse 4-qubit-circuit-style counts: max outcome 7 only uses 3 bits, so
# inferring width via bit_length would yield 3 instead of the true 4.
SPARSE_COUNTS = {0: 100, 1: 200, 2: 300, 7: 50}


def test_explicit_n_qubits_pads_sparse_counts() -> None:
    """Test A: explicit n_qubits=4 produces width-4 bitstrings for sparse outcomes."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning would fail the test
        result = normalize_originq(
            dict(SPARSE_COUNTS),
            task_id="task-A",
            n_qubits=4,
        )

    keys = list(result.counts.keys())
    assert keys, "expected non-empty counts"
    assert all(len(k) == 4 for k in keys), (
        f"all bitstrings must be padded to width 4, got {keys}"
    )
    # Outcome 7 -> '0111' under width 4 (rightmost bit = qubit 0)
    assert "0111" in result.counts
    assert result.counts["0111"] == 50
    assert result.counts["0000"] == 100


def test_missing_n_qubits_warns_and_uses_bit_length_fallback() -> None:
    """Test B: omitting n_qubits emits UserWarning and falls back to bit_length()."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = normalize_originq(
            dict(SPARSE_COUNTS),
            task_id="task-B",
        )

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert user_warnings, "expected a UserWarning when n_qubits is omitted"
    assert "n_qubits" in str(user_warnings[0].message)

    keys = list(result.counts.keys())
    assert keys
    # Legacy behavior: max outcome (7) has bit_length 3
    assert all(len(k) == 3 for k in keys), (
        f"legacy fallback should yield width-3 keys, got {keys}"
    )
    assert "111" in result.counts


def test_explicit_n_qubits_with_probability_form() -> None:
    """Probability-form input also honors explicit n_qubits."""
    raw = {"key": ["0x0", "0x1", "0x7"], "value": [0.5, 0.3, 0.2]}
    result = normalize_originq(raw, task_id="task-P", n_qubits=4)
    keys = list(result.probabilities.keys())
    assert all(len(k) == 4 for k in keys), keys
    assert result.probabilities["0000"] == pytest.approx(0.5)
    assert result.probabilities["0111"] == pytest.approx(0.2)


def test_hex_string_counts_keys_are_normalized() -> None:
    """Counts dicts may carry hex string keys; widths must still pad to n_qubits."""
    raw = {"0x0": 100, "0x1": 200, "0x7": 50}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = normalize_originq(raw, task_id="task-H", n_qubits=4)
    keys = list(result.counts.keys())
    assert all(len(k) == 4 for k in keys), keys
    assert result.counts["0111"] == 50


class _MockOriginQAdapter:
    """Minimal adapter stub returning a sparse OriginQ-style raw dict.

    The stub's ``submit`` returns a fixed task id and ``query`` returns the
    sparse counts dict. End-to-end test of the normalizer integration
    contract: the caller is responsible for passing ``circuit.qubit_num``.
    """

    name = "originq:mock"

    def __init__(self, raw_payload: dict[Any, int]) -> None:
        self._payload = raw_payload
        self.last_n_qubits: int | None = None

    def submit(self, circuit_ir: str, *, shots: int = 1000) -> str:
        return "mock-task-1"

    def query(self, task_id: str) -> dict[str, Any]:
        return {"status": "success", "result": dict(self._payload)}


def _submit_and_normalize(circuit: Circuit, adapter: _MockOriginQAdapter):
    """Reference caller demonstrating the required integration contract.

    Real adapters / task_manager must pass ``circuit.qubit_num`` so that
    sparse outcomes preserve the high-zero qubits.
    """
    task_id = adapter.submit(circuit.originir, shots=1000)
    raw = adapter.query(task_id)
    assert raw["status"] == "success"
    adapter.last_n_qubits = circuit.qubit_num
    return normalize_originq(
        raw["result"],
        task_id=task_id,
        n_qubits=circuit.qubit_num,
    )


def test_end_to_end_caller_passes_circuit_qubit_num() -> None:
    """Test C: end-to-end mock — caller propagates ``circuit.qubit_num``.

    Builds a 4-qubit circuit (only the low 3 qubits get touched, so the
    raw OriginQ outcomes are sparse), submits via a mock adapter, and
    verifies the resulting UnifiedResult preserves the full 4-qubit
    width that the circuit was built with.
    """
    c = Circuit(4)
    c.add_gate("H", qubits=[0])
    c.add_gate("X", qubits=[1])
    c.add_gate("X", qubits=[2])
    c.measure(0)
    c.measure(1)
    c.measure(2)
    c.measure(3)

    assert c.qubit_num == 4

    adapter = _MockOriginQAdapter(SPARSE_COUNTS)

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # caller must NOT trigger the fallback warning
        unified = _submit_and_normalize(c, adapter)

    assert adapter.last_n_qubits == 4
    keys = list(unified.counts.keys())
    assert all(len(k) == 4 for k in keys), keys
    assert unified.counts["0000"] == 100
    assert unified.counts["0111"] == 50
    assert unified.platform == "originq"
