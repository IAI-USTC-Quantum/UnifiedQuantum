from __future__ import annotations

import pytest


def _sample_chip_info():
    return {
        "basis_gates": ["h", "rx", "ry", "rz", "cz"],
        "calibration_time": "2026-05-03 21:12:46",
        "global_info": {
            "one_qubit_gate_length": 8.4e-08,
            "two_qubit_gate_length": 2.1e-07,
            "two_qubit_gate_basis": "CZ",
            "nqubits_available": 3,
            "T1_average": 72.5,
            "T2_average": 26.25,
            "single_qubit_gate_fidelity_average": 0.997,
            "two_qubit_gate_fidelity_average": 0.975,
        },
        "qubits_info": {
            "Q0": {
                "index": 0,
                "T1": 69.45,
                "T2": 12.319,
                "fidelity": 0.999,
                "readout g_fidelity": 0.974,
                "readout e_fidelity": 0.94,
            },
            "Q1": {
                "index": 1,
                "T1": 86.015,
                "T2": 7.041,
                "fidelity": 0.994,
                "readout g_fidelity": 0.728,
                "readout e_fidelity": 0.928,
            },
            "Q2": {
                "index": 2,
                "T1": 80.0,
                "T2": 19.5,
                "fidelity": 0.998,
                "readout g_fidelity": 0.95,
                "readout e_fidelity": 0.96,
            },
        },
        "couplers_info": {
            "C0": {"index": 0, "fidelity": 0.0, "qubits_index": [0, 1]},
            "C1": {"index": 1, "fidelity": 0.986, "qubits_index": [1, 2]},
        },
    }


def test_quark_chip_info_extracts_topology_and_gate_data():
    from uniqc.backend_adapter.task.adapters.quark_adapter import _extract_quark_backend_details

    details = _extract_quark_backend_details(_sample_chip_info())

    assert details["num_qubits"] == 3
    assert details["topology"] == [[0, 1], [1, 2]]
    assert details["available_qubits"] == [0, 1, 2]
    assert details["valid_gates"] == ["h", "rx", "ry", "rz", "cz"]
    assert details["avg_1q_fidelity"] == pytest.approx(0.997)
    assert details["avg_2q_fidelity"] == pytest.approx(0.975)
    assert details["coherence_t1"] == pytest.approx(72.5)
    assert details["coherence_t2"] == pytest.approx(26.25)
    assert details["global_info"]["two_qubit_gates"] == ["cz"]
    assert details["global_info"]["single_qubit_gate_time"] == pytest.approx(84.0)
    assert details["global_info"]["two_qubit_gate_time"] == pytest.approx(210.0)

    pair_data = {
        (item["qubit_u"], item["qubit_v"]): item["gates"][0]["fidelity"]
        for item in details["per_pair_calibration"]
    }
    assert pair_data[(0, 1)] is None
    assert pair_data[(1, 2)] == pytest.approx(0.986)


def test_quark_backend_summary_uses_backend_cache_topology_and_gates():
    from uniqc.backend_adapter.backend_registry import _normalise_quark
    from uniqc.backend_adapter.task.adapters.quark_adapter import _extract_quark_backend_details
    from uniqc.gateway.api.backends import _backend_summary

    raw = [
        {
            "name": "Baihua",
            "status": "available",
            "task_in_queue": 0,
            **_extract_quark_backend_details(_sample_chip_info()),
        }
    ]

    backend = _normalise_quark(raw)[0]
    summary = _backend_summary(backend, chip_meta={})

    assert summary["topology"]["has_connectivity"] is True
    assert [node["id"] for node in summary["topology"]["nodes"]] == [0, 1, 2]
    assert "cz" in summary["supported_gates"]
    edge_fids = {
        (edge["u"], edge["v"]): edge["fidelity"]
        for edge in summary["topology"]["edges"]
    }
    assert edge_fids[(0, 1)] is None
    assert edge_fids[(1, 2)] == pytest.approx(0.986)
    assert summary["calibration"]["available"] is True
    assert summary["calibration"]["calibrated_at"] == "2026-05-03 21:12:46"
