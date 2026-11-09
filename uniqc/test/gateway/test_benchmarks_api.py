"""Tests for the local benchmark gateway API (real local computation)."""

from __future__ import annotations

import pytest


@pytest.fixture
def client(fastapi_client):
    return fastapi_client


@pytest.mark.requires_cpp
def test_benchmarks_qv_runs_and_reports(client):
    response = client.post("/api/benchmarks/qv", json={"width": 3, "trials": 3, "shots": 200, "seed": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["benchmark"] == "quantum_volume"
    assert payload["passed"] is True
    assert payload["quantum_volume"] == 8
    assert len(payload["trial_results"]) == 3


def test_benchmarks_qv_rejects_out_of_bounds(client):
    for body in ({"width": 1}, {"width": 9}, {"trials": 0}, {"shots": 10}, {"seed": -1}):
        assert client.post("/api/benchmarks/qv", json=body).status_code == 422


@pytest.mark.requires_cpp
def test_benchmarks_throughput_runs_and_reports(client):
    response = client.post(
        "/api/benchmarks/throughput",
        json={"circuits": 20, "qubits": 5, "depth": 3, "shots": 100, "seed": 2},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["benchmark"] == "local_compile_execute_throughput"
    assert payload["timing"]["circuits_per_hour"] > 0
    assert payload["environment"]["cpu_backend"].startswith("uniqc_cpp")


def test_benchmarks_throughput_rejects_unknown_backend(client):
    response = client.post(
        "/api/benchmarks/throughput",
        json={"circuits": 10, "qubits": 4, "depth": 2, "shots": 10, "backend": "originq:WK_C180"},
    )
    assert response.status_code == 422


@pytest.mark.requires_cpp
def test_benchmarks_noise_qram_lookup(client):
    response = client.post(
        "/api/benchmarks/noise-qram",
        json={"case": "lookup", "address": 5, "shots": 200, "seed": 3, "model_seed": 42},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["case"] == "qram_lookup_3layer"
    assert payload["expected_value"] == 2
    assert payload["mitigated_top_outcome"] == "10"
    assert sum(payload["noisy_counts"].values()) == 200
    assert "synthetic" in payload["boundary"]


@pytest.mark.requires_cpp
def test_benchmarks_noise_qram_qpu(client):
    response = client.post(
        "/api/benchmarks/noise-qram",
        json={"case": "qpu", "shots": 200, "seed": 4, "model_seed": 42},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["case"] == "qpu_addressing_3layer_qram"
    assert payload["raw_fidelity"] > 0.6
    assert sum(payload["noisy_counts"].values()) == 200


def test_benchmarks_noise_qram_rejects_bad_case(client):
    response = client.post("/api/benchmarks/noise-qram", json={"case": "grover"})
    assert response.status_code == 422
