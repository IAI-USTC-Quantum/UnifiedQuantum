"""Tests for the task adapter layer.

These tests verify that:
1. Each adapter correctly translates OriginIR to provider-native circuits.
2. Config is loaded from ``~/.uniqc/config.yaml`` via the active profile.
3. Task modules delegate to adapters.

Cloud tests require real credentials and are marked with @pytest.mark.cloud.
"""

from __future__ import annotations

import json

import pytest

from uniqc.test.cloud._config_helpers import write_uniqc_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ORIGINIR_BELL = """
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
""".strip()

ORIGINIR_3Q = """
QINIT 3
CREG 3
H q[0]
H q[1]
H q[2]
CNOT q[0], q[1]
CNOT q[1], q[2]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
MEASURE q[2], c[2]
""".strip()


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class RunTestConfigYaml:
    """Config loading from the active YAML profile."""

    def run_test_originq_config_from_yaml(self, monkeypatch, tmp_path):
        """OriginQ config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(
            tmp_path,
            {"originq": {"token": "test_key_123", "task_group_size": 100}},
        )
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_originq_config

        config = load_originq_config()
        assert config["api_key"] == "test_key_123"
        assert config["task_group_size"] == 100

    def run_test_quark_config_from_yaml(self, monkeypatch, tmp_path):
        """QuarkStudio config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(tmp_path, {"quark": {"token": "quark_secret_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_quark_config

        config = load_quark_config()
        assert config["api_token"] == "quark_secret_token"

    def run_test_ibm_config_from_yaml(self, monkeypatch, tmp_path):
        """IBM config is read from ~/.uniqc/config.yaml."""
        write_uniqc_config(tmp_path, {"ibm": {"token": "ibm_secret_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_ibm_config

        config = load_ibm_config()
        assert config["api_token"] == "ibm_secret_token"

    def run_test_dummy_config_from_yaml(self, monkeypatch, tmp_path):
        """OriginQ Dummy config is read from the OriginQ YAML section."""
        write_uniqc_config(
            tmp_path,
            {
                "originq": {
                    "token": "",
                    "available_qubits": [0, 1, 2, 3],
                    "available_topology": [[0, 1], [1, 2], [2, 3]],
                    "task_group_size": 50,
                }
            },
        )
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_dummy_config

        config = load_dummy_config()
        assert config["available_qubits"] == [0, 1, 2, 3]
        assert config["available_topology"] == [[0, 1], [1, 2], [2, 3]]
        assert config["task_group_size"] == 50

    def run_test_originq_config_import_error_without_token(self, monkeypatch, tmp_path):
        """ImportError is raised when the active YAML config has no OriginQ token."""
        write_uniqc_config(tmp_path, {"originq": {"token": ""}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.config import load_originq_config

        with pytest.raises(ImportError, match="originq.token"):
            load_originq_config()

    def run_test_active_profile_is_used(self, monkeypatch, tmp_path):
        """Task config respects active_profile from ~/.uniqc/config.yaml."""
        from uniqc.backend_adapter.config import save_config

        config_file = tmp_path / ".uniqc" / "config.yaml"
        save_config(
            {
                "active_profile": "prod",
                "default": {"originq": {"token": "default-token"}},
                "prod": {"originq": {"token": "prod-token"}},
            },
            config_file,
        )
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", config_file)

        from uniqc.config import load_originq_config

        cfg = load_originq_config()
        assert cfg["api_key"] == "prod-token"


# ---------------------------------------------------------------------------
# OriginQ adapter tests (require credentials)
# ---------------------------------------------------------------------------


@pytest.mark.cloud
@pytest.mark.requires_pyqpanda3
class RunTestOriginQAdapterIntegration:
    """Integration tests for OriginQ adapter with real pyqpanda3 and credentials."""

    def run_test_translate_circuit(self):
        """Test that translate_circuit converts OriginIR to QProg."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        result = adapter.translate_circuit(ORIGINIR_BELL)
        assert result is not None

    @pytest.mark.real_cloud_execution
    def run_test_submit_and_query(self):
        """Test submit and query with real service."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        task_id = adapter.submit(ORIGINIR_BELL, shots=1000)
        assert task_id is not None

        result = adapter.query(task_id)
        assert "status" in result

    @pytest.mark.real_cloud_execution
    def run_test_submit_batch(self):
        """Test submit_batch with real service."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        circuits = [ORIGINIR_BELL] * 2
        task_ids = adapter.submit_batch(circuits, shots=1000)
        assert len(task_ids) >= 1


# ---------------------------------------------------------------------------
# IBM adapter tests (require credentials)
# ---------------------------------------------------------------------------


@pytest.mark.cloud
@pytest.mark.requires_qiskit
class RunTestIBMAdapterIntegration:
    """Integration tests for IBM adapter with real qiskit and credentials."""

    def run_test_translate_circuit(self):
        """Test circuit translation with real qiskit."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        result = adapter.translate_circuit(ORIGINIR_BELL)
        assert result is not None
        assert hasattr(result, "num_qubits")

    def run_test_service_init_and_translate(self):
        """Test real IBM service initialisation and circuit translation."""
        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()

        adapter.translate_circuit(ORIGINIR_BELL)
        # Note: IBM submission requires backend selection
        # This test may need adjustment based on available backends


# ---------------------------------------------------------------------------
# Adapter availability tests
# ---------------------------------------------------------------------------


class RunTestAdapterAvailability:
    """Each adapter reports availability based on installed packages / config."""

    def run_test_originq_adapter_available_with_config(self, monkeypatch, tmp_path):
        """Test OriginQ adapter availability with config."""
        write_uniqc_config(tmp_path, {"originq": {"token": "test_key"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")

        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter()
        assert adapter.is_available() is True

    def run_test_ibm_adapter_available_with_config(self, monkeypatch, tmp_path):
        """Test IBM adapter availability with config."""
        write_uniqc_config(tmp_path, {"ibm": {"token": "test_token"}})
        monkeypatch.setattr("uniqc.config.CONFIG_FILE", tmp_path / ".uniqc" / "config.yaml")
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", lambda **_kwargs: object())

        from uniqc.backend_adapter.task.adapters import QiskitAdapter

        adapter = QiskitAdapter()
        assert isinstance(adapter.is_available(), bool)


# ---------------------------------------------------------------------------
# OriginQ adapter unit tests (mock-based)
# ---------------------------------------------------------------------------


class TestOriginQAdapterUnit:
    """Unit tests for OriginQ adapter using mocks."""

    def run_test_format_counts_returns_dict(self):
        """_format_counts returns {bitstring: shots} dict, not list of dicts."""
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = None
        adapter._QCloudOptions = None
        adapter._QCloudJob = None
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._convert_originir = None

        # dict input
        result = adapter._format_counts({"00": 512, "11": 488})
        assert isinstance(result, dict)
        assert result == {"00": 512, "11": 488}

        # list of dicts (batch) — counts should be merged
        result = adapter._format_counts([{"00": 256}, {"00": 256, "11": 488}])
        assert isinstance(result, dict)
        assert result == {"00": 512, "11": 488}

        # non-dict/list fallback
        result = adapter._format_counts("something")
        assert isinstance(result, dict)
        assert result == {"something": 1}

    def run_test_get_chip_characterization_double_qubits_no_uv_accessor(self):
        """get_chip_characterization falls back to topology index when dq lacks u/v accessors.

        Some pyqpanda3 chip_info() implementations return double_qubits_info() objects
        that have get_fidelity() but lack get_qubit_u() / get_qubit_v(). The adapter
        must use the topology index to look up the qubit pair instead of crashing.
        """
        # Minimal mock objects
        mock_sq = type(
            "MockSQ",
            (),
            {
                "get_qubit_id": lambda self: 0,
                "get_t1": lambda self: 50.0,
                "get_t2": lambda self: 80.0,
                "get_single_gate_fidelity": lambda self: 0.99,
                "get_readout_fidelity": lambda self: 0.95,
                "get_readout_fidelity_0": lambda self: 0.97,
                "get_readout_fidelity_1": lambda self: 0.93,
            },
        )()

        mock_dq = type(
            "MockDQ",
            (),
            {
                # No get_qubit_u / get_qubit_v — this is the case being tested
                "get_fidelity": lambda self: 0.85,
            },
        )()

        mock_ci = type(
            "MockCI",
            (),
            {
                "qubits_num": lambda self: 5,
                "get_chip_topology": lambda self: [(0, 1), (1, 2), (2, 3)],
                "available_qubits": lambda self: [0, 1, 2, 3, 4],
                "single_qubit_info": lambda self: [mock_sq],
                "double_qubits_info": lambda self: [mock_dq],
            },
        )()

        mock_backend = type(
            "MockBackend",
            (),
            {
                "chip_info": lambda self: mock_ci,
                "configuration": lambda self: type(
                    "MockCfg",
                    (),
                    {
                        "supported_gates": lambda self: ["x", "h", "cx", "cz"],
                        "single_qubit_gate_time": lambda self: 20.0,
                        "two_qubit_gate_time": lambda self: 300.0,
                    },
                )(),
            },
        )()

        mock_service = type(
            "MockService",
            (),
            {
                "backend": lambda self, name: mock_backend,
            },
        )()

        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = mock_service
        adapter._QCloudOptions = None
        adapter._QCloudJob = None
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._convert_originir = None

        chip = adapter.get_chip_characterization("wuyuan:d5")

        assert chip is not None
        assert len(chip.two_qubit_data) == 1
        # Fallback to topology: index 0 → (0, 1)
        assert chip.two_qubit_data[0].qubit_u == 0
        assert chip.two_qubit_data[0].qubit_v == 1
        # Fidelity was available even without u/v accessors
        assert chip.two_qubit_data[0].gates[0].fidelity == 0.85


# ---------------------------------------------------------------------------
# probCount fallback unit tests (issue #119)
# ---------------------------------------------------------------------------


def _probcount_payload(entries: list[dict]) -> str:
    """Build a raw ``job.result(keys=["probCount"])`` origin_data payload."""
    return json.dumps({"obj": {"probCount": [json.dumps(e) for e in entries]}})


class _FakeQCloudResult:
    """Stand-in for pyqpanda3 QCloudResult."""

    def __init__(self, status: str, counts, error: str = "") -> None:
        self._status = status
        self._counts = counts
        self._error = error

    def job_status(self):
        return type("Status", (), {"name": self._status})()

    def error_message(self) -> str:
        return self._error

    def get_counts(self):
        return self._counts

    def get_counts_list(self):
        raise RuntimeError("no list-shaped counts")


class _FakeJob:
    """Stand-in for pyqpanda3 QCloudJob with result(keys=[...]) support."""

    def __init__(self, qr: _FakeQCloudResult, probcount_payload: str | None = None) -> None:
        self._qr = qr
        self._payload = probcount_payload
        self.result_calls: list[tuple] = []

    def query(self) -> _FakeQCloudResult:
        return self._qr

    def result(self, keys=None):
        self.result_calls.append(tuple(keys or ()))
        payload = self._payload

        class _RawResult:
            def origin_data(self) -> str:
                return payload

        return _RawResult()


class TestOriginQProbCountFallback:
    """issue #119: WK_C180 FINISHED tasks lose counts in get_counts() but keep
    them in the raw probCount key — query() must recover them."""

    @staticmethod
    def _adapter(job: _FakeJob):
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = object()
        adapter._QCloudOptions = None
        adapter._QCloudJob = lambda taskid: job
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._convert_originir = None
        adapter._batch_job_sizes = {}
        adapter._ensure_imports = lambda: None
        return adapter

    def test_finished_empty_counts_recovers_from_probcount(self):
        bell = {"value": [258, 13, 77, 152], "key": ["0x0", "0x1", "0x2", "0x3"]}
        job = _FakeJob(
            _FakeQCloudResult("FINISHED", {}),
            _probcount_payload([bell]),
        )
        result = self._adapter(job).query("T1")
        assert result["status"] == "success"
        assert result["result"] == {"00": 258, "01": 13, "10": 77, "11": 152}

    def test_nonempty_counts_skips_fallback(self):
        job = _FakeJob(
            _FakeQCloudResult("FINISHED", {"00": 5, "11": 3}),
            _probcount_payload([{"value": [1], "key": ["0x0"]}]),
        )
        result = self._adapter(job).query("T1")
        assert job.result_calls == []
        assert result["result"] == {"00": 5, "11": 3}

    def test_running_task_never_calls_fallback(self):
        job = _FakeJob(_FakeQCloudResult("RUNNING", {}))
        result = self._adapter(job).query("T1")
        assert job.result_calls == []
        assert result["status"] == "running"

    def test_failed_task_never_calls_fallback(self):
        job = _FakeJob(_FakeQCloudResult("FAILED", {}, error="boom"))
        result = self._adapter(job).query("T1")
        assert job.result_calls == []
        assert result["status"] == "failed"

    def test_malformed_probcount_payload_keeps_empty_result(self):
        job = _FakeJob(_FakeQCloudResult("FINISHED", {}), "not-json")
        result = self._adapter(job).query("T1")
        assert result["status"] == "success"
        assert result["result"] == {}

    def test_batch_probcount_returns_per_circuit_list(self):
        entry_a = {"value": [258, 242], "key": ["0x0", "0x3"]}
        entry_b = {"value": [13, 487], "key": ["0x1", "0x2"]}
        job = _FakeJob(
            _FakeQCloudResult("FINISHED", {}),
            _probcount_payload([entry_a, entry_b]),
        )
        adapter = self._adapter(job)
        adapter._batch_job_sizes["T1"] = (2, 500)
        result = adapter.query("T1")
        assert result["status"] == "success"
        assert result["result"] == [{"00": 258, "11": 242}, {"01": 13, "10": 487}]

    def test_parse_hex_outcomes_width_from_max_key(self):
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        parsed = OriginQAdapter._parse_hex_outcomes(["0x0", "0x2"], [1, 2])
        assert parsed == {"00": 1, "10": 2}
        # Decimal keys are accepted too.
        parsed = OriginQAdapter._parse_hex_outcomes([0, 5], [3, 4])
        assert parsed == {"000": 3, "101": 4}


# ---------------------------------------------------------------------------
# Native batch submission unit tests (mock-based)
# ---------------------------------------------------------------------------


class TestOriginQNativeBatch:
    """Unit tests for OriginQ native batch submission via run_instruction()."""

    def _make_adapter(self, mock_backend, batch_size_qubits: int = 2):
        from uniqc.backend_adapter.task.adapters import OriginQAdapter

        adapter = OriginQAdapter.__new__(OriginQAdapter)
        adapter._api_key = "test"
        adapter._service = type("S", (), {"backend": lambda self, name: mock_backend})()
        # _create_options needs a callable QCloudOptions class.

        class _Opt:
            def __init__(self):
                self.amend = False
                self.mapping = False
                self.optimization = True

            def set_amend(self, v):
                self.amend = v

            def set_mapping(self, v):
                self.mapping = v

            def set_optimization(self, v):
                self.optimization = v

        adapter._QCloudOptions = _Opt
        adapter._QCloudJob = None
        adapter._JobStatus = None
        adapter._DataBase = None
        adapter._convert_originir = None
        adapter._last_backend_name = "WK_C180"
        adapter._last_n_qubits = batch_size_qubits
        adapter._canonical_backend_cache = {"WK_C180": "WK_C180"}
        adapter._batch_job_sizes = {}
        return adapter

    def test_native_batch_uses_run_list_and_returns_single_id(self, monkeypatch):

        captured = {}

        class FakeJob:
            def job_id(self):
                return "BATCH-JOB-ID-1"

        class FakeBackend:
            def chip_info(self):
                return type("CI", (), {"qubits_num": lambda self: 2})()

            def run(self, progs, shots, options):
                # pyqpanda3 native batch overload: list[QProg], shots, options
                captured["progs"] = progs
                captured["shots"] = shots
                captured["options"] = options
                return FakeJob()

            def run_instruction(self, *args, **kwargs):
                raise AssertionError("Native batch must not use run_instruction")

        adapter = self._make_adapter(FakeBackend())

        # Fake QProg sentinel
        class FakeQProg:
            def __init__(self, ir):
                self.ir = ir

        adapter.translate_circuit = lambda ir: FakeQProg(ir)
        adapter._validate_backend = lambda name: None
        adapter._ensure_imports = lambda: None

        circuits = ["c0", "c1", "c2"]
        ids = adapter.submit_batch(circuits, shots=2048, backend_name="WK_C180")

        assert ids == ["BATCH-JOB-ID-1"]
        assert len(captured["progs"]) == 3
        assert all(isinstance(p, FakeQProg) for p in captured["progs"])
        assert [p.ir for p in captured["progs"]] == circuits
        assert captured["shots"] == 2048
        assert adapter._batch_job_sizes["BATCH-JOB-ID-1"] == (3, 2048)

    def test_native_batch_disabled_falls_back_to_per_circuit_run(self):
        class FakeJob:
            _next = 0

            def job_id(self):
                FakeJob._next += 1
                return f"JOB-{FakeJob._next}"

        run_call_args: list = []

        class FakeBackend:
            def chip_info(self):
                return type("CI", (), {"qubits_num": lambda self: 2})()

            def run(self, *args, **kwargs):
                run_call_args.append((args, kwargs))
                return FakeJob()

            def run_instruction(self, *a, **kw):
                raise AssertionError("Should not call run_instruction")

        adapter = self._make_adapter(FakeBackend())
        adapter.translate_circuit = lambda ir: object()
        adapter._validate_backend = lambda name: None
        adapter._ensure_imports = lambda: None

        ids = adapter.submit_batch(
            ["c0", "c1", "c2"],
            shots=100,
            native_batch=False,
            backend_name="WK_C180",
        )
        assert len(ids) == 3
        # Three calls, each a single QProg (not a list)
        assert len(run_call_args) == 3
        for args, _kwargs in run_call_args:
            first = args[0]
            assert not isinstance(first, list), "per-circuit fallback must pass single QProg"
        # Per-circuit submissions must not register batch sizing.
        assert adapter._batch_job_sizes == {}

    def test_native_batch_single_circuit_falls_back_to_run(self):
        run_calls: list = []

        class FakeJob:
            def job_id(self):
                return "SINGLE-1"

        class FakeBackend:
            def chip_info(self):
                return type("CI", (), {"qubits_num": lambda self: 2})()

            def run(self, *args, **kwargs):
                run_calls.append((args, kwargs))
                return FakeJob()

            def run_instruction(self, *a, **kw):
                raise AssertionError("Single-circuit batch should not call run_instruction")

        adapter = self._make_adapter(FakeBackend())
        adapter.translate_circuit = lambda ir: object()
        adapter._validate_backend = lambda name: None
        adapter._ensure_imports = lambda: None

        ids = adapter.submit_batch(["only"], shots=10, backend_name="WK_C180")
        assert ids == ["SINGLE-1"]
        assert len(run_calls) == 1
        first_arg = run_calls[0][0][0]
        assert not isinstance(first_arg, list)


class TestNativeBatchHighLevel:
    """Tests for the public submit_batch / wait_for_result batch contract."""

    def test_wrap_batch_result_list(self):
        from uniqc.backend_adapter.task_manager import _wrap_as_unified_result_list

        raw = [{"00": 100, "11": 100}, {"01": 200}]
        results = _wrap_as_unified_result_list(
            raw,
            task_id="batch-1",
            backend="originq:WK_C180",
            shots=200,
        )
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0].counts == {"00": 100, "11": 100}
        assert results[0].task_id == "batch-1#0"
        assert results[1].counts == {"01": 200}
        assert results[1].task_id == "batch-1#1"
        assert results[0].platform == "originq"

    def test_wrap_batch_result_handles_dict_wrapper(self):
        from uniqc.backend_adapter.task_manager import _wrap_as_unified_result_list

        raw = {"result": [{"0": 50}, {"1": 50}], "status": "success"}
        results = _wrap_as_unified_result_list(
            raw,
            task_id="b",
            backend="ibm",
            shots=50,
        )
        assert len(results) == 2
        assert results[0].counts == {"0": 50}
        assert results[1].counts == {"1": 50}
