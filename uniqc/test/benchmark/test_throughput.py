"""Tests for the local compile/execute throughput benchmark."""

from __future__ import annotations

import json

import pytest

from uniqc.benchmark.throughput import build_random_nisq_circuit, run_throughput_benchmark


def test_circuit_generator_is_seed_deterministic():
    a = build_random_nisq_circuit(4, 3, seed=21).originir
    b = build_random_nisq_circuit(4, 3, seed=21).originir
    c = build_random_nisq_circuit(4, 3, seed=22).originir
    assert a == b
    assert a != c


def test_circuit_generator_input_validation():
    with pytest.raises(ValueError, match="n_qubits"):
        build_random_nisq_circuit(0, 3, seed=1)
    with pytest.raises(ValueError, match="depth"):
        build_random_nisq_circuit(4, 0, seed=1)


def test_circuit_generator_filters_out_of_range_topology_edges():
    from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser

    circuit = build_random_nisq_circuit(4, 3, seed=5, entangler_edges=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
    parser = OriginIR_BaseParser()
    parser.parse(circuit.originir)
    assert parser.n_qubit == 4
    for opcode in parser.program_body:
        operation, qubits = opcode[0], opcode[1]
        if isinstance(qubits, list) and len(qubits) == 2:
            assert all(int(q) < 4 for q in qubits), (operation, qubits)


@pytest.mark.requires_cpp
def test_benchmark_runs_and_reports(tmp_path):
    result = run_throughput_benchmark(circuits=20, n_qubits=5, depth=3, shots=100, seed=3)
    assert result.circuits == 20
    assert result.total_seconds > 0
    assert result.circuits_per_hour > 0
    assert result.compile_circuits_per_hour > 0
    assert result.execute_circuits_per_hour > 0
    payload = result.to_json_dict()
    json.dumps(payload)  # must be JSON-serializable
    assert payload["input_set"]["shots_per_circuit"] == 100
    assert payload["environment"]["cpu_backend"].startswith("uniqc_cpp")
    assert payload["benchmark"] == "local_compile_execute_throughput"


def test_benchmark_rejects_mps_backend():
    with pytest.raises(ValueError, match="statevector"):
        run_throughput_benchmark(
            circuits=5, n_qubits=4, depth=2, shots=10, seed=1, backend_id="dummy:local:mps-linear-4"
        )


def test_benchmark_input_validation():
    with pytest.raises(ValueError, match="circuits"):
        run_throughput_benchmark(circuits=0, n_qubits=4, depth=2, shots=10)
    with pytest.raises(ValueError, match="shots"):
        run_throughput_benchmark(circuits=5, n_qubits=4, depth=2, shots=0)


@pytest.mark.requires_cpp
def test_benchmark_virtual_line_backend_topology(tmp_path):
    """A topology-constrained fixture must run and record its canonical id."""
    result = run_throughput_benchmark(
        circuits=10, n_qubits=4, depth=3, shots=50, seed=9, backend_id="dummy:local:virtual-line-5"
    )
    assert result.backend_id == "dummy:local:virtual-line-5"
    assert result.circuits_per_hour > 0
