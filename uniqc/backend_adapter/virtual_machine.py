"""User-defined noisy virtual machines under ``~/.uniqc/backend/virtual/``.

Each ``*.yaml`` file in that directory describes one noisy virtual machine:
qubit set, coupling topology, and a layered gate error model (uniform
per-arity depolarizing, per-gate-type and per-gate-instance overrides, T1/T2
thermal relaxation, and per-qubit readout error).

A configured machine is referenced through the dummy platform as
``dummy:virtual:<name>`` (filename stem)::

    submit_task(circuit, backend="dummy:virtual:my-machine", shots=1000)

YAML schema
-----------
.. code-block:: yaml

    description: 6-qubit noisy virtual machine
    qubits: [0, 1, 2, 3, 4, 5]        # or: num_qubits: 6
    topology:                          # optional; omit for all-to-all
      - [0, 1]
      - [1, 2]
    gate_times_ns:                     # required when thermal_relaxation is used
      default_1q: 30
      default_2q: 80
      CZ: 120                          # optional per-gate override
    noise:
      depolarizing:                    # uniform, per gate arity
        1q: 0.001                      #   every single-qubit gate
        2q: 0.01                       #   every two-qubit gate (true 2q channel)
      gate_type:                       # per gate type, stacked on top of the above
        CZ: {depolarizing: 0.015}
        H: 0.0005                      # bare-float shorthand
      gate_instance:                   # per (gate, qubits) instance
        - {gate: CZ, qubits: [0, 1], depolarizing: 0.04}
        - {gate: H,  qubits: [3],  depolarizing: 0.002}
      thermal_relaxation:              # per-qubit T1/T2 (microseconds)
        default: {t1_us: 50, t2_us: 40}
        qubits:
          2: {t1_us: 30, t2_us: 25}
      readout:                         # [p(0->1), p(1->0)]
        default: [0.02, 0.02]
        qubits:
          4: [0.05, 0.08]
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_VIRTUAL_DIR",
    "VirtualMachineConfig",
    "VirtualMachineScan",
    "load_virtual_machine",
    "scan_virtual_machines",
    "list_virtual_machines",
    "build_error_loader",
    "build_readout_error",
    "create_virtual_machine_template",
]

import dataclasses
import re
import warnings
from pathlib import Path
from typing import Any

import yaml

from uniqc.circuit_builder.originir_spec import available_originir_gates

DEFAULT_VIRTUAL_DIR = Path.home() / ".uniqc" / "backend" / "virtual"

_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_TOP_LEVEL_KEYS = {"description", "qubits", "num_qubits", "topology", "gate_times_ns", "noise"}
_NOISE_KEYS = {"depolarizing", "gate_type", "gate_instance", "thermal_relaxation", "readout"}
_GATE_TIME_DEFAULT_KEYS = {"default_1q", "default_2q"}
_US_TO_NS = 1000.0


@dataclasses.dataclass(frozen=True, slots=True)
class VirtualMachineConfig:
    """Parsed and validated user-defined noisy virtual machine."""

    name: str
    description: str = ""
    qubits: tuple[int, ...] = ()
    topology: tuple[tuple[int, int], ...] = ()  # normalised (min, max) edges
    gate_times_ns: dict[str, float] = dataclasses.field(default_factory=dict)
    depol_1q: float | None = None
    depol_2q: float | None = None
    gate_type_depol: dict[str, float] = dataclasses.field(default_factory=dict)
    gate_instance_depol: dict[tuple[str, tuple[int, ...]], float] = dataclasses.field(default_factory=dict)
    t1_us: dict[int, float] = dataclasses.field(default_factory=dict)  # effective per-qubit
    t2_us: dict[int, float] = dataclasses.field(default_factory=dict)  # effective per-qubit
    readout: dict[int, tuple[float, float]] = dataclasses.field(default_factory=dict)  # (p01, p10)
    source_path: str = ""


@dataclasses.dataclass(frozen=True, slots=True)
class VirtualMachineScan:
    """Result of scanning one ``*.yaml`` file in the virtual machine directory."""

    name: str
    path: Path
    config: VirtualMachineConfig | None
    error: str | None


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


def _fail(path: Path, message: str) -> None:
    raise ValueError(f"{path}: {message}")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_probability(path: Path, value: Any, where: str) -> float:
    if not _is_number(value) or not 0.0 <= float(value) <= 1.0:
        _fail(path, f"{where} must be a number in [0, 1], got {value!r}")
    return float(value)


def _check_positive_time(path: Path, value: Any, where: str) -> float:
    if not _is_number(value) or float(value) <= 0:
        _fail(path, f"{where} must be a positive number, got {value!r}")
    return float(value)


def _parse_qubits(path: Path, raw: dict[str, Any]) -> tuple[int, ...]:
    has_qubits = "qubits" in raw
    has_num = "num_qubits" in raw
    if has_qubits and has_num:
        _fail(path, "declare only one of 'qubits' / 'num_qubits'")
    if has_num:
        n = raw["num_qubits"]
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            _fail(path, f"num_qubits must be a positive integer, got {n!r}")
        return tuple(range(n))
    if not has_qubits:
        _fail(path, "missing qubit declaration: set 'qubits' or 'num_qubits'")
    qubits = raw["qubits"]
    if not isinstance(qubits, list) or not qubits:
        _fail(path, "qubits must be a non-empty list of integer indices")
    parsed: list[int] = []
    for q in qubits:
        if not isinstance(q, int) or isinstance(q, bool) or q < 0:
            _fail(path, f"qubits entries must be non-negative integers, got {q!r}")
        parsed.append(q)
    if len(set(parsed)) != len(parsed):
        _fail(path, f"qubits contains duplicates: {parsed}")
    return tuple(parsed)


def _parse_topology(path: Path, raw: Any, qubit_set: set[int]) -> tuple[tuple[int, int], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        _fail(path, "topology must be a list of [u, v] edges")
    edges: list[tuple[int, int]] = []
    for i, edge in enumerate(raw):
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or not all(isinstance(q, int) and not isinstance(q, bool) for q in edge)
        ):
            _fail(path, f"topology edge #{i} must be a [u, v] pair of integers, got {edge!r}")
        u, v = int(edge[0]), int(edge[1])
        if u == v:
            _fail(path, f"topology edge #{i} is a self-loop on qubit {u}")
        for q in (u, v):
            if q not in qubit_set:
                _fail(path, f"topology edge [{u}, {v}] references undeclared qubit {q}")
        edges.append((min(u, v), max(u, v)))
    return tuple(sorted(set(edges)))


def _parse_gate_times(path: Path, raw: Any) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _fail(path, "gate_times_ns must be a mapping")
    times: dict[str, float] = {}
    for key, value in raw.items():
        key_str = str(key)
        if key_str in _GATE_TIME_DEFAULT_KEYS:
            canon = key_str
        else:
            canon = key_str.upper()
            if canon not in available_originir_gates:
                _fail(path, f"gate_times_ns: unknown key '{key_str}' (use default_1q/default_2q or a gate name)")
        times[canon] = _check_positive_time(path, value, f"gate_times_ns.{key_str}")
    return times


def _parse_gate_type(path: Path, raw: Any) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _fail(path, "noise.gate_type must be a mapping of gate name to error spec")
    parsed: dict[str, float] = {}
    for key, value in raw.items():
        gate = str(key).upper()
        spec = available_originir_gates.get(gate)
        if spec is None:
            _fail(path, f"noise.gate_type: unknown gate '{key}'")
        if spec["qubit"] not in (1, 2):
            _fail(path, f"noise.gate_type: gate '{gate}' is not a 1q/2q gate and cannot carry gate noise")
        if _is_number(value):
            prob = _check_probability(path, value, f"noise.gate_type.{gate}")
        elif isinstance(value, dict):
            unknown = set(value) - {"depolarizing"}
            if unknown:
                _fail(path, f"noise.gate_type.{gate}: unknown keys {sorted(unknown)} (supported: depolarizing)")
            if "depolarizing" not in value:
                _fail(path, f"noise.gate_type.{gate}: missing 'depolarizing' rate")
            prob = _check_probability(path, value["depolarizing"], f"noise.gate_type.{gate}.depolarizing")
        else:
            _fail(path, f"noise.gate_type.{gate}: expected a number or a mapping, got {value!r}")
        parsed[gate] = prob
    return parsed


def _parse_gate_instance(
    path: Path,
    raw: Any,
    qubit_set: set[int],
    topology: tuple[tuple[int, int], ...],
) -> dict[tuple[str, tuple[int, ...]], float]:
    if raw is None:
        return {}
    if not isinstance(raw, list):
        _fail(path, "noise.gate_instance must be a list of {gate, qubits, depolarizing} entries")
    topology_set = set(topology)
    parsed: dict[tuple[str, tuple[int, ...]], float] = {}
    for i, entry in enumerate(raw):
        where = f"noise.gate_instance[{i}]"
        if not isinstance(entry, dict):
            _fail(path, f"{where} must be a mapping, got {entry!r}")
        unknown = set(entry) - {"gate", "qubits", "depolarizing"}
        if unknown:
            _fail(path, f"{where}: unknown keys {sorted(unknown)} (supported: gate, qubits, depolarizing)")
        for required in ("gate", "qubits", "depolarizing"):
            if required not in entry:
                _fail(path, f"{where}: missing '{required}'")
        gate = str(entry["gate"]).upper()
        spec = available_originir_gates.get(gate)
        if spec is None:
            _fail(path, f"{where}: unknown gate '{entry['gate']}'")
        qubits = entry["qubits"]
        if (
            not isinstance(qubits, list)
            or not qubits
            or not all(isinstance(q, int) and not isinstance(q, bool) for q in qubits)
        ):
            _fail(path, f"{where}.qubits must be a list of integer qubit indices, got {qubits!r}")
        if len(qubits) != spec["qubit"]:
            _fail(path, f"{where}: gate '{gate}' acts on {spec['qubit']} qubit(s), got {qubits}")
        if len(set(qubits)) != len(qubits):
            _fail(path, f"{where}.qubits contains duplicates: {qubits}")
        for q in qubits:
            if q not in qubit_set:
                _fail(path, f"{where}: qubit {q} is not in the declared qubit set")
        normalised = tuple(sorted(qubits)) if gate == "CZ" else tuple(qubits)
        if len(qubits) == 2 and topology_set and tuple(sorted(qubits)) not in topology_set:
            _fail(path, f"{where}: edge {sorted(qubits)} is not part of the declared topology")
        prob = _check_probability(path, entry["depolarizing"], f"{where}.depolarizing")
        parsed[(gate, normalised)] = prob
    return parsed


def _parse_thermal_relaxation(
    path: Path,
    raw: Any,
    qubits: tuple[int, ...],
    gate_times_ns: dict[str, float],
) -> tuple[dict[int, float], dict[int, float]]:
    if raw is None:
        return {}, {}
    if not isinstance(raw, dict):
        _fail(path, "noise.thermal_relaxation must be a mapping with 'default' and/or 'qubits'")
    unknown = set(raw) - {"default", "qubits"}
    if unknown:
        _fail(path, f"noise.thermal_relaxation: unknown keys {sorted(unknown)} (supported: default, qubits)")
    if not gate_times_ns:
        _fail(path, "noise.thermal_relaxation requires 'gate_times_ns' to be configured")

    def _parse_entry(value: Any, where: str) -> dict[str, float]:
        if not isinstance(value, dict):
            _fail(path, f"{where} must be a mapping with t1_us and/or t2_us")
        unknown_keys = set(value) - {"t1_us", "t2_us"}
        if unknown_keys:
            _fail(path, f"{where}: unknown keys {sorted(unknown_keys)} (supported: t1_us, t2_us)")
        if not value:
            _fail(path, f"{where}: at least one of t1_us / t2_us is required")
        return {key: _check_positive_time(path, v, f"{where}.{key}") for key, v in value.items()}

    default = _parse_entry(raw["default"], "noise.thermal_relaxation.default") if "default" in raw else {}
    per_qubit_raw = raw.get("qubits") or {}
    if not isinstance(per_qubit_raw, dict):
        _fail(path, "noise.thermal_relaxation.qubits must be a mapping of qubit index to T1/T2")
    per_qubit: dict[int, dict[str, float]] = {}
    for key, value in per_qubit_raw.items():
        q = int(key) if _is_number(key) else None
        if q is None or q not in set(qubits):
            _fail(path, f"noise.thermal_relaxation.qubits: qubit {key!r} is not in the declared qubit set")
        per_qubit[q] = _parse_entry(value, f"noise.thermal_relaxation.qubits.{key}")
    if not default and not per_qubit:
        _fail(path, "noise.thermal_relaxation: configure 'default' and/or 'qubits'")

    t1_us: dict[int, float] = {}
    t2_us: dict[int, float] = {}
    for q in qubits:
        entry = {**default, **per_qubit.get(q, {})}
        t1 = entry.get("t1_us")
        t2 = entry.get("t2_us")
        if t1 is not None and t2 is not None and t2 > 2.0 * t1:
            _fail(path, f"noise.thermal_relaxation: qubit {q} has T2 ({t2} us) > 2*T1 ({t1} us)")
        if t1 is not None:
            t1_us[q] = t1
        if t2 is not None:
            t2_us[q] = t2
    return t1_us, t2_us


def _parse_readout(path: Path, raw: Any, qubits: tuple[int, ...]) -> dict[int, tuple[float, float]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _fail(path, "noise.readout must be a mapping with 'default' and/or 'qubits'")
    unknown = set(raw) - {"default", "qubits"}
    if unknown:
        _fail(path, f"noise.readout: unknown keys {sorted(unknown)} (supported: default, qubits)")

    def _parse_pair(value: Any, where: str) -> tuple[float, float]:
        if not isinstance(value, list) or len(value) != 2:
            _fail(path, f"{where} must be a [p(0->1), p(1->0)] pair, got {value!r}")
        return (
            _check_probability(path, value[0], f"{where}[0]"),
            _check_probability(path, value[1], f"{where}[1]"),
        )

    default = _parse_pair(raw["default"], "noise.readout.default") if "default" in raw else None
    per_qubit_raw = raw.get("qubits") or {}
    if not isinstance(per_qubit_raw, dict):
        _fail(path, "noise.readout.qubits must be a mapping of qubit index to [p01, p10]")
    readout: dict[int, tuple[float, float]] = {}
    if default is not None:
        for q in qubits:
            readout[q] = default
    for key, value in per_qubit_raw.items():
        q = int(key) if _is_number(key) else None
        if q is None or q not in set(qubits):
            _fail(path, f"noise.readout.qubits: qubit {key!r} is not in the declared qubit set")
        readout[q] = _parse_pair(value, f"noise.readout.qubits.{key}")
    return readout


def _parse_config(name: str, raw: dict[str, Any], path: Path) -> VirtualMachineConfig:
    unknown = set(raw) - _TOP_LEVEL_KEYS
    if unknown:
        _fail(path, f"unknown top-level keys {sorted(unknown)} (supported: {sorted(_TOP_LEVEL_KEYS)})")

    description = raw.get("description") or ""
    if not isinstance(description, str):
        _fail(path, "description must be a string")

    qubits = _parse_qubits(path, raw)
    qubit_set = set(qubits)
    topology = _parse_topology(path, raw.get("topology"), qubit_set)
    gate_times_ns = _parse_gate_times(path, raw.get("gate_times_ns"))

    noise = raw.get("noise") or {}
    if not isinstance(noise, dict):
        _fail(path, "noise must be a mapping")
    unknown_noise = set(noise) - _NOISE_KEYS
    if unknown_noise:
        _fail(path, f"unknown noise keys {sorted(unknown_noise)} (supported: {sorted(_NOISE_KEYS)})")

    depol_1q = depol_2q = None
    depolarizing = noise.get("depolarizing")
    if depolarizing is not None:
        if not isinstance(depolarizing, dict):
            _fail(path, "noise.depolarizing must be a mapping with '1q' and/or '2q' rates")
        unknown_depol = set(depolarizing) - {"1q", "2q"}
        if unknown_depol:
            _fail(path, f"noise.depolarizing: unknown keys {sorted(unknown_depol)} (supported: 1q, 2q)")
        if "1q" in depolarizing:
            depol_1q = _check_probability(path, depolarizing["1q"], "noise.depolarizing.1q")
        if "2q" in depolarizing:
            depol_2q = _check_probability(path, depolarizing["2q"], "noise.depolarizing.2q")

    gate_type_depol = _parse_gate_type(path, noise.get("gate_type"))
    gate_instance_depol = _parse_gate_instance(path, noise.get("gate_instance"), qubit_set, topology)
    t1_us, t2_us = _parse_thermal_relaxation(path, noise.get("thermal_relaxation"), qubits, gate_times_ns)
    readout = _parse_readout(path, noise.get("readout"), qubits)

    return VirtualMachineConfig(
        name=name,
        description=description,
        qubits=qubits,
        topology=topology,
        gate_times_ns=gate_times_ns,
        depol_1q=depol_1q,
        depol_2q=depol_2q,
        gate_type_depol=gate_type_depol,
        gate_instance_depol=gate_instance_depol,
        t1_us=t1_us,
        t2_us=t2_us,
        readout=readout,
        source_path=str(path),
    )


def _find_config_file(name: str, virtual_dir: Path) -> Path | None:
    for suffix in (".yaml", ".yml"):
        path = virtual_dir / f"{name}{suffix}"
        if path.is_file():
            return path
    return None


def load_virtual_machine(name: str, virtual_dir: Path | None = None) -> VirtualMachineConfig:
    """Load and validate the virtual machine ``<name>.yaml`` from the config directory.

    Args:
        name: Virtual machine name (filename stem). Only letters, digits,
            ``-`` and ``_`` are allowed.
        virtual_dir: Directory to search. Defaults to
            ``~/.uniqc/backend/virtual/``.

    Returns:
        The validated :class:`VirtualMachineConfig`.

    Raises:
        ValueError: If the name is invalid, the file is missing, or the
            configuration fails validation.
    """
    if not name or not _NAME_RE.match(name):
        raise ValueError(f"Invalid virtual machine name {name!r}: only letters, digits, '-' and '_' are allowed")
    vdir = virtual_dir if virtual_dir is not None else DEFAULT_VIRTUAL_DIR
    path = _find_config_file(name, vdir)
    if path is None:
        raise ValueError(
            f"Virtual machine '{name}' not found in {vdir} (expected {name}.yaml). "
            f"Create one with `uniqc backend virtual init {name}`."
        )
    try:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from None
    if not isinstance(raw, dict):
        _fail(path, "top level must be a mapping")
    return _parse_config(name, raw, path)


def scan_virtual_machines(virtual_dir: Path | None = None) -> list[VirtualMachineScan]:
    """Scan the virtual machine directory, reporting valid and invalid files alike."""
    vdir = virtual_dir if virtual_dir is not None else DEFAULT_VIRTUAL_DIR
    results: list[VirtualMachineScan] = []
    if not vdir.is_dir():
        return results
    seen: set[str] = set()
    for path in sorted(vdir.iterdir()):
        if not path.is_file() or path.suffix not in (".yaml", ".yml"):
            continue
        name = path.stem
        if name in seen:
            continue
        seen.add(name)
        try:
            config = load_virtual_machine(name, vdir)
            results.append(VirtualMachineScan(name=name, path=path, config=config, error=None))
        except ValueError as exc:
            results.append(VirtualMachineScan(name=name, path=path, config=None, error=str(exc)))
    return results


def list_virtual_machines(virtual_dir: Path | None = None) -> list[VirtualMachineConfig]:
    """Return all valid virtual machine configs, warning about invalid files."""
    configs: list[VirtualMachineConfig] = []
    for entry in scan_virtual_machines(virtual_dir):
        if entry.config is not None:
            configs.append(entry.config)
        else:
            warnings.warn(f"Skipping invalid virtual machine {entry.path}: {entry.error}", stacklevel=2)
    return configs


# ---------------------------------------------------------------------------
# Noise construction
# ---------------------------------------------------------------------------


def build_error_loader(config: VirtualMachineConfig) -> Any | None:
    """Build the gate error loader described by a virtual machine config.

    Layers (all stacked): uniform per-arity depolarizing, per-gate-type
    overrides, per-gate-instance overrides, and T1/T2 thermal relaxation
    (attached per gate type using the configured gate durations).

    Returns:
        An ``ErrorLoader_GateSpecificError``, or None when the config carries
        no gate noise.
    """
    from uniqc.simulator.error_model import (
        Depolarizing,
        ErrorLoader_GateSpecificError,
        ErrorModel,
        ThermalRelaxation,
        TwoQubitDepolarizing,
    )

    generic: list[ErrorModel] = []
    gatetype: dict[str, list[ErrorModel]] = {}
    specific: dict[tuple[str, tuple[int, ...]], list[ErrorModel]] = {}

    # Uniform per-arity depolarizing: the 1q rate applies to 1q gates only and
    # the 2q rate to 2q gates only (a true two-qubit depolarizing channel).
    if config.depol_1q:
        for gate, spec in available_originir_gates.items():
            if spec["qubit"] == 1:
                gatetype.setdefault(gate, []).append(Depolarizing(config.depol_1q))
    if config.depol_2q:
        for gate, spec in available_originir_gates.items():
            if spec["qubit"] == 2:
                gatetype.setdefault(gate, []).append(TwoQubitDepolarizing(config.depol_2q))

    for gate, prob in config.gate_type_depol.items():
        model: ErrorModel
        model = Depolarizing(prob) if available_originir_gates[gate]["qubit"] == 1 else TwoQubitDepolarizing(prob)
        gatetype.setdefault(gate, []).append(model)

    for (gate, qubits), prob in config.gate_instance_depol.items():
        model = Depolarizing(prob) if len(qubits) == 1 else TwoQubitDepolarizing(prob)
        specific[(gate, tuple(qubits))] = [model]

    if config.t1_us or config.t2_us:
        t1_ns = {q: v * _US_TO_NS for q, v in config.t1_us.items()} or None
        t2_ns = {q: v * _US_TO_NS for q, v in config.t2_us.items()} or None
        for gate, spec in available_originir_gates.items():
            arity = spec["qubit"]
            if arity not in (1, 2):
                continue
            t_ns = config.gate_times_ns.get(gate) or config.gate_times_ns.get(f"default_{arity}q")
            if not t_ns:
                continue
            gatetype.setdefault(gate, []).append(ThermalRelaxation(t1_ns, t2_ns, t_ns))

    if not generic and not gatetype and not specific:
        return None
    return ErrorLoader_GateSpecificError(
        generic_error=generic,
        gatetype_error=gatetype,  # type: ignore[arg-type]
        gate_specific_error=specific,  # type: ignore[arg-type]
    )


def build_readout_error(config: VirtualMachineConfig) -> dict[int, list[float]]:
    """Return the per-qubit readout error mapping ``{qubit: [p01, p10]}``."""
    return {q: [p01, p10] for q, (p01, p10) in config.readout.items()}


# ---------------------------------------------------------------------------
# Template scaffolding (used by `uniqc backend virtual init`)
# ---------------------------------------------------------------------------

_TEMPLATE = """\
# 含噪量子虚拟机配置 —— 由 `uniqc backend virtual init` 生成
# 引用方式: backend="dummy:virtual:{name}"
#   Python: submit_task(circuit, backend="dummy:virtual:{name}", shots=1000)
#   CLI:    uniqc submit circuit.qasm --backend dummy:virtual:{name}

description: 自定义含噪虚拟机

# 比特声明(二选一): qubits: [0, 1, 2, 3] 或 num_qubits: 4
num_qubits: 4

# 耦合拓扑(可选;删除本节表示全连接、无拓扑约束),2q 门双向可用
topology:
  - [0, 1]
  - [1, 2]
  - [2, 3]

# 门时长(纳秒);配置 thermal_relaxation 时必需
gate_times_ns:
  default_1q: 30        # 所有 1q 门的默认时长
  default_2q: 80        # 所有 2q 门的默认时长
  # CZ: 120             # 可按门类型单独覆盖

noise:
  # 按门类型的均匀退极化噪声(概率 ∈ [0, 1])
  depolarizing:
    1q: 0.001           # 所有 1q 门
    2q: 0.01            # 所有 2q 门(真双比特退极化通道)

  # 按门类型覆盖(与均匀噪声叠加);也可简写为 H: 0.0005
  gate_type:
    CZ: {{depolarizing: 0.02}}

  # 按具体门实例配置(与上面各层叠加;CZ 的比特顺序无关)
  gate_instance:
    - {{gate: CZ, qubits: [0, 1], depolarizing: 0.05}}
    - {{gate: H,  qubits: [2],  depolarizing: 0.003}}

  # T1/T2 热弛豫(微秒 μs),需配合 gate_times_ns;要求 t2_us <= 2 * t1_us
  thermal_relaxation:
    default: {{t1_us: 50, t2_us: 40}}
    qubits:
      2: {{t1_us: 30, t2_us: 25}}

  # 读出错误 [p(0→1), p(1→0)]
  readout:
    default: [0.02, 0.02]
    qubits:
      3: [0.05, 0.08]
"""


def create_virtual_machine_template(name: str, virtual_dir: Path | None = None, *, force: bool = False) -> Path:
    """Write a commented template config for ``name`` and return its path.

    Raises:
        ValueError: If the name is invalid.
        FileExistsError: If the file already exists and ``force`` is False.
    """
    if not name or not _NAME_RE.match(name):
        raise ValueError(f"Invalid virtual machine name {name!r}: only letters, digits, '-' and '_' are allowed")
    vdir = virtual_dir if virtual_dir is not None else DEFAULT_VIRTUAL_DIR
    path = vdir / f"{name}.yaml"
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists (use --force to overwrite)")
    vdir.mkdir(parents=True, exist_ok=True)
    path.write_text(_TEMPLATE.format(name=name), encoding="utf-8")
    return path
