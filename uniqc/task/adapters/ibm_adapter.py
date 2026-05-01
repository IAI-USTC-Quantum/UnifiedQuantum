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

from uniqc.task.adapters.base import (
    QuantumAdapter,
)
from uniqc.task.config import load_ibm_config


def _avg(values: list[float]) -> float | None:
    """Return the arithmetic mean of a list, or None if the list is empty."""
    return sum(values) / len(values) if values else None


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

    # Single-qubit gate fidelity: SX gate error, 1 - error = fidelity
    sq_errors: list[float] = []
    try:
        # target["sx"] returns dict[qubit_index, InstructionProperties]
        sx_ops = target["sx"]
        if hasattr(sx_ops, "items"):
            for qpair, props in sx_ops.items():
                if len(qpair) == 1 and props and props.error is not None:
                    sq_errors.append(props.error)
    except Exception:
        pass

    # Two-qubit gate fidelity: CZ (Heron/Nighthawk) or ECR (Eagle)
    tq_errors: list[float] = []
    for gname in ("cz", "ecr"):
        try:
            ops = target[gname]
            if hasattr(ops, "items"):
                for qpair, props in ops.items():
                    if len(qpair) == 2 and props and props.error is not None:
                        tq_errors.append(props.error)
                if tq_errors:
                    break
        except Exception:
            continue

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
        props = b.properties()
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
        which uses ``qiskit-ibm-provider`` for task submission.

    This class is kept for backwards compatibility and delegates all
    operations to an internal QiskitAdapter instance.
    """

    name = "ibm"

    def __init__(self, proxy: dict[str, str] | str | None = None) -> None:
        warnings.warn(
            "IBMAdapter is deprecated. Use QiskitAdapter instead. "
            "It provides the same functionality via qiskit-ibm-provider.",
            DeprecationWarning,
            stacklevel=2,
        )
        from uniqc.task.adapters.qiskit_adapter import QiskitAdapter

        self._delegate = QiskitAdapter(proxy=proxy)

    # -------------------------------------------------------------------------
    # Forward all methods to the delegate QiskitAdapter
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        return self._delegate.is_available()

    def list_backends(self) -> list[dict[str, Any]]:
        # QiskitAdapter does not implement list_backends; delegate to IBMAdapter
        # via the runtime service. Re-instantiate the original logic here.
        from uniqc.config import sync_tokens_to_env
        sync_tokens_to_env()
        config = load_ibm_config()
        token: str = config["api_token"]
        import qiskit_ibm_provider
        qiskit_ibm_provider.IBMProvider.save_account(token)
        provider = qiskit_ibm_provider.IBMProvider(instance="ibm-q/open/main")
        raw_backends: list[dict[str, Any]] = []
        for b in provider.backends():
            try:
                status = "available" if b.status().operational else "unavailable"
            except Exception:
                status = "unknown"
            try:
                pt = b.processor_type
                processor_type = pt.get("family", "") if isinstance(pt, dict) else str(pt) if pt else ""
            except Exception:
                processor_type = ""
            entry: dict[str, Any] = {
                "name": b.name,
                "simulator": b.simulator,
                "configuration": {
                    "num_qubits": b.num_qubits,
                    "coupling_map": list(getattr(b, "coupling_map", [])),
                    "basis_gates": getattr(b, "basis_gates", []),
                    "max_shots": getattr(b, "max_shots", None),
                    "memory": getattr(b, "memory", False),
                    "qobd": getattr(b, "qobd", False),
                    "supported_instructions": list(b.supported_instructions)
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
        from datetime import datetime, timezone

        from uniqc.backend_info import Platform, QubitTopology
        from uniqc.cli.chip_info import (
            ChipCharacterization,
            ChipGlobalInfo,
            SingleQubitData,
            TwoQubitData,
            TwoQubitGateData,
        )

        service = self._get_service()
        try:
            backend = service.backend(backend_name)
        except Exception:
            return None

        try:
            target = backend.target
        except Exception:
            target = None

        num_qubits = getattr(backend, "num_qubits", 0)

        # Per-qubit data
        single_qubit_data: list[SingleQubitData] = []
        for q in range(num_qubits):
            t1: float | None = None
            t2: float | None = None
            sx_fidelity: float | None = None
            ro_fid_0: float | None = None
            ro_fid_1: float | None = None
            avg_ro: float | None = None

            # Gate errors from target
            if target is not None:
                try:
                    sx_ops = target["sx"]
                    if hasattr(sx_ops, "items"):
                        for qpair, props in sx_ops.items():
                            if len(qpair) == 1 and qpair[0] == q and props and props.error is not None:
                                sx_fidelity = 1.0 - props.error
                                break
                except Exception:
                    pass

            # T1/T2 from qubit_properties
            try:
                qp = backend.qubit_properties(q)
                if qp.t1 is not None:
                    t1 = qp.t1 * 1e6  # seconds → μs
                if qp.t2 is not None:
                    t2 = qp.t2 * 1e6
            except Exception:
                pass

            # Readout error from properties
            try:
                props = backend.properties()
                if props:
                    re = props.readout_error(q)
                    if re is not None:
                        avg_ro = 1.0 - re
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

        # Per-pair data from target CZ/ECR
        two_qubit_data: list[TwoQubitData] = {}
        seen_pairs: set[tuple[int, int]] = set()

        if target is not None:
            for gname in ("cz", "ecr"):
                try:
                    ops = target[gname]
                    if hasattr(ops, "items"):
                        for qpair, props in ops.items():
                            if len(qpair) == 2 and props and props.error is not None:
                                u, v = qpair[0], qpair[1]
                                key = tuple(sorted([u, v]))
                                if key not in seen_pairs:
                                    seen_pairs.add(key)
                                    two_qubit_data[key] = TwoQubitData(
                                        qubit_u=u,
                                        qubit_v=v,
                                        gates=(
                                            TwoQubitGateData(gate=gname, fidelity=1.0 - props.error),
                                        ),
                                    )
                                else:
                                    # Append to existing gates tuple
                                    existing = two_qubit_data[key]
                                    two_qubit_data[key] = TwoQubitData(
                                        qubit_u=existing.qubit_u,
                                        qubit_v=existing.qubit_v,
                                        gates=existing.gates + (TwoQubitGateData(gate=gname, fidelity=1.0 - props.error),),
                                    )
                except Exception:
                    pass

        # Global info from configuration
        try:
            cfg = backend.configuration
            basis_gates: list[str] = list(getattr(cfg, "basis_gates", []) or [])
            dt_ns: float | None = getattr(cfg, "dt", None)
            sq_gate_time: float | None = float(dt_ns) * 1e9 if dt_ns is not None else None  # dt is in seconds
        except Exception:
            basis_gates = []
            sq_gate_time = None

        # Classify basis gates into 1Q / 2Q
        sq_gates, tq_gates = [], []
        for g in basis_gates:
            g_lower = g.lower()
            if (
                g_lower in {"h", "x", "y", "z", "s", "sx", "sdg", "sxdg", "t", "tdg", "i",
                            "rx", "ry", "rz", "u1", "u2", "u3", "r", "rphi", "rphi90", "rphi180"}
                and g not in sq_gates
            ):
                sq_gates.append(g)
            elif (
                g_lower in {"cx", "cz", "ecr", "swap", "iswap", "xx", "yy", "zz", "xy"}
                and g not in tq_gates
            ):
                tq_gates.append(g)

        # 2Q gate time (try to derive from dt)
        tq_gate_time: float | None = None
        if sq_gate_time is not None:
            tq_gate_time = sq_gate_time * 10  # rough estimate; IBM doesn't always expose this

        # Calibration timestamp
        calibrated_at: str | None = None
        try:
            cal = backend.calibration
            if cal and hasattr(cal, "last_update_date"):
                calibrated_at = str(cal.last_update_date)
        except Exception:
            calibrated_at = datetime.now(timezone.utc).isoformat()

        return ChipCharacterization(
            platform=Platform.IBM,
            chip_name=backend_name,
            full_id=f"ibm:{backend_name}",
            available_qubits=tuple(range(num_qubits)),
            connectivity=tuple(
                QubitTopology(u=u, v=v) for u, v in getattr(backend, "coupling_map", []) or []
            ),
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
