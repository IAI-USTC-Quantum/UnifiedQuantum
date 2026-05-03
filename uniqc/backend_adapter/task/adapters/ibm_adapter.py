"""IBM Quantum backend adapter using QiskitRuntimeService.

Uses ``QiskitRuntimeService`` from ``qiskit-ibm-runtime`` to list backends
and submit/query tasks.  This is the recommended IBM approach as of 2024+,
superseding the raw REST API which is blocked by Cloudflare on quantum.ibm.com.

QiskitRuntimeService reference:
    https://docs.quantum.ibm.com/qiskit-ibm-runtime
"""

from __future__ import annotations

import warnings
from typing import Any

from uniqc.backend_adapter.task.adapters.base import (
    QuantumAdapter,
)

_SINGLE_QUBIT_GATE_PRIORITY = ("sx", "x", "id")
_TWO_QUBIT_GATE_PRIORITY = ("cz", "ecr", "cx")


def _avg(values: list[float]) -> float | None:
    """Return the arithmetic mean of a list, or None if the list is empty."""
    return sum(values) / len(values) if values else None


def _call_or_value(value: Any) -> Any:
    return value() if callable(value) else value


def _backend_configuration(backend: Any) -> Any | None:
    try:
        return _call_or_value(getattr(backend, "configuration", None))
    except Exception:
        return None


def _backend_name(backend: Any) -> str:
    return str(_call_or_value(getattr(backend, "name", "")))


def _backend_is_simulator(backend: Any) -> bool:
    try:
        return bool(_call_or_value(getattr(backend, "simulator", False)))
    except Exception:
        return False


def _as_qubit_tuple(qargs: Any) -> tuple[int, ...]:
    if isinstance(qargs, int):
        return (int(qargs),)
    try:
        return tuple(int(q) for q in qargs)
    except TypeError:
        return ()


def _iter_target_instruction_props(target: Any, gate_names: tuple[str, ...], arity: int):
    """Yield ``(gate_name, qubits, props)`` from a Qiskit Target."""
    if target is None:
        return
    for gate_name in gate_names:
        try:
            ops = target[gate_name]
        except Exception:
            continue
        if not hasattr(ops, "items"):
            continue
        for qargs, props in ops.items():
            qubits = _as_qubit_tuple(qargs)
            if len(qubits) == arity and props is not None:
                yield gate_name, qubits, props


def _target_error(target: Any, gate_names: tuple[str, ...], qubits: tuple[int, ...]) -> tuple[str, float | None]:
    for gate_name, qargs, props in _iter_target_instruction_props(target, gate_names, len(qubits)):
        if qargs == qubits and getattr(props, "error", None) is not None:
            return gate_name, float(props.error)
    return "", None


def _properties_gate_error(properties: Any, gate_names: tuple[str, ...], qubits: tuple[int, ...]) -> tuple[str, float | None]:
    if properties is None:
        return "", None
    for gate_name in gate_names:
        try:
            error = properties.gate_error(gate_name, qubits)
        except Exception:
            continue
        if error is not None:
            return gate_name, float(error)
    return "", None


def _normalize_coupling_map(raw: Any) -> list[tuple[int, int]]:
    if raw is None:
        return []
    try:
        if hasattr(raw, "get_edges"):
            raw = raw.get_edges()
    except Exception:
        pass
    edges: list[tuple[int, int]] = []
    try:
        iterator = iter(raw)
    except TypeError:
        return []
    for edge in iterator:
        try:
            u, v = edge
        except (TypeError, ValueError):
            continue
        edges.append((int(u), int(v)))
    return edges


def _backend_coupling_map(backend: Any, cfg: Any | None = None) -> list[tuple[int, int]]:
    for raw in (getattr(backend, "coupling_map", None), getattr(cfg, "coupling_map", None)):
        edges = _normalize_coupling_map(raw)
        if edges:
            return edges
    try:
        target = backend.target
        coupling_map = target.build_coupling_map() if target is not None else None
        edges = _normalize_coupling_map(coupling_map)
        if edges:
            return edges
    except Exception:
        pass
    return []


def _get_backend_properties(backend: Any, *, refresh: bool = False) -> Any | None:
    try:
        properties = getattr(backend, "properties", None)
        if callable(properties):
            try:
                return properties(refresh=refresh)
            except TypeError:
                return properties()
        return properties
    except Exception:
        return None


def _compute_ibm_fidelity(b: Any) -> dict[str, Any]:
    """Compute average fidelity and coherence metrics for an IBM backend.

    Uses ``backend.target`` for gate errors and ``backend.qubit_properties``
    for T1/T2 and readout error. Returns None for all fields on simulators
    or when the data is unavailable.

    Returns:
        dict with keys: avg_1q_fidelity, avg_2q_fidelity, avg_readout_fidelity,
        coherence_t1 (microseconds), coherence_t2 (microseconds).
    """
    try:
        target = b.target
    except Exception:
        return {
            "avg_1q_fidelity": None,
            "avg_2q_fidelity": None,
            "avg_readout_fidelity": None,
            "coherence_t1": None,
            "coherence_t2": None,
        }

    if target is None:
        return {
            "avg_1q_fidelity": None,
            "avg_2q_fidelity": None,
            "avg_readout_fidelity": None,
            "coherence_t1": None,
            "coherence_t2": None,
        }

    properties = _get_backend_properties(b)

    # Single-qubit gate fidelity: prefer SX, then X/ID if SX is absent.
    sq_errors: list[float] = []
    seen_qubits: set[int] = set()
    for _gate_name, qpair, props in _iter_target_instruction_props(target, _SINGLE_QUBIT_GATE_PRIORITY, 1):
        if qpair[0] in seen_qubits or getattr(props, "error", None) is None:
            continue
        sq_errors.append(float(props.error))
        seen_qubits.add(qpair[0])
    if not sq_errors:
        for q in range(getattr(b, "num_qubits", 0) or 0):
            _gate, error = _properties_gate_error(properties, _SINGLE_QUBIT_GATE_PRIORITY, (q,))
            if error is not None:
                sq_errors.append(error)

    # Two-qubit gate fidelity: prefer CZ, then ECR/CX depending on backend generation.
    tq_errors: list[float] = []
    seen_edges: set[tuple[int, int]] = set()
    for _gate_name, qpair, props in _iter_target_instruction_props(target, _TWO_QUBIT_GATE_PRIORITY, 2):
        key = tuple(sorted(qpair))
        if key in seen_edges or getattr(props, "error", None) is None:
            continue
        tq_errors.append(float(props.error))
        seen_edges.add(key)
    if not tq_errors:
        for edge in _backend_coupling_map(b):
            _gate, error = _properties_gate_error(properties, _TWO_QUBIT_GATE_PRIORITY, edge)
            if error is not None:
                tq_errors.append(error)

    # Coherence and readout: qubit_properties gives T1/T2 (seconds)
    t1s, t2s, ro_errors = [], [], []
    num_qubits = b.num_qubits
    try:
        for q in range(num_qubits):
            try:
                qp = b.qubit_properties(q)
                if qp.t1 is not None:
                    t1s.append(qp.t1 * 1e6)  # seconds → μs
                if qp.t2 is not None:
                    t2s.append(qp.t2 * 1e6)
            except Exception:
                pass
    except Exception:
        pass

    # Readout error from properties if qubit_properties didn't have it
    try:
        props = properties
        if props:
            for q in range(num_qubits):
                try:
                    re = props.readout_error(q)
                    if re is not None:
                        ro_errors.append(re)
                except Exception:
                    pass
    except Exception:
        pass

    return {
        "avg_1q_fidelity": _avg([1 - e for e in sq_errors]) if sq_errors else None,
        "avg_2q_fidelity": _avg([1 - e for e in tq_errors]) if tq_errors else None,
        "avg_readout_fidelity": _avg([1 - e for e in ro_errors]) if ro_errors else None,
        "coherence_t1": _avg(t1s),
        "coherence_t2": _avg(t2s),
    }


class IBMAdapter(QuantumAdapter):
    """Deprecated: delegates to QiskitAdapter.

    .. deprecated::
        IBMAdapter is deprecated. Use :class:`QiskitAdapter` instead,
        which uses ``qiskit-ibm-runtime`` for task submission.

    This class is kept for backwards compatibility and delegates all
    operations to an internal QiskitAdapter instance.
    """

    name = "ibm"

    def __init__(self, proxy: dict[str, str] | str | None = None) -> None:
        warnings.warn(
            "IBMAdapter is deprecated. Use QiskitAdapter instead. "
            "It provides the same functionality via qiskit-ibm-runtime.",
            DeprecationWarning,
            stacklevel=2,
        )
        from uniqc.backend_adapter.task.adapters.qiskit_adapter import QiskitAdapter

        self._delegate = QiskitAdapter(proxy=proxy)

    # -------------------------------------------------------------------------
    # Forward all methods to the delegate QiskitAdapter
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        return self._delegate.is_available()

    def _get_service(self):
        return self._delegate._service

    def list_backends(self) -> list[dict[str, Any]]:
        """List IBM backends through QiskitRuntimeService.

        The returned entries include both average metrics and per-qubit/per-edge
        calibration details from ``backend.target`` so the Gateway can color
        chip topologies without flattening every edge to the global average.
        """
        service = self._get_service()
        raw_backends: list[dict[str, Any]] = []
        for b in service.backends():
            name = _backend_name(b)
            cfg = _backend_configuration(b)
            try:
                status = "available" if b.status().operational else "unavailable"
            except Exception:
                status = "unknown"
            try:
                pt = b.processor_type
                processor_type = pt.get("family", "") if isinstance(pt, dict) else str(pt) if pt else ""
            except Exception:
                processor_type = ""
            coupling_map = _backend_coupling_map(b, cfg)
            entry: dict[str, Any] = {
                "name": name,
                "simulator": _backend_is_simulator(b),
                "configuration": {
                    "num_qubits": getattr(b, "num_qubits", 0),
                    "coupling_map": [list(edge) for edge in coupling_map],
                    "basis_gates": list(getattr(b, "basis_gates", []) or getattr(cfg, "basis_gates", []) or []),
                    "max_shots": getattr(b, "max_shots", None) or getattr(cfg, "max_shots", None),
                    "memory": getattr(b, "memory", False) or getattr(cfg, "memory", False),
                    "qobd": getattr(b, "qobd", False) or getattr(cfg, "qobd", False),
                    "supported_instructions": list(getattr(b, "supported_instructions", []) or [])
                    if hasattr(b, "supported_instructions")
                    else [],
                    "processor_type": processor_type,
                },
                "status": status,
                "description": getattr(b, "description", ""),
            }
            try:
                od = b.online_date
                if od:
                    entry["online_date"] = str(od)
            except Exception:
                pass
            fidelity = _compute_ibm_fidelity(b)
            entry.update(fidelity)
            chip = _chip_characterization_from_backend(b, backend_name=name)
            if chip is not None:
                entry["per_qubit_calibration"] = [item.to_dict() for item in chip.single_qubit_data]
                entry["per_pair_calibration"] = [item.to_dict() for item in chip.two_qubit_data]
                entry["global_info"] = chip.global_info.to_dict()
                entry["calibrated_at"] = chip.calibrated_at
            raw_backends.append(entry)
        return raw_backends

    def translate_circuit(self, originir: str) -> Any:
        return self._delegate.translate_circuit(originir)

    def submit(self, circuit: Any, *, shots: int = 1000, **kwargs: Any) -> str:
        return self._delegate.submit(circuit, shots=shots, **kwargs)

    def submit_batch(self, circuits: list[Any], *, shots: int = 1000, **kwargs: Any) -> list[str]:
        return self._delegate.submit_batch(circuits, shots=shots, **kwargs)

    def query(self, taskid: str) -> dict[str, Any]:
        return self._delegate.query(taskid)

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        return self._delegate.query_batch(taskids)

    def query_sync(
        self,
        taskid: str | list[str],
        interval: float = 2.0,
        timeout: float = 60.0,
        retry: int = 5,
    ) -> list[dict[str, Any]]:
        return self._delegate.query_sync(taskid, interval=interval, timeout=timeout, retry=retry)

    # -------------------------------------------------------------------------
    # Chip characterization
    # -------------------------------------------------------------------------

    def get_chip_characterization(self, backend_name: str):
        """Return per-qubit and per-pair calibration data for an IBM backend.

        Parameters
        ----------
        backend_name:
            IBM backend name, e.g. ``"ibm-sherbrooke"``.

        Returns
        -------
        ChipCharacterization or None
        """
        service = self._get_service()
        try:
            backend = service.backend(backend_name)
        except Exception:
            return None
        return _chip_characterization_from_backend(backend, backend_name=backend_name)


def _chip_characterization_from_backend(backend: Any, *, backend_name: str | None = None):
    """Build ``ChipCharacterization`` from an IBM backend object."""
    from datetime import datetime, timezone

    from uniqc.backend_adapter.backend_info import Platform, QubitTopology
    from uniqc.cli.chip_info import (
        ChipCharacterization,
        ChipGlobalInfo,
        SingleQubitData,
        TwoQubitData,
        TwoQubitGateData,
    )

    name = backend_name or _backend_name(backend)
    try:
        target = backend.target
    except Exception:
        target = None
    properties = _get_backend_properties(backend, refresh=True)
    cfg = _backend_configuration(backend)
    num_qubits = int(getattr(backend, "num_qubits", 0) or 0)

    # Per-qubit data
    single_qubit_data: list[SingleQubitData] = []
    for q in range(num_qubits):
        t1: float | None = None
        t2: float | None = None
        sx_fidelity: float | None = None
        ro_fid_0: float | None = None
        ro_fid_1: float | None = None
        avg_ro: float | None = None

        # Gate errors from target, with BackendProperties fallback.
        _gate, error = _target_error(target, _SINGLE_QUBIT_GATE_PRIORITY, (q,))
        if error is None:
            _gate, error = _properties_gate_error(properties, _SINGLE_QUBIT_GATE_PRIORITY, (q,))
        if error is not None:
            sx_fidelity = 1.0 - error

        # T1/T2 from qubit_properties
        try:
            qp = backend.qubit_properties(q)
            if qp.t1 is not None:
                t1 = qp.t1 * 1e6  # seconds → μs
            if qp.t2 is not None:
                t2 = qp.t2 * 1e6
        except Exception:
            pass

        # Readout error: prefer Target measure instruction, then BackendProperties.
        _gate, readout_error = _target_error(target, ("measure",), (q,))
        if readout_error is not None:
            avg_ro = 1.0 - readout_error
        try:
            if properties:
                if avg_ro is None:
                    re = properties.readout_error(q)
                    if re is not None:
                        avg_ro = 1.0 - float(re)
                qubit_props = properties.qubit_property(q)
                p10 = qubit_props.get("prob_meas1_prep0", (None,))[0]
                p01 = qubit_props.get("prob_meas0_prep1", (None,))[0]
                if p10 is not None:
                    ro_fid_0 = 1.0 - float(p10)
                if p01 is not None:
                    ro_fid_1 = 1.0 - float(p01)
                if avg_ro is None and ro_fid_0 is not None and ro_fid_1 is not None:
                    avg_ro = (ro_fid_0 + ro_fid_1) / 2.0
        except Exception:
            pass

        single_qubit_data.append(
            SingleQubitData(
                qubit_id=q,
                t1=t1,
                t2=t2,
                single_gate_fidelity=sx_fidelity,
                readout_fidelity_0=ro_fid_0,
                readout_fidelity_1=ro_fid_1,
                avg_readout_fidelity=avg_ro,
            )
        )

    # Per-pair data from target CZ/ECR/CX, with BackendProperties fallback.
    two_qubit_data: dict[tuple[int, int], TwoQubitData] = {}
    for gname, qpair, props in _iter_target_instruction_props(target, _TWO_QUBIT_GATE_PRIORITY, 2):
        if getattr(props, "error", None) is None:
            continue
        u, v = qpair
        key = tuple(sorted((u, v)))
        existing = two_qubit_data.get(key)
        gate_data = TwoQubitGateData(gate=gname, fidelity=1.0 - float(props.error))
        if existing is None:
            two_qubit_data[key] = TwoQubitData(qubit_u=u, qubit_v=v, gates=(gate_data,))
        else:
            two_qubit_data[key] = TwoQubitData(
                qubit_u=existing.qubit_u,
                qubit_v=existing.qubit_v,
                gates=existing.gates + (gate_data,),
            )
    if not two_qubit_data:
        for edge in _backend_coupling_map(backend, cfg):
            gname, error = _properties_gate_error(properties, _TWO_QUBIT_GATE_PRIORITY, edge)
            if error is None:
                continue
            u, v = edge
            two_qubit_data[tuple(sorted(edge))] = TwoQubitData(
                qubit_u=u,
                qubit_v=v,
                gates=(TwoQubitGateData(gate=gname, fidelity=1.0 - error),),
            )

    # Global info from configuration / target.
    try:
        basis_gates: list[str] = list(getattr(backend, "basis_gates", []) or getattr(cfg, "basis_gates", []) or [])
        if not basis_gates and target is not None and hasattr(target, "operation_names"):
            basis_gates = list(target.operation_names)
        dt_s: float | None = getattr(cfg, "dt", None)
        sq_gate_time: float | None = float(dt_s) * 1e9 if dt_s is not None else None
    except Exception:
        basis_gates = []
        sq_gate_time = None

    # Classify basis gates into 1Q / 2Q
    sq_gates, tq_gates = [], []
    for g in basis_gates:
        g_lower = str(g).lower()
        if (
            g_lower in {"h", "x", "y", "z", "s", "sx", "sdg", "sxdg", "t", "tdg", "i",
                        "id", "rx", "ry", "rz", "u1", "u2", "u3", "r", "rphi", "rphi90", "rphi180"}
            and g_lower not in sq_gates
        ):
            sq_gates.append(g_lower)
        elif (
            g_lower in {"cx", "cz", "ecr", "swap", "iswap", "xx", "yy", "zz", "xy"}
            and g_lower not in tq_gates
        ):
            tq_gates.append(g_lower)

    # 2Q gate time: use the average target duration where available.
    tq_durations = [
        float(props.duration) * 1e9
        for _gname, _qpair, props in _iter_target_instruction_props(target, _TWO_QUBIT_GATE_PRIORITY, 2)
        if getattr(props, "duration", None) is not None
    ]
    tq_gate_time: float | None = _avg(tq_durations)

    # Calibration timestamp
    calibrated_at: str | None = None
    try:
        if properties is not None and getattr(properties, "last_update_date", None) is not None:
            calibrated_at = str(properties.last_update_date)
    except Exception:
        pass
    if calibrated_at is None:
        calibrated_at = datetime.now(timezone.utc).isoformat()

    return ChipCharacterization(
        platform=Platform.IBM,
        chip_name=name,
        full_id=f"ibm:{name}",
        available_qubits=tuple(range(num_qubits)),
        connectivity=tuple(QubitTopology(u=u, v=v) for u, v in _backend_coupling_map(backend, cfg)),
        single_qubit_data=tuple(single_qubit_data),
        two_qubit_data=tuple(two_qubit_data.values()),
        global_info=ChipGlobalInfo(
            single_qubit_gates=tuple(sq_gates),
            two_qubit_gates=tuple(tq_gates),
            single_qubit_gate_time=sq_gate_time,
            two_qubit_gate_time=tq_gate_time,
        ),
        calibrated_at=calibrated_at,
    )
