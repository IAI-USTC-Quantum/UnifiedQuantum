"""Offline unit tests for the TianYan (cqlib) backend adapter.

These tests inject a fake ``cqlib`` module via ``sys.modules`` so no real
SDK or network access is required. Credential loading is stubbed by
monkeypatching ``uniqc.config.load_tianyan_config``.
"""

from __future__ import annotations

import sys
import types

import pytest

ORIGINIR_BELL = """
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""".strip()


# ---------------------------------------------------------------------------
# Fake cqlib SDK
# ---------------------------------------------------------------------------


def _make_fake_cqlib(*, explode_on_init: bool = False) -> types.ModuleType:
    """Build a fake ``cqlib`` module with a TianYanPlatform test double.

    Per-call state lives in ``module.STATE`` so individual tests can stage
    query responses without touching other tests.
    """
    module = types.ModuleType("cqlib")
    module.STATE = {
        "instances": [],
        "responses": {},  # query_id -> result entry dict
        "submitted": [],  # submit_job kwargs
        "download_config": None,  # staged machine config payload
    }

    class FakeTianYanPlatform:
        QUERY_EXP_PATH = "/qccp-quantum/sdk/experiment/result/find"

        def __init__(self, login_key=None, auto_login=True, machine_name=None):
            if explode_on_init:
                raise RuntimeError("network access attempted")
            self.login_key = login_key
            self.auto_login = auto_login
            self.machine_name = machine_name
            module.STATE["instances"].append(self)

        def set_machine(self, name):
            self.machine_name = name

        def query_quantum_computer_list(self):
            return [
                ["1764555284795101186", "free", "running", "tianyan176"],
                ["1764555284795101187", "paid", "offline", "tianyan504"],
            ]

        def submit_job(self, circuit=None, exp_name="", num_shots=12000, lab_id=None, is_verify=True, **kwargs):
            query_id = f"QID-{len(module.STATE['submitted']) + 1}"
            module.STATE["submitted"].append(
                {
                    "query_id": query_id,
                    "circuit": circuit,
                    "exp_name": exp_name,
                    "num_shots": num_shots,
                    "lab_id": lab_id,
                    "is_verify": is_verify,
                    "machine_name": self.machine_name,
                }
            )
            # The real cqlib returns a *list* of query ids (one per circuit).
            return [query_id]

        def _send_request(self, path=None, data=None, method=None):
            assert path == self.QUERY_EXP_PATH
            assert method == "POST"
            query_id = data["query_ids"][0]
            entry = module.STATE["responses"].get(query_id)
            return {
                "code": 0,
                "data": {"experimentResultModelList": [entry] if entry else []},
            }

        def download_config(self, read_time=None, machine=None):
            return module.STATE["download_config"]

    module.TianYanPlatform = FakeTianYanPlatform
    return module


@pytest.fixture
def fake_cqlib(monkeypatch):
    """Install the fake cqlib module and stub credentials."""
    module = _make_fake_cqlib()
    monkeypatch.setitem(sys.modules, "cqlib", module)
    monkeypatch.setattr(
        "uniqc.config.load_tianyan_config",
        lambda: {"login_key": "TEST-LOGIN-KEY"},
    )
    return module


@pytest.fixture
def adapter(fake_cqlib):
    from uniqc.backend_adapter.task.adapters import TianyanAdapter

    return TianyanAdapter()


# ---------------------------------------------------------------------------
# Circuit translation
# ---------------------------------------------------------------------------


class TestTianyanTranslate:
    def test_bell_circuit_to_qcis(self, adapter):
        qcis = adapter.translate_circuit(ORIGINIR_BELL)
        assert qcis.splitlines() == ["H Q0", "CX Q0 Q1", "M Q0", "M Q1"]

    def test_parametric_and_dagger_gates(self, adapter):
        ir = "\n".join(
            [
                "QINIT 3",
                "CREG 3",
                "RX q[0], (0.12)",
                "RY q[1], (-0.5) dagger",
                "S q[2] dagger",
                "SX q[0]",
                "SX q[1] dagger",
                "T q[2] dagger",
                "CZ q[0], q[2]",
                "SWAP q[1], q[2]",
                "MEASURE q[0], c[0]",
                "MEASURE q[1], c[1]",
                "MEASURE q[2], c[2]",
            ]
        )
        qcis = adapter.translate_circuit(ir)
        assert qcis.splitlines()[:7] == [
            "RX Q0 0.12",
            "RY Q1 0.5",  # dagger negates the angle
            "SD Q2",
            "X2P Q0",
            "X2M Q1",
            "TD Q2",
            "CZ Q0 Q2",
        ]

    def test_unsupported_gate_raises_clear_error(self, adapter):
        ir = "QINIT 2\nCREG 2\nISWAP q[0], q[1]\nMEASURE q[0], c[0]\nMEASURE q[1], c[1]"
        with pytest.raises(NotImplementedError, match="ISWAP"):
            adapter.translate_circuit(ir)

    def test_rphi_not_supported(self, adapter):
        ir = "QINIT 1\nCREG 1\nRPhi q[0], (0.1, 0.2)\nMEASURE q[0], c[0]"
        with pytest.raises(NotImplementedError, match="RPhi"):
            adapter.translate_circuit(ir)

    def test_qubit_out_of_range(self, adapter):
        ir = "QINIT 1\nCREG 1\nH q[3]"
        with pytest.raises(ValueError, match="out of range"):
            adapter.translate_circuit(ir)


class TestTianyanCircuitAdapter:
    def test_adapt_matches_originir_to_qcis(self):
        from uniqc.backend_adapter.circuit_adapter import TianyanCircuitAdapter, originir_to_qcis
        from uniqc.circuit_builder import Circuit

        circuit = Circuit()
        circuit.h(0)
        circuit.cnot(0, 1)
        circuit.measure(0)
        circuit.measure(1)

        adapter = TianyanCircuitAdapter()
        assert adapter.adapt(circuit) == originir_to_qcis(circuit.originir)
        assert "H" in adapter.get_supported_gates()
        assert "CNOT" in adapter.get_supported_gates()


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


class TestTianyanSubmit:
    def test_submit_returns_query_id_and_forwards_kwargs(self, adapter, fake_cqlib):
        query_id = adapter.submit(ORIGINIR_BELL, shots=500, machine_name="tianyan176", task_name="exp1")
        assert query_id == "QID-1"

        call = fake_cqlib.STATE["submitted"][0]
        assert call["machine_name"] == "tianyan176"
        assert call["num_shots"] == 500
        assert call["exp_name"] == "exp1"
        # OriginIR input is translated to QCIS on submission.
        assert call["circuit"].splitlines()[0] == "H Q0"

    def test_submit_accepts_qcis_passthrough(self, adapter, fake_cqlib):
        adapter.submit("H Q0\nM Q0", shots=100, machine_name="tianyan_sw")
        assert fake_cqlib.STATE["submitted"][0]["circuit"] == "H Q0\nM Q0"

    def test_platform_cached_per_machine(self, adapter, fake_cqlib):
        adapter.submit(ORIGINIR_BELL, machine_name="tianyan176")
        adapter.submit(ORIGINIR_BELL, machine_name="tianyan176")
        adapter.submit(ORIGINIR_BELL, machine_name="tianyan_sw")
        assert len(fake_cqlib.STATE["instances"]) == 2

    def test_submit_batch_one_id_per_circuit(self, adapter):
        ids = adapter.submit_batch([ORIGINIR_BELL, ORIGINIR_BELL], shots=100)
        assert ids == ["QID-1", "QID-2"]

    def test_max_native_batch_size_is_one(self, adapter):
        assert adapter.max_native_batch_size == 1

    def test_missing_credentials_raises_import_error(self, monkeypatch, fake_cqlib):
        from uniqc.backend_adapter.task.adapters import TianyanAdapter

        def _raise():
            raise ImportError("Tianyan config not found. Run `uniqc config set tianyan.login_key ...`")

        monkeypatch.setattr("uniqc.config.load_tianyan_config", _raise)
        with pytest.raises(ImportError, match="tianyan.login_key"):
            TianyanAdapter().submit(ORIGINIR_BELL, machine_name="tianyan176")


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def _result_entry(query_id: str, labels=(0, 1), shots_rows=((0, 1), (0, 1), (1, 0))) -> dict:
    return {
        "experimentTaskId": query_id,
        "resultStatus": [list(labels), *[list(row) for row in shots_rows]],
        "probability": [],
    }


class TestTianyanQuery:
    def test_query_running_when_no_entry(self, adapter):
        result = adapter.query("QID-1")
        assert result["status"] == "running"

    def test_query_success_counts_bit_order(self, adapter, fake_cqlib):
        # resultStatus row 0 lists measured qubits in measurement order
        # (first = c[0]); uniqc puts c[0] on the RIGHT of the bitstring.
        fake_cqlib.STATE["responses"]["QID-1"] = _result_entry("QID-1")
        result = adapter.query("QID-1")
        assert result["status"] == "success"
        assert result["result"] == {"10": 2, "01": 1}

    def test_query_failed_on_explicit_error_status(self, adapter, fake_cqlib):
        fake_cqlib.STATE["responses"]["QID-1"] = {
            "experimentTaskId": "QID-1",
            "status": "failed",
            "errorMessage": "machine offline",
        }
        result = adapter.query("QID-1")
        assert result["status"] == "failed"
        assert "machine offline" in result["result"]["error"]

    def test_query_entry_without_result_is_running(self, adapter, fake_cqlib):
        fake_cqlib.STATE["responses"]["QID-1"] = {"experimentTaskId": "QID-1", "status": "running"}
        assert adapter.query("QID-1")["status"] == "running"

    def test_query_batch_merges_statuses(self, adapter, fake_cqlib):
        fake_cqlib.STATE["responses"]["QID-1"] = _result_entry("QID-1")
        # QID-2 has no entry -> running
        merged = adapter.query_batch(["QID-1", "QID-2"])
        assert merged["status"] == "running"

        fake_cqlib.STATE["responses"]["QID-2"] = _result_entry("QID-2", shots_rows=((1, 1),))
        merged = adapter.query_batch(["QID-1", "QID-2"])
        assert merged["status"] == "success"
        assert merged["result"] == [{"10": 2, "01": 1}, {"11": 1}]

        fake_cqlib.STATE["responses"]["QID-2"] = {"experimentTaskId": "QID-2", "status": "failed"}
        merged = adapter.query_batch(["QID-1", "QID-2"])
        assert merged["status"] == "failed"


# ---------------------------------------------------------------------------
# list_backends / is_available
# ---------------------------------------------------------------------------


class TestTianyanBackends:
    def test_list_backends_normalised(self, adapter):
        backends = adapter.list_backends()
        by_name = {b["name"]: b for b in backends}

        hw = by_name["tianyan176"]
        assert hw["available"] is True
        assert hw["is_simulator"] is False
        assert hw["num_qubits"] == 176

        offline = by_name["tianyan504"]
        assert offline["available"] is False

        # Simulators are always present, even when the API omits them.
        assert by_name["tianyan_sw"]["is_simulator"] is True
        assert by_name["tianyan_sw"]["available"] is True

    def test_is_available_with_sdk_and_credentials(self, adapter):
        assert adapter.is_available() is True

    def test_is_available_false_without_credentials(self, monkeypatch, fake_cqlib):
        from uniqc.backend_adapter.task.adapters import TianyanAdapter

        def _raise():
            raise ImportError("no config")

        monkeypatch.setattr("uniqc.config.load_tianyan_config", _raise)
        assert TianyanAdapter().is_available() is False

    def test_is_available_false_without_sdk(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "cqlib", None)
        from uniqc.backend_adapter.task.adapters import TianyanAdapter

        assert TianyanAdapter().is_available() is False


# ---------------------------------------------------------------------------
# Dry-run (must not touch the network / SDK platform object)
# ---------------------------------------------------------------------------


class TestTianyanDryRun:
    def test_dry_run_offline_success(self, monkeypatch):
        # Platform construction would raise — dry_run must never reach it.
        monkeypatch.setitem(sys.modules, "cqlib", _make_fake_cqlib(explode_on_init=True))
        monkeypatch.setattr(
            "uniqc.config.load_tianyan_config",
            lambda: {"login_key": "TEST-LOGIN-KEY"},
        )

        from uniqc.backend_adapter.task.adapters import TianyanAdapter

        result = TianyanAdapter().dry_run(ORIGINIR_BELL, shots=100, machine_name="tianyan176")
        assert result.success is True
        assert result.circuit_qubits == 2
        assert result.backend_name == "tianyan176"
        assert "H" in result.supported_gates

    def test_dry_run_rejects_unsupported_gate(self, adapter):
        ir = "QINIT 2\nCREG 2\nISWAP q[0], q[1]"
        result = adapter.dry_run(ir, shots=100)
        assert result.success is False
        assert "ISWAP" in result.error

    def test_dry_run_rejects_nonpositive_shots(self, adapter):
        result = adapter.dry_run(ORIGINIR_BELL, shots=0)
        assert result.success is False


# ---------------------------------------------------------------------------
# Normaliser
# ---------------------------------------------------------------------------


class TestNormalizeTianyan:
    def test_counts_endianness(self):
        from uniqc.backend_adapter.task.normalizers import normalize_tianyan

        entry = _result_entry("QID-9", labels=(0, 6), shots_rows=((0, 1), (1, 0), (1, 0)))
        unified = normalize_tianyan(entry, task_id="QID-9", backend_name="tianyan176")
        assert unified.platform == "tianyan"
        assert unified.backend_name == "tianyan176"
        # First measured qubit -> c[0] -> rightmost character.
        assert unified.counts == {"10": 1, "01": 2}

    def test_empty_result_status(self):
        from uniqc.backend_adapter.task.normalizers import normalize_tianyan

        unified = normalize_tianyan({"experimentTaskId": "x"}, task_id="x")
        assert unified.counts == {}


# ---------------------------------------------------------------------------
# Chip characterization
# ---------------------------------------------------------------------------

_FAKE_MACHINE_CONFIG = {
    "calibrationTime": "2026-08-20 10:31:33",
    "computerId": "tianyan176",
    "disabledQubits": "Q2",
    "disabledCouplers": "G1",
    "overview": {
        "qubits": ["Q0", "Q1", "Q2"],
        "coupler_map": {"G0": ["Q0", "Q1"], "G1": ["Q1", "Q2"]},
    },
    "qubit": {
        "relatime": {
            "T1": {"param_list": [30.0, 25.0], "qubit_used": ["Q0", "Q1"], "unit": "us"},
            "T2": {"param_list": [20.0, 15.0], "qubit_used": ["Q0", "Q1"], "unit": "us"},
        },
        "singleQubit": {
            "gate error": {"param_list": [0.1, 0.2], "qubit_used": ["Q0", "Q1"], "unit": "%"},
        },
    },
    "readout": {
        "readoutArray": {
            "Readout Error": {"param_list": [3.0, 4.0], "qubit_used": ["Q0", "Q1"], "unit": "%"},
        },
    },
    "twoQubitGate": {
        "czGate": {
            "gate error": {"param_list": [1.5], "qubit_used": ["G0"], "unit": "%"},
        },
    },
}


class TestTianyanChipCharacterization:
    def test_builds_unified_model(self, adapter, fake_cqlib):
        fake_cqlib.STATE["download_config"] = _FAKE_MACHINE_CONFIG

        chip = adapter.get_chip_characterization("tianyan176")

        assert chip is not None
        assert chip.full_id == "tianyan:tianyan176"
        # Q2 disabled -> only Q0/Q1 available; G1 disabled (and touches the
        # disabled Q2 anyway) -> only the Q0-Q1 edge remains.
        assert chip.available_qubits == (0, 1)
        assert [(e.u, e.v) for e in chip.connectivity] == [(0, 1)]
        q0 = chip.single_qubit_data[0]
        assert q0.t1 == pytest.approx(30.0)
        assert q0.t2 == pytest.approx(20.0)
        assert q0.single_gate_fidelity == pytest.approx(0.999)
        assert q0.avg_readout_fidelity == pytest.approx(0.97)
        assert q0.readout_fidelity_0 is None  # platform reports one combined error
        assert chip.two_qubit_data[0].gates[0].gate == "cz"
        assert chip.two_qubit_data[0].gates[0].fidelity == pytest.approx(0.985)
        assert chip.global_info.two_qubit_gates == ("cz",)
        assert chip.calibrated_at == "2026-08-20 10:31:33"

    def test_returns_none_without_config(self, adapter):
        assert adapter.get_chip_characterization("tianyan176") is None
