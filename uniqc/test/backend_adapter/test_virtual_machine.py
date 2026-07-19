"""Tests for user-defined noisy virtual machines (~/.uniqc/backend/virtual/)."""

from __future__ import annotations

import math
import textwrap

import pytest

from uniqc.backend_adapter import virtual_machine as vm
from uniqc.simulator.error_model import (
    Depolarizing,
    ThermalRelaxation,
    TwoQubitDepolarizing,
)

FULL_CONFIG = textwrap.dedent("""\
    description: test machine
    num_qubits: 4
    topology:
      - [0, 1]
      - [1, 2]
      - [2, 3]
    gate_times_ns:
      default_1q: 30
      default_2q: 80
      CZ: 120
    noise:
      depolarizing:
        1q: 0.001
        2q: 0.01
      gate_type:
        CZ: {depolarizing: 0.02}
        H: 0.0005
      gate_instance:
        - {gate: CZ, qubits: [1, 0], depolarizing: 0.05}
        - {gate: H,  qubits: [2],  depolarizing: 0.003}
      thermal_relaxation:
        default: {t1_us: 50, t2_us: 40}
        qubits:
          2: {t1_us: 30, t2_us: 25}
      readout:
        default: [0.02, 0.02]
        qubits:
          3: [0.05, 0.08]
""")


def _write(tmp_path, text, name="test-bm"):
    path = tmp_path / f"{name}.yaml"
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


def test_load_full_config(tmp_path):
    _write(tmp_path, FULL_CONFIG)
    config = vm.load_virtual_machine("test-bm", tmp_path)

    assert config.name == "test-bm"
    assert config.description == "test machine"
    assert config.qubits == (0, 1, 2, 3)
    assert config.topology == ((0, 1), (1, 2), (2, 3))
    assert config.gate_times_ns["default_1q"] == 30.0
    assert config.gate_times_ns["CZ"] == 120.0
    assert config.depol_1q == 0.001
    assert config.depol_2q == 0.01
    assert config.gate_type_depol == {"CZ": 0.02, "H": 0.0005}
    # CZ instance qubits are normalised to sorted order (matches the loader).
    assert config.gate_instance_depol == {("CZ", (0, 1)): 0.05, ("H", (2,)): 0.003}
    # T1/T2 merge: per-qubit override wins, default covers the rest.
    assert config.t1_us == {0: 50.0, 1: 50.0, 2: 30.0, 3: 50.0}
    assert config.t2_us == {0: 40.0, 1: 40.0, 2: 25.0, 3: 40.0}
    assert config.readout[3] == (0.05, 0.08)
    assert config.readout[0] == (0.02, 0.02)


def test_load_qubits_list_and_yml_suffix(tmp_path):
    path = tmp_path / "m.yml"
    path.write_text("qubits: [0, 2, 5]\n", encoding="utf-8")
    config = vm.load_virtual_machine("m", tmp_path)
    assert config.qubits == (0, 2, 5)
    assert config.topology == ()


def test_load_rejects_bad_names(tmp_path):
    for bad in ("../escape", "a:b", "", "white space", "a/b"):
        with pytest.raises(ValueError, match="Invalid virtual machine name"):
            vm.load_virtual_machine(bad, tmp_path)


def test_load_missing_file_reports_path_and_hint(tmp_path):
    with pytest.raises(ValueError, match=r"not found.*uniqc backend virtual init"):
        vm.load_virtual_machine("missing", tmp_path)


def test_load_rejects_unknown_top_level_key(tmp_path):
    _write(tmp_path, "num_qubits: 2\nbogus_key: 1\n")
    with pytest.raises(ValueError, match="unknown top-level keys"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_both_qubits_and_num_qubits(tmp_path):
    _write(tmp_path, "num_qubits: 2\nqubits: [0, 1]\n")
    with pytest.raises(ValueError, match="only one of 'qubits' / 'num_qubits'"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_probability_out_of_range(tmp_path):
    _write(tmp_path, "num_qubits: 2\nnoise:\n  depolarizing:\n    1q: 1.5\n")
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_topology_with_undeclared_qubit(tmp_path):
    _write(tmp_path, "num_qubits: 2\ntopology:\n  - [0, 5]\n")
    with pytest.raises(ValueError, match="undeclared qubit 5"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_instance_edge_outside_topology(tmp_path):
    _write(
        tmp_path,
        "num_qubits: 3\ntopology:\n  - [0, 1]\nnoise:\n  gate_instance:\n"
        "    - {gate: CZ, qubits: [0, 2], depolarizing: 0.1}\n",
    )
    with pytest.raises(ValueError, match="not part of the declared topology"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_gate_arity_mismatch(tmp_path):
    _write(
        tmp_path,
        "num_qubits: 2\ntopology:\n  - [0, 1]\nnoise:\n  gate_instance:\n"
        "    - {gate: H, qubits: [0, 1], depolarizing: 0.1}\n",
    )
    with pytest.raises(ValueError, match="acts on 1 qubit"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_t2_above_2t1(tmp_path):
    _write(
        tmp_path,
        "num_qubits: 1\ngate_times_ns:\n  default_1q: 30\nnoise:\n"
        "  thermal_relaxation:\n    default: {t1_us: 10, t2_us: 30}\n",
    )
    with pytest.raises(ValueError, match=r"T2 .* 2\*T1"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_thermal_without_gate_times(tmp_path):
    _write(
        tmp_path,
        "num_qubits: 1\nnoise:\n  thermal_relaxation:\n    default: {t1_us: 50}\n",
    )
    with pytest.raises(ValueError, match="requires 'gate_times_ns'"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_bad_readout_pair(tmp_path):
    _write(tmp_path, "num_qubits: 1\nnoise:\n  readout:\n    default: [0.5]\n")
    with pytest.raises(ValueError, match=r"\[p\(0->1\), p\(1->0\)\]"):
        vm.load_virtual_machine("test-bm", tmp_path)


def test_load_rejects_unknown_gate(tmp_path):
    _write(tmp_path, "num_qubits: 1\nnoise:\n  gate_type:\n    FOOGATE: 0.1\n")
    with pytest.raises(ValueError, match="unknown gate"):
        vm.load_virtual_machine("test-bm", tmp_path)


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def test_scan_reports_valid_and_invalid(tmp_path):
    _write(tmp_path, "num_qubits: 2\n", name="good")
    _write(tmp_path, "num_qubits: 2\ntopology:\n  - [0, 9]\n", name="bad")
    (tmp_path / "notes.txt").write_text("not a config", encoding="utf-8")

    entries = {e.name: e for e in vm.scan_virtual_machines(tmp_path)}
    assert set(entries) == {"good", "bad"}
    assert entries["good"].config is not None and entries["good"].error is None
    assert entries["bad"].config is None and entries["bad"].error is not None


def test_list_virtual_machines_skips_invalid_with_warning(tmp_path):
    _write(tmp_path, "num_qubits: 2\n", name="good")
    _write(tmp_path, "num_qubits: 2\ntopology:\n  - [0, 9]\n", name="bad")
    with pytest.warns(UserWarning, match="Skipping invalid virtual machine"):
        configs = vm.list_virtual_machines(tmp_path)
    assert [c.name for c in configs] == ["good"]


# ---------------------------------------------------------------------------
# Noise construction
# ---------------------------------------------------------------------------


def test_build_error_loader_layers(tmp_path):
    _write(tmp_path, FULL_CONFIG)
    config = vm.load_virtual_machine("test-bm", tmp_path)
    loader = vm.build_error_loader(config)

    # Uniform 1q: every 1q gate carries Depolarizing(0.001); 2q gates must not.
    h_models = loader.gatetype_error["H"]
    assert any(isinstance(m, Depolarizing) and m.p == 0.001 for m in h_models)
    assert not any(isinstance(m, Depolarizing) and m.p == 0.001 for m in loader.gatetype_error["CZ"])
    # Uniform 2q: true two-qubit channel on every 2q gate.
    assert any(isinstance(m, TwoQubitDepolarizing) and m.p == 0.01 for m in loader.gatetype_error["CNOT"])
    # Gate-type override stacked on the same gate.
    assert any(isinstance(m, TwoQubitDepolarizing) and m.p == 0.02 for m in loader.gatetype_error["CZ"])
    # Per-instance entries.
    assert loader.gate_specific_error[("CZ", (0, 1))][0].p == 0.05
    assert loader.gate_specific_error[("H", (2,))][0].p == 0.003
    # Thermal relaxation attached per gate type with the right duration:
    # CZ uses its 120 ns override, H falls back to default_1q.
    cz_thermal = [m for m in loader.gatetype_error["CZ"] if isinstance(m, ThermalRelaxation)]
    assert len(cz_thermal) == 1 and cz_thermal[0].gate_time_ns == 120.0
    h_thermal = [m for m in loader.gatetype_error["H"] if isinstance(m, ThermalRelaxation)]
    assert len(h_thermal) == 1 and h_thermal[0].gate_time_ns == 30.0
    # T1/T2 converted to ns.
    assert h_thermal[0].t1_ns[0] == 50_000.0


def test_build_error_loader_none_without_noise(tmp_path):
    _write(tmp_path, "num_qubits: 2\n")
    config = vm.load_virtual_machine("test-bm", tmp_path)
    assert vm.build_error_loader(config) is None
    assert vm.build_readout_error(config) == {}


def test_build_readout_error_merges_default_and_overrides(tmp_path):
    _write(tmp_path, FULL_CONFIG)
    config = vm.load_virtual_machine("test-bm", tmp_path)
    readout = vm.build_readout_error(config)
    assert readout[3] == [0.05, 0.08]
    assert readout[0] == [0.02, 0.02]


def test_thermal_relaxation_rates_from_yaml(tmp_path):
    """End-to-end numeric check: YAML T1/T2/times -> opcode probabilities."""
    _write(tmp_path, FULL_CONFIG)
    config = vm.load_virtual_machine("test-bm", tmp_path)
    loader = vm.build_error_loader(config)
    thermal = [m for m in loader.gatetype_error["CZ"] if isinstance(m, ThermalRelaxation)][0]

    opcodes = thermal.generate_error_opcode([0, 1])
    t, t1, t2 = 120.0, 50_000.0, 40_000.0
    gamma = 1.0 - math.exp(-t / t1)
    p_phi = 0.5 * (1.0 - math.exp(-t * (1.0 / t2 - 1.0 / (2.0 * t1))))
    assert opcodes == [
        ("AmplitudeDamping", 0, None, pytest.approx(gamma), None, None),
        ("PhaseFlip", 0, None, pytest.approx(p_phi), None, None),
        ("AmplitudeDamping", 1, None, pytest.approx(gamma), None, None),
        ("PhaseFlip", 1, None, pytest.approx(p_phi), None, None),
    ]


# ---------------------------------------------------------------------------
# Template scaffolding
# ---------------------------------------------------------------------------


def test_create_template_roundtrip(tmp_path):
    path = vm.create_virtual_machine_template("demo", tmp_path)
    assert path.name == "demo.yaml"
    config = vm.load_virtual_machine("demo", tmp_path)
    assert config.qubits


def test_create_template_refuses_overwrite(tmp_path):
    vm.create_virtual_machine_template("demo", tmp_path)
    with pytest.raises(FileExistsError):
        vm.create_virtual_machine_template("demo", tmp_path)
    vm.create_virtual_machine_template("demo", tmp_path, force=True)
