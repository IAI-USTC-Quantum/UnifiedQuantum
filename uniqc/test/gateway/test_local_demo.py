"""Real local product presets; compare against independent closed-form results."""

from __future__ import annotations

import math

import pytest

from uniqc.gateway.demo import DemoRequest, run_demo


@pytest.mark.parametrize("case", ["ghz", "w", "ramsey"])
@pytest.mark.parametrize("qubits", [2, 4, 8])
def test_actual_native_demo_matches_analytic_state_probabilities(case, qubits):
    result = run_demo(DemoRequest(case=case, qubits=qubits, phase=0.73))
    assert abs(result["probability_sum"] - 1) < 1e-10
    assert result["max_probability_error"] < 1e-10
    for bits, probability in result["probabilities"].items():
        assert len(bits) == qubits
        ones = bits.count("1")
        if case == "ghz":
            assert bits in ("0" * qubits, "1" * qubits)
            assert abs(probability - 0.5) < 1e-10
        elif case == "w":
            assert ones == 1
            assert abs(probability - 1 / qubits) < 1e-10
        else:
            one = math.sin(0.73 / 2) ** 2
            assert abs(probability - one ** ones * (1 - one) ** (qubits - ones)) < 1e-10


def test_real_http_demo_and_validation(fastapi_client):
    response = fastapi_client.post("/api/demo/simulate", json={"case": "w", "qubits": 3})
    assert response.status_code == 200
    assert response.json()["max_probability_error"] < 1e-10
    for body in ({"qubits": 9}, {"qubits": True}, {"case": "arbitrary"}, {"phase": 100}):
        assert fastapi_client.post("/api/demo/simulate", json=body).status_code == 422
