"""Offline unit tests for the LogicalQubit (lqcloud) backend adapter.

These tests inject a fake ``lqcloud`` module via ``sys.modules`` so no real
SDK or network access is required. Credential loading is stubbed by
monkeypatching ``uniqc.config.load_logicalqubit_config``.
"""

from __future__ import annotations

import enum
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
# Fake lqcloud SDK
# ---------------------------------------------------------------------------


class _FakeJobStatus(enum.Enum):
    QUEUED = "queued"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _make_fake_lqcloud(*, explode_on_provider_init: bool = False) -> types.ModuleType:
    """Build a fake ``lqcloud`` module (plus ``lqcloud.job`` submodule).

    Per-call state lives in ``module.STATE`` so individual tests can stage
    job statuses / counts without touching other tests.
    """
    module = types.ModuleType("lqcloud")
    job_module = types.ModuleType("lqcloud.job")
    module.STATE = {
        "providers": [],
        "submitted": [],  # {"job_id", "backend_name", "shots", "circuit"}
        "statuses": {},  # job_id -> _FakeJobStatus
        "counts": {},  # job_id -> counts dict
        "backend_names": ["lq-sim-1", "lq-qpu-1"],
        "backend_config": None,  # staged get_backend_config payload
    }

    class FakeQuantumCircuit:
        def __init__(self, num_qubits, num_clbits=None):
            self.num_qubits = num_qubits
            self.num_clbits = num_clbits if num_clbits is not None else num_qubits
            self.ops = []

        def __getattr__(self, name):
            def _recorder(*args):
                self.ops.append((name, *args))

            return _recorder

    class FakeJob:
        def __init__(self, job_id, provider, *args, **kwargs):
            self.job_id = job_id
            self.provider = provider

        def status(self):
            return module.STATE["statuses"].get(self.job_id, _FakeJobStatus.RUNNING)

        def result(self):
            counts = module.STATE["counts"].get(self.job_id, {})
            return types.SimpleNamespace(get_counts=lambda: counts)

    class FakeBackend:
        def __init__(self, name, provider):
            self.name = name
            self.provider = provider

        def run(self, qc, shots=1000):
            job_id = f"JOB-{len(module.STATE['submitted']) + 1}"
            module.STATE["submitted"].append(
                {
                    "job_id": job_id,
                    "backend_name": self.name,
                    "shots": shots,
                    "circuit": qc,
                }
            )
            return FakeJob(job_id, self.provider)

    class FakeLQCloudProvider:
        def __init__(self, api_key=None, token=None, url=None, interactive=True):
            if explode_on_provider_init:
                raise RuntimeError("network access attempted")
            self.api_key = api_key
            self.token = token
            self.url = url
            self.interactive = interactive
            module.STATE["providers"].append(self)

        def get_backends(self):
            return [{"name": name} for name in module.STATE["backend_names"]]

        def get_backend(self, name, verify=True):
            if name not in module.STATE["backend_names"]:
                raise ValueError(f"unknown backend {name}")
            return FakeBackend(name, self)

        def get_backend_config(self, name):
            return module.STATE["backend_config"]

    module.LQCloudProvider = FakeLQCloudProvider
    module.QuantumCircuit = FakeQuantumCircuit
    job_module.Job = FakeJob
    job_module.JobStatus = _FakeJobStatus
    module.job = job_module
    return module


@pytest.fixture
def fake_lqcloud(monkeypatch):
    """Install the fake lqcloud module (+ lqcloud.job) and stub credentials."""
    module = _make_fake_lqcloud()
    monkeypatch.setitem(sys.modules, "lqcloud", module)
    monkeypatch.setitem(sys.modules, "lqcloud.job", module.job)
    monkeypatch.setattr(
        "uniqc.config.load_logicalqubit_config",
        lambda: {"api_key": "TEST-API-KEY", "url": "https://cloud.logicalqubit.com"},
    )
    return module


@pytest.fixture
def adapter(fake_lqcloud):
    from uniqc.backend_adapter.task.adapters import LogicalQubitAdapter

    return LogicalQubitAdapter()


# ---------------------------------------------------------------------------
# Circuit translation
# ---------------------------------------------------------------------------


class TestLogicalQubitTranslate:
    def test_bell_circuit_ops(self, adapter):
        qc = adapter.translate_circuit(ORIGINIR_BELL)
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2
        assert qc.ops == [("h", 0), ("cx", 0, 1), ("measure", 0, 0), ("measure", 1, 1)]

    def test_gate_mapping_and_angle_order(self, adapter):
        # lqcloud follows qiskit conventions: rx(theta, qubit).
        ir = "\n".join(
            [
                "QINIT 2",
                "CREG 2",
                "RX q[0], (0.12)",
                "RY q[1], (0.5) dagger",
                "S q[0] dagger",
                "SX q[1]",
                "SX q[0] dagger",
                "T q[1] dagger",
                "U1 q[0], (0.3)",
                "CZ q[0], q[1]",
                "ISWAP q[1], q[0]",
                "MEASURE q[0], c[0]",
                "MEASURE q[1], c[1]",
            ]
        )
        qc = adapter.translate_circuit(ir)
        assert qc.ops == [
            ("rx", 0.12, 0),
            ("ry", -0.5, 1),
            ("sdg", 0),
            ("sx", 1),
            ("sxdg", 0),
            ("tdg", 1),
            ("p", 0.3, 0),
            ("cz", 0, 1),
            ("iswap", 1, 0),
            ("measure", 0, 0),
            ("measure", 1, 1),
        ]

    def test_unsupported_gate_raises_clear_error(self, adapter):
        ir = "QINIT 1\nCREG 1\nRPhi q[0], (0.1, 0.2)\nMEASURE q[0], c[0]"
        with pytest.raises(NotImplementedError, match="RPhi"):
            adapter.translate_circuit(ir)


class TestLogicalQubitCircuitAdapter:
    def test_adapt_matches_originir_to_lqcloud(self, fake_lqcloud):
        from uniqc.backend_adapter.circuit_adapter import (
            LogicalQubitCircuitAdapter,
            originir_to_lqcloud_circuit,
        )
        from uniqc.circuit_builder import Circuit

        circuit = Circuit()
        circuit.h(0)
        circuit.cnot(0, 1)
        circuit.measure(0)
        circuit.measure(1)

        adapter = LogicalQubitCircuitAdapter()
        got = adapter.adapt(circuit)
        expected = originir_to_lqcloud_circuit(circuit.originir, fake_lqcloud.QuantumCircuit)
        assert got.ops == expected.ops
        assert "H" in adapter.get_supported_gates()
        assert "TOFFOLI" in adapter.get_supported_gates()


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


class TestLogicalQubitSubmit:
    def test_submit_returns_job_id_and_forwards_kwargs(self, adapter, fake_lqcloud):
        job_id = adapter.submit(ORIGINIR_BELL, shots=500, backend_name="lq-sim-1")
        assert job_id == "JOB-1"

        call = fake_lqcloud.STATE["submitted"][0]
        assert call["backend_name"] == "lq-sim-1"
        assert call["shots"] == 500
        # OriginIR input is translated to an lqcloud QuantumCircuit.
        assert call["circuit"].ops[0] == ("h", 0)

    def test_provider_created_once_with_config(self, adapter, fake_lqcloud):
        adapter.submit(ORIGINIR_BELL, backend_name="lq-sim-1")
        adapter.submit(ORIGINIR_BELL, backend_name="lq-sim-1")
        providers = fake_lqcloud.STATE["providers"]
        assert len(providers) == 1
        assert providers[0].api_key == "TEST-API-KEY"
        assert providers[0].url == "https://cloud.logicalqubit.com"
        assert providers[0].interactive is False

    def test_submit_requires_backend_name(self, adapter):
        with pytest.raises(ValueError, match="backend"):
            adapter.submit(ORIGINIR_BELL)

    def test_submit_rejects_shots_above_server_limit(self, adapter):
        with pytest.raises(ValueError, match="50000"):
            adapter.submit(ORIGINIR_BELL, shots=50001, backend_name="lq-sim-1")

    def test_submit_batch_one_id_per_circuit(self, adapter):
        ids = adapter.submit_batch([ORIGINIR_BELL, ORIGINIR_BELL], shots=100, backend_name="lq-sim-1")
        assert ids == ["JOB-1", "JOB-2"]

    def test_max_native_batch_size_is_one(self, adapter):
        assert adapter.max_native_batch_size == 1

    def test_missing_credentials_raises_import_error(self, monkeypatch, fake_lqcloud):
        from uniqc.backend_adapter.task.adapters import LogicalQubitAdapter

        def _raise():
            raise ImportError("LogicalQubit config not found. Run `uniqc config set logicalqubit.api_key ...`")

        monkeypatch.setattr("uniqc.config.load_logicalqubit_config", _raise)
        with pytest.raises(ImportError, match="logicalqubit.api_key"):
            LogicalQubitAdapter().submit(ORIGINIR_BELL, backend_name="lq-sim-1")


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class TestLogicalQubitQuery:
    def test_query_running(self, adapter, fake_lqcloud):
        fake_lqcloud.STATE["statuses"]["JOB-1"] = _FakeJobStatus.QUEUED
        assert adapter.query("JOB-1")["status"] == "running"

        fake_lqcloud.STATE["statuses"]["JOB-1"] = _FakeJobStatus.RUNNING
        assert adapter.query("JOB-1")["status"] == "running"

    def test_query_completed_returns_counts(self, adapter, fake_lqcloud):
        fake_lqcloud.STATE["statuses"]["JOB-1"] = _FakeJobStatus.COMPLETED
        fake_lqcloud.STATE["counts"]["JOB-1"] = {"00": 503, "11": 497}
        result = adapter.query("JOB-1")
        assert result["status"] == "success"
        # qiskit-style big-endian keys already match the uniqc convention.
        assert result["result"] == {"00": 503, "11": 497}

    def test_query_failed_and_cancelled(self, adapter, fake_lqcloud):
        fake_lqcloud.STATE["statuses"]["JOB-1"] = _FakeJobStatus.FAILED
        assert adapter.query("JOB-1")["status"] == "failed"

        fake_lqcloud.STATE["statuses"]["JOB-1"] = _FakeJobStatus.CANCELLED
        assert adapter.query("JOB-1")["status"] == "failed"

    def test_query_rebuilds_job_handle_by_id(self, adapter, fake_lqcloud):
        # query() must not need the original submit-time Job object.
        fake_lqcloud.STATE["statuses"]["external-job-9"] = _FakeJobStatus.COMPLETED
        fake_lqcloud.STATE["counts"]["external-job-9"] = {"0": 10, "1": 6}
        result = adapter.query("external-job-9")
        assert result["status"] == "success"
        assert result["result"] == {"0": 10, "1": 6}

    def test_query_batch_merges_statuses(self, adapter, fake_lqcloud):
        fake_lqcloud.STATE["statuses"]["JOB-1"] = _FakeJobStatus.COMPLETED
        fake_lqcloud.STATE["counts"]["JOB-1"] = {"00": 10}
        fake_lqcloud.STATE["statuses"]["JOB-2"] = _FakeJobStatus.RUNNING
        merged = adapter.query_batch(["JOB-1", "JOB-2"])
        assert merged["status"] == "running"

        fake_lqcloud.STATE["statuses"]["JOB-2"] = _FakeJobStatus.COMPLETED
        fake_lqcloud.STATE["counts"]["JOB-2"] = {"11": 8}
        merged = adapter.query_batch(["JOB-1", "JOB-2"])
        assert merged["status"] == "success"
        assert merged["result"] == [{"00": 10}, {"11": 8}]

        fake_lqcloud.STATE["statuses"]["JOB-2"] = _FakeJobStatus.FAILED
        merged = adapter.query_batch(["JOB-1", "JOB-2"])
        assert merged["status"] == "failed"


# ---------------------------------------------------------------------------
# list_backends / is_available
# ---------------------------------------------------------------------------


class TestLogicalQubitBackends:
    def test_list_backends(self, adapter):
        backends = adapter.list_backends()
        assert backends == [{"name": "lq-sim-1"}, {"name": "lq-qpu-1"}]

    def test_is_available_with_sdk_and_credentials(self, adapter):
        assert adapter.is_available() is True

    def test_is_available_false_without_credentials(self, monkeypatch, fake_lqcloud):
        from uniqc.backend_adapter.task.adapters import LogicalQubitAdapter

        def _raise():
            raise ImportError("no config")

        monkeypatch.setattr("uniqc.config.load_logicalqubit_config", _raise)
        assert LogicalQubitAdapter().is_available() is False

    def test_is_available_false_without_sdk(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "lqcloud", None)
        from uniqc.backend_adapter.task.adapters import LogicalQubitAdapter

        assert LogicalQubitAdapter().is_available() is False


# ---------------------------------------------------------------------------
# Dry-run (must not create the provider / touch the network)
# ---------------------------------------------------------------------------


class TestLogicalQubitDryRun:
    def test_dry_run_offline_success(self, monkeypatch):
        fake = _make_fake_lqcloud(explode_on_provider_init=True)
        monkeypatch.setitem(sys.modules, "lqcloud", fake)
        monkeypatch.setitem(sys.modules, "lqcloud.job", fake.job)
        monkeypatch.setattr(
            "uniqc.config.load_logicalqubit_config",
            lambda: {"api_key": "TEST-API-KEY", "url": "https://cloud.logicalqubit.com"},
        )

        from uniqc.backend_adapter.task.adapters import LogicalQubitAdapter

        result = LogicalQubitAdapter().dry_run(ORIGINIR_BELL, shots=100, backend_name="lq-sim-1")
        assert result.success is True
        assert result.circuit_qubits == 2
        assert result.backend_name == "lq-sim-1"
        assert "H" in result.supported_gates

    def test_dry_run_rejects_unsupported_gate(self, adapter):
        ir = "QINIT 1\nCREG 1\nRPhi q[0], (0.1, 0.2)"
        result = adapter.dry_run(ir, shots=100)
        assert result.success is False
        assert "RPhi" in result.error

    def test_dry_run_enforces_shots_limit(self, adapter):
        result = adapter.dry_run(ORIGINIR_BELL, shots=50001)
        assert result.success is False
        assert "50000" in result.error

        result = adapter.dry_run(ORIGINIR_BELL, shots=0)
        assert result.success is False

    def test_dry_run_fails_when_circuit_exceeds_cached_chip(self, adapter, monkeypatch):
        from uniqc.backend_adapter.backend_info import Platform
        from uniqc.cli.chip_info import ChipCharacterization

        chip = ChipCharacterization(
            platform=Platform.LOGICALQUBIT,
            chip_name="QZ01",
            full_id="logicalqubit:QZ01",
            available_qubits=(0, 1),
        )
        monkeypatch.setattr("uniqc.cli.chip_cache.get_chip", lambda platform, name: chip)

        ir = "QINIT 3\nCREG 3\nH q[0]\nCNOT q[1], q[2]"
        result = adapter.dry_run(ir, shots=100, backend_name="QZ01")
        assert result.success is False
        assert "[2]" in result.error

    def test_dry_run_skips_qubit_validation_without_chip_cache(self, adapter, monkeypatch):
        monkeypatch.setattr("uniqc.cli.chip_cache.get_chip", lambda platform, name: None)

        ir = "QINIT 3\nCREG 3\nH q[0]\nCNOT q[1], q[2]"
        result = adapter.dry_run(ir, shots=100, backend_name="QZ01")
        assert result.success is True


# ---------------------------------------------------------------------------
# Normaliser
# ---------------------------------------------------------------------------


class TestNormalizeLogicalQubit:
    def test_binary_keys_pass_through_unchanged(self):
        from uniqc.backend_adapter.task.normalizers import normalize_logicalqubit

        # qiskit-style big-endian: rightmost char is c[0] — same as uniqc.
        unified = normalize_logicalqubit({"01": 10, "11": 6}, task_id="j1")
        assert unified.platform == "logicalqubit"
        assert unified.counts == {"01": 10, "11": 6}

    def test_hex_keys_widened(self):
        from uniqc.backend_adapter.task.normalizers import normalize_logicalqubit

        unified = normalize_logicalqubit({"0x0": 5, "0x3": 7}, task_id="j2")
        assert unified.counts == {"00": 5, "11": 7}

    def test_result_object_with_get_counts(self):
        from uniqc.backend_adapter.task.normalizers import normalize_logicalqubit

        fake_result = types.SimpleNamespace(get_counts=lambda: {"10": 3})
        unified = normalize_logicalqubit(fake_result, task_id="j3")
        assert unified.counts == {"10": 3}


# ---------------------------------------------------------------------------
# Chip characterization (topology only — lqcloud exposes no calibration data)
# ---------------------------------------------------------------------------

_FAKE_BACKEND_CONFIG = {
    "name": "lq-qpu-1",
    "status": "active",
    "qubits": 3,
    "topology": {
        "type": "grid",
        "rows": 2,
        "cols": 2,
        "coupling_map": [[0, 1], [1, 2]],
    },
    "native_gates": None,
}


class TestLogicalQubitChipCharacterization:
    def test_builds_topology_only_model(self, adapter, fake_lqcloud):
        fake_lqcloud.STATE["backend_config"] = _FAKE_BACKEND_CONFIG

        chip = adapter.get_chip_characterization("lq-qpu-1")

        assert chip is not None
        assert chip.full_id == "logicalqubit:lq-qpu-1"
        assert chip.available_qubits == (0, 1, 2)
        assert [(e.u, e.v) for e in chip.connectivity] == [(0, 1), (1, 2)]
        # No calibration data from the platform — per-qubit fields stay None.
        assert chip.single_qubit_data[0].t1 is None
        assert chip.calibrated_at is None
        assert chip.global_info.two_qubit_gates == ("cz",)

    def test_returns_none_without_config(self, adapter):
        assert adapter.get_chip_characterization("lq-qpu-1") is None


class TestLogicalQubitNormaliser:
    def test_active_status_and_qubits_field(self):
        """lqcloud reports ``status: active`` and a ``qubits`` count field."""
        from uniqc.backend_adapter.backend_registry import _normalise_logicalqubit

        raw = [{"name": "QZ01", "status": "active", "qubits": 17, "type": "real_qpu"}]
        backend = _normalise_logicalqubit(raw)[0]

        assert backend.status == "available"
        assert backend.num_qubits == 17
        assert "qubits" not in backend.extra


class TestChipCacheTopologyFallback:
    def test_enriches_backend_info_from_chip_cache(self, monkeypatch):
        from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
        from uniqc.backend_adapter.task_manager import _enrich_backend_info_from_chip_cache
        from uniqc.cli import chip_cache
        from uniqc.cli.chip_info import ChipCharacterization

        entry = BackendInfo(platform=Platform.TIANYAN, name="tianyan176", num_qubits=176)
        chip = ChipCharacterization(
            platform=Platform.TIANYAN,
            chip_name="tianyan176",
            full_id="tianyan:tianyan176",
            available_qubits=(0, 1),
            connectivity=(QubitTopology(u=0, v=1),),
        )
        monkeypatch.setattr(chip_cache, "get_chip", lambda platform, name: chip)

        enriched = _enrich_backend_info_from_chip_cache(Platform.TIANYAN, entry)

        assert [(e.u, e.v) for e in enriched.topology] == [(0, 1)]
        assert enriched.extra["_uniqc_topology_source"] == "chip_cache"

    def test_keeps_existing_topology(self, monkeypatch):
        from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
        from uniqc.backend_adapter.task_manager import _enrich_backend_info_from_chip_cache
        from uniqc.cli.chip_info import ChipCharacterization

        entry = BackendInfo(
            platform=Platform.TIANYAN,
            name="tianyan176",
            num_qubits=66,
            topology=(QubitTopology(u=2, v=3),),
            extra={"num_qubits_source": "live_config"},
        )
        chip = ChipCharacterization(
            platform=Platform.TIANYAN,
            chip_name="tianyan176",
            full_id="tianyan:tianyan176",
            available_qubits=(0, 1),
            connectivity=(QubitTopology(u=0, v=1),),
        )
        monkeypatch.setattr("uniqc.cli.chip_cache.get_chip", lambda platform, name: chip)

        # Topology present and live-sourced qubit count -> nothing to enrich.
        assert _enrich_backend_info_from_chip_cache(Platform.TIANYAN, entry) is entry

    def test_corrects_name_derived_num_qubits_from_chip_cache(self, monkeypatch):
        from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology
        from uniqc.backend_adapter.task_manager import _enrich_backend_info_from_chip_cache
        from uniqc.cli.chip_info import ChipCharacterization

        entry = BackendInfo(
            platform=Platform.TIANYAN,
            name="tianyan176",
            num_qubits=176,  # derived from the machine *name*
            topology=(QubitTopology(u=2, v=3),),
            extra={"num_qubits_source": "machine_name"},
        )
        chip = ChipCharacterization(
            platform=Platform.TIANYAN,
            chip_name="tianyan176",
            full_id="tianyan:tianyan176",
            available_qubits=tuple(range(66)),
        )
        monkeypatch.setattr("uniqc.cli.chip_cache.get_chip", lambda platform, name: chip)

        enriched = _enrich_backend_info_from_chip_cache(Platform.TIANYAN, entry)

        assert enriched.num_qubits == 66
        assert enriched.extra["_uniqc_num_qubits_source"] == "chip_cache"
        # Existing topology is preserved.
        assert [(e.u, e.v) for e in enriched.topology] == [(2, 3)]

    def test_live_sourced_num_qubits_is_never_clobbered(self, monkeypatch):
        from uniqc.backend_adapter.backend_info import BackendInfo, Platform
        from uniqc.backend_adapter.task_manager import _enrich_backend_info_from_chip_cache
        from uniqc.cli.chip_info import ChipCharacterization

        entry = BackendInfo(
            platform=Platform.ORIGINQ,
            name="WK_C180",
            num_qubits=180,
            extra={"num_qubits_source": "live_config"},
        )
        # Stale chip cache disagreeing with the live count must not win.
        chip = ChipCharacterization(
            platform=Platform.ORIGINQ,
            chip_name="WK_C180",
            full_id="originq:WK_C180",
            available_qubits=tuple(range(72)),
        )
        monkeypatch.setattr("uniqc.cli.chip_cache.get_chip", lambda platform, name: chip)

        assert _enrich_backend_info_from_chip_cache(Platform.ORIGINQ, entry) is entry
