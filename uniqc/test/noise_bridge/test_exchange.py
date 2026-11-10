"""Tests for the noise-model exchange importer (consumer side)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from uniqc.noise_bridge import (
    SCHEMA,
    ExchangeModelError,
    ImportedNoiseModel,
    build_synthetic_model,
    load_noise_model,
    write_synthetic_model,
)

# Optional externally supplied exchange record; no sibling checkout is required.
NLEARN_SMOKE = Path(os.environ.get("UNIQC_NOISE_EXCHANGE_FIXTURE", "__external_fixture_not_configured__"))


@pytest.fixture()
def synthetic_model_path(tmp_path):
    return write_synthetic_model(tmp_path / "model.json", num_qubits=5, seed=42)


@pytest.fixture()
def synthetic_model(synthetic_model_path):
    return load_noise_model(synthetic_model_path)


class TestSyntheticExchange:
    def test_roundtrip(self, synthetic_model_path, synthetic_model):
        assert synthetic_model.num_qubits == 5
        assert synthetic_model.physical_chain == [0, 1, 2, 3, 4]
        assert synthetic_model.local_edges == [(0, 1), (1, 2), (2, 3), (3, 4)]
        assert synthetic_model.data_class == "synthetic"
        assert synthetic_model.model_sha256

    def test_payload_is_valid_json_and_declares_synthetic(self, synthetic_model_path):
        payload = json.loads(synthetic_model_path.read_text(encoding="utf-8"))
        assert payload["schema"] == SCHEMA
        assert payload["data_class"] == "synthetic"
        assert payload["new_hardware_run"] is False

    def test_error_loader_wiring(self, synthetic_model):
        loader = synthetic_model.error_loader()
        keys = set(loader.gate_specific_error)
        assert keys == {(("RPhi"), (i,)) for i in range(5)} | {("CZ", (i, i + 1)) for i in range(4)}
        first_1q = loader.gate_specific_error[("RPhi", (0,))][0]
        binding = synthetic_model.payload["consumer_bindings"]["uniqc.noisy_simulator.v1"]
        expected = binding["gate_specific_errors"][0]["error"]["arguments"]
        assert [first_1q.p_x, first_1q.p_y, first_1q.p_z] == [float(v) for v in expected]

    def test_readout_error_wiring(self, synthetic_model):
        readout = synthetic_model.readout_error()
        assert set(readout) == {0, 1, 2, 3, 4}
        for rates in readout.values():
            assert len(rates) == 2
            assert all(0.0 <= r <= 1.0 for r in rates)

    def test_edge_flip_entries_present(self, synthetic_model):
        entries = synthetic_model.edge_flip_entries()
        assert len(entries) == 1
        assert entries[0]["outcome_xor_mask"] == (1 << 3) | (1 << 4)

    def test_simulate_counts_sums_to_shots(self, synthetic_model):
        from uniqc.noise_bridge.qram_cases import QRAM_CASE_DATA, build_qram_lookup_circuit

        circuit = build_qram_lookup_circuit(1)
        counts = synthetic_model.simulate_counts(
            circuit, shots=200, seed=7, qram_data={"qram_case": dict(enumerate(QRAM_CASE_DATA))}
        )
        assert sum(counts.values()) == 200
        assert all(set(key) <= {"0", "1"} and len(key) == 2 for key in counts)

    def test_simulate_counts_seed_deterministic(self, synthetic_model):
        from uniqc.noise_bridge.qram_cases import QRAM_CASE_DATA, build_qram_lookup_circuit

        circuit = build_qram_lookup_circuit(2)
        kwargs = dict(shots=100, qram_data={"qram_case": dict(enumerate(QRAM_CASE_DATA))})
        assert synthetic_model.simulate_counts(circuit, seed=5, **kwargs) == synthetic_model.simulate_counts(
            circuit, seed=5, **kwargs
        )


class TestValidation:
    def test_tampered_file_rejected(self, synthetic_model_path):
        payload = json.loads(synthetic_model_path.read_text(encoding="utf-8"))
        payload["channels"]["readout"][0]["p01"] = 0.99
        tampered = synthetic_model_path.parent / "tampered.json"
        tampered.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ExchangeModelError, match="model_sha256"):
            load_noise_model(tampered)

    def test_wrong_schema_rejected(self, synthetic_model_path):
        payload = json.loads(synthetic_model_path.read_text(encoding="utf-8"))
        payload["schema"] = "something.else.v9"
        other = synthetic_model_path.parent / "wrong-schema.json"
        other.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ExchangeModelError, match="schema"):
            load_noise_model(other)

    def test_hardware_run_flag_enforced(self):
        import hashlib

        payload = build_synthetic_model(num_qubits=3, seed=1)
        payload["new_hardware_run"] = True
        body = {k: v for k, v in payload.items() if k != "model_sha256"}
        payload["model_sha256"] = hashlib.sha256(
            json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with pytest.raises(ExchangeModelError, match="new_hardware_run"):
            from uniqc.noise_bridge.exchange import validate_exchange_payload

            validate_exchange_payload(payload)

    def test_corrupt_json_rejected(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(ExchangeModelError, match="cannot read"):
            load_noise_model(bad)

    def test_missing_binding_channel_rejected(self):
        import hashlib

        from uniqc.noise_bridge.exchange import validate_exchange_payload

        payload = build_synthetic_model(num_qubits=3, seed=1)
        errors = payload["consumer_bindings"]["uniqc.noisy_simulator.v1"]["gate_specific_errors"]
        errors[0]["qubits"] = [99]  # out-of-range 1q channel
        body = {k: v for k, v in payload.items() if k != "model_sha256"}
        payload["model_sha256"] = hashlib.sha256(
            json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with pytest.raises(ExchangeModelError, match="out of range"):
            validate_exchange_payload(payload)


class TestProducerFile:
    def test_nlearn_smoke_file_loads(self):
        if not NLEARN_SMOKE.is_file():
            pytest.skip("producer smoke model not present in this checkout")
        model = load_noise_model(NLEARN_SMOKE)
        assert isinstance(model, ImportedNoiseModel)
        assert model.num_qubits == 2

    def test_adapter_factory(self, synthetic_model):
        adapter = synthetic_model.to_adapter()
        assert adapter.backend_id == "dummy:noise-model"
        assert adapter.is_available()
