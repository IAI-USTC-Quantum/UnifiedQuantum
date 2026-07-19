"""Integration tests for ``dummy:virtual:<name>`` noisy virtual machines."""

from __future__ import annotations

import textwrap

import pytest

from uniqc.backend_adapter import virtual_machine as vm

DEMO_YAML = textwrap.dedent("""\
    description: 2-qubit noisy demo
    num_qubits: 2
    topology:
      - [0, 1]
    noise:
      depolarizing:
        1q: 0.0
        2q: 0.0
      readout:
        default: [0.0, 1.0]
""")

BELL = "QINIT 2\nCREG 2\nX q[0]\nMEASURE q[0], c[0]\nMEASURE q[1], c[1]\n"


@pytest.fixture
def virtual_dir(tmp_path, monkeypatch):
    """Redirect the virtual machine directory to a tmp path with one config."""
    (tmp_path / "demo.yaml").write_text(DEMO_YAML, encoding="utf-8")
    monkeypatch.setattr(vm, "DEFAULT_VIRTUAL_DIR", tmp_path)
    return tmp_path


def test_resolve_virtual_machine(virtual_dir):
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:virtual:demo", allow_fetch=False)

    assert spec.identifier == "dummy:virtual:demo"
    assert spec.name == "virtual:demo"
    assert spec.available_qubits == [0, 1]
    assert spec.available_topology == [[0, 1]]
    assert spec.noise_source == "virtual_config"
    assert spec.readout_error == {0: [0.0, 1.0], 1: [0.0, 1.0]}
    # depol rates are 0.0 → no gate error loader.
    assert spec.error_loader is None


def test_resolve_virtual_machine_missing_config(virtual_dir):
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    with pytest.raises(ValueError, match="not found"):
        resolve_dummy_backend("dummy:virtual:absent", allow_fetch=False)


def test_virtual_machine_listed_in_backend_infos(virtual_dir):
    from uniqc.backend_adapter.dummy_backend import list_dummy_backend_infos

    infos = {b.name: b for b in list_dummy_backend_infos()}
    assert "virtual:demo" in infos
    info = infos["virtual:demo"]
    assert info.extra["dummy_kind"] == "virtual-noisy"
    assert info.extra["noise_source"] == "virtual_config"
    assert info.num_qubits == 2


def test_invalid_virtual_machine_skipped_in_backend_infos(virtual_dir):
    (virtual_dir / "broken.yaml").write_text("num_qubits: 2\ntopology:\n  - [0, 9]\n", encoding="utf-8")
    from uniqc.backend_adapter.dummy_backend import list_dummy_backend_infos

    with pytest.warns(UserWarning, match="Skipping invalid virtual machine"):
        infos = list_dummy_backend_infos()
    assert "virtual:broken" not in {b.name for b in infos}


def test_noise_model_override_disables_virtual_noise(virtual_dir):
    from uniqc.backend_adapter.dummy_backend import resolve_dummy_backend

    spec = resolve_dummy_backend("dummy:virtual:demo", allow_fetch=False, noise_model={"depol": 0.01})

    assert spec.noise_source == "noise_model"
    assert spec.error_loader is None
    assert spec.readout_error is None


def test_parse_backend_target_virtual():
    from uniqc.backend_adapter.preflight import parse_backend_target

    target = parse_backend_target("dummy:virtual:demo")
    assert target.kind == "virtual"
    assert target.virtual_name == "demo"
    assert not target.needs_provider_sdk

    with pytest.raises(ValueError, match="Malformed dummy backend identifier"):
        parse_backend_target("dummy:virtual:")


@pytest.mark.requires_cpp
def test_ensure_backend_ready_virtual(virtual_dir):
    from uniqc.backend_adapter.preflight import ensure_backend_ready

    assert ensure_backend_ready("dummy:virtual:demo") is None
    with pytest.raises(ValueError, match="not found"):
        ensure_backend_ready("dummy:virtual:absent")


@pytest.mark.requires_cpp
def test_virtual_machine_end_to_end_readout_noise(virtual_dir):
    """p(1->0)=1.0 readout must flip every '1' measurement to '0'."""
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    noisy = DummyAdapter(**dummy_adapter_kwargs("dummy:virtual:demo"))
    task_id = noisy.submit(BELL, shots=200)
    result = noisy.query(task_id)
    assert result["status"] == "success"
    counts = result["result"]
    assert counts == {"00": 200}

    ideal = DummyAdapter(backend_id="dummy:local:simulator")
    ideal_result = ideal.query(ideal.submit(BELL, shots=200))
    assert ideal_result["result"] == {"01": 200}


@pytest.mark.requires_cpp
def test_virtual_machine_end_to_end_gate_noise(virtual_dir):
    """A virtual machine with extreme 1q depolarizing scrambles an X q[0] circuit."""
    (virtual_dir / "demo.yaml").write_text(
        textwrap.dedent("""\
        num_qubits: 2
        topology:
          - [0, 1]
        noise:
          depolarizing:
            1q: 0.5
        """),
        encoding="utf-8",
    )
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    noisy = DummyAdapter(**dummy_adapter_kwargs("dummy:virtual:demo"))
    result = noisy.query(noisy.submit(BELL, shots=1000))
    assert result["status"] == "success"
    counts = result["result"]
    # With 50% per-gate depolarizing, qubit 0 must show both outcomes often.
    assert counts.get("00", 0) > 100 and counts.get("01", 0) > 100


@pytest.mark.requires_cpp
def test_virtual_machine_topology_enforced(virtual_dir):
    """2q gates outside the configured topology fail the task."""
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    adapter = DummyAdapter(**dummy_adapter_kwargs("dummy:virtual:demo"))
    bad = "QINIT 3\nCREG 3\nCNOT q[0], q[2]\nMEASURE q[0], c[0]\n"
    result = adapter.query(adapter.submit(bad, shots=10))
    assert result["status"] == "failed"
    assert "qubit" in result["error"].lower()


@pytest.mark.requires_cpp
def test_virtual_machine_dry_run(virtual_dir):
    from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs
    from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

    adapter = DummyAdapter(**dummy_adapter_kwargs("dummy:virtual:demo"))
    assert adapter.dry_run(BELL, shots=10).success
