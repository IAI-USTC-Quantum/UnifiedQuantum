"""LogicalQubit (逻辑比特) backend adapter.

Submits circuits to the LogicalQubit cloud platform using lqcloud.

Installation:
    pip install unified-quantum[logicalqubit]
"""

from __future__ import annotations

__all__ = ["LogicalQubitAdapter"]

from typing import Any

from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
)
from uniqc.backend_adapter.task.optional_deps import check_lqcloud, require

#: Server-side shot limit advertised by the lqcloud platform.
MAX_SHOTS = 50000


def _resolve_backend(kwargs: dict[str, Any], default: str | None) -> str | None:
    """Resolve the target backend from submit kwargs (canonical key first)."""
    for key in ("backend_name", "chip_id", "chip"):
        value = kwargs.get(key)
        if value:
            return str(value)
    return default


class LogicalQubitAdapter(QuantumAdapter):
    """Adapter for the LogicalQubit cloud platform (逻辑比特) using lqcloud.

    Credentials are read from ``uniqc.config.load_logicalqubit_config()``
    (``logicalqubit.api_key``, optional ``logicalqubit.url``). Both the
    lqcloud SDK import and the credential load are lazy so that importing
    this module never requires the SDK or a configured account.

    Note:
        The lqcloud package is required for this adapter.
        Install with: pip install unified-quantum[logicalqubit]
    """

    name = "logicalqubit"
    # lqcloud batch submission returns a single aggregate Job without child
    # ids; keep one platform job per circuit instead.
    max_native_batch_size: int = 1

    def __init__(self, backend_name: str | None = None) -> None:
        """Initialize the LogicalQubit adapter.

        Args:
            backend_name: Default backend for submit() calls that don't
                specify one. ``submit_task`` users normally pass
                ``backend='logicalqubit:<backend>'`` which overrides this.
        """
        self._default_backend = backend_name
        self._provider: Any = None

    # -------------------------------------------------------------------------
    # SDK / credential bootstrap (all lazy)
    # -------------------------------------------------------------------------

    def _get_provider(self) -> Any:
        """Return the cached ``LQCloudProvider`` (created on first use)."""
        if self._provider is None:
            require("lqcloud", "logicalqubit")
            from lqcloud import LQCloudProvider

            from uniqc.config import load_logicalqubit_config

            config = load_logicalqubit_config()
            self._provider = LQCloudProvider(
                api_key=config["api_key"],
                url=config.get("url") or None,
                interactive=False,
            )
        return self._provider

    def is_available(self) -> bool:
        """Return True if lqcloud is installed and an api_key is configured."""
        if not check_lqcloud():
            return False
        try:
            from uniqc.config import load_logicalqubit_config

            load_logicalqubit_config()
        except Exception:
            return False
        return True

    # -------------------------------------------------------------------------
    # Backend discovery
    # -------------------------------------------------------------------------

    def list_backends(self) -> list[dict[str, Any]]:
        """Return raw LogicalQubit backend metadata.

        ``LQCloudProvider.get_backends()`` returns a list of dicts, each
        carrying at least a ``"name"`` key. Entries are passed through
        with ``name`` normalised to ``str``; the registry normaliser
        handles the rest.
        """
        provider = self._get_provider()
        results: list[dict[str, Any]] = []
        for entry in provider.get_backends() or []:
            if isinstance(entry, dict):
                item = dict(entry)
                item["name"] = str(item.get("name", ""))
                results.append(item)
        return results

    # -------------------------------------------------------------------------
    # Chip characterization
    # -------------------------------------------------------------------------

    def get_chip_characterization(self, chip_name: str):
        """Return topology-level characterization for a LogicalQubit backend.

        lqcloud's ``get_backend_config`` exposes the qubit count and the
        coupling map but no T1/T2 or fidelity calibration data, so the
        returned :class:`ChipCharacterization` carries connectivity only
        (per-qubit fields are left as None).

        Parameters
        ----------
        chip_name:
            LogicalQubit backend name, e.g. ``"QZ01-repetition_code"``.

        Returns
        -------
        ChipCharacterization or None
            None when lqcloud is unavailable or the backend config cannot
            be fetched.
        """
        from uniqc.backend_adapter.backend_info import Platform, QubitTopology
        from uniqc.cli.chip_info import (
            ChipCharacterization,
            ChipGlobalInfo,
            SingleQubitData,
            TwoQubitData,
        )

        try:
            conf = self._get_provider().get_backend_config(chip_name)
        except Exception:
            return None
        if not isinstance(conf, dict):
            return None

        edges: set[tuple[int, int]] = set()
        for pair in (conf.get("topology") or {}).get("coupling_map") or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            try:
                u, v = int(pair[0]), int(pair[1])
            except (TypeError, ValueError):
                continue
            if u != v:
                edges.add((min(u, v), max(u, v)))

        nqubits = int(conf.get("qubits") or 0)
        if nqubits <= 0:
            nqubits = max((v for _, v in edges), default=-1) + 1
        available = tuple(range(nqubits))

        return ChipCharacterization(
            platform=Platform.LOGICALQUBIT,
            chip_name=chip_name,
            full_id=f"logicalqubit:{chip_name}",
            available_qubits=available,
            connectivity=tuple(QubitTopology(u=u, v=v) for u, v in sorted(edges)),
            single_qubit_data=tuple(SingleQubitData(qubit_id=i) for i in available),
            two_qubit_data=tuple(TwoQubitData(qubit_u=u, qubit_v=v) for u, v in sorted(edges)),
            global_info=ChipGlobalInfo(single_qubit_gates=("sx", "rz"), two_qubit_gates=("cz",)),
            calibrated_at=None,
        )

    # -------------------------------------------------------------------------
    # Circuit translation (OriginIR to lqcloud QuantumCircuit)
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> Any:
        """Convert an OriginIR string to an lqcloud QuantumCircuit (local).

        Args:
            originir: OriginIR format circuit string.

        Returns:
            lqcloud QuantumCircuit object.
        """
        lqcloud = require("lqcloud", "logicalqubit")

        from uniqc.backend_adapter.circuit_adapter import originir_to_lqcloud_circuit

        return originir_to_lqcloud_circuit(originir, lqcloud.QuantumCircuit)

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(self, circuit: Any, *, shots: int = 1000, **kwargs: Any) -> str:
        """Submit a single circuit to LogicalQubit.

        Args:
            circuit: lqcloud QuantumCircuit (as produced by
                :class:`~uniqc.backend_adapter.circuit_adapter.LogicalQubitCircuitAdapter`).
                OriginIR input (detected by its ``QINIT`` header) is
                translated first for convenience.
            shots: Number of measurement shots (server limit: 50000).
            **kwargs: Additional options:
                - backend_name: Target backend name

        Returns:
            lqcloud job id string.
        """
        if int(shots) > MAX_SHOTS:
            raise ValueError(f"shots ({shots}) exceeds the LogicalQubit server maximum ({MAX_SHOTS})")

        backend_name = _resolve_backend(kwargs, self._default_backend)
        if not backend_name:
            raise ValueError(
                "LogicalQubit submit() requires a backend name. "
                "Pass backend='logicalqubit:<backend>' to submit_task or the "
                "backend_name kwarg; run `uniqc backend list -p logicalqubit` "
                "to discover available backends."
            )

        provider = self._get_provider()
        # verify=False avoids an extra network round-trip; the name is
        # validated server-side at run() time.
        backend = provider.get_backend(backend_name, verify=False)

        qc = self.translate_circuit(circuit) if isinstance(circuit, str) and "QINIT" in circuit else circuit

        job = backend.run(qc, shots=int(shots))
        return str(job.job_id)

    def submit_batch(self, circuits: list[Any], *, shots: int = 1000, **kwargs: Any) -> list[str]:
        """Submit circuits one by one (one job id per circuit).

        lqcloud's batch API returns a single aggregate Job without child
        ids, so uniqc slices batches into per-circuit jobs
        (``max_native_batch_size == 1``).
        """
        return [self.submit(circuit, shots=shots, **kwargs) for circuit in circuits]

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    def _job_for(self, taskid: str) -> Any:
        """Rebuild a Job handle from a job id for status queries."""
        require("lqcloud", "logicalqubit")
        from lqcloud.job import Job

        return Job(taskid, self._get_provider())

    def query(self, taskid: str) -> dict[str, Any]:
        """Query a single task's status.

        Args:
            taskid: lqcloud job id.

        Returns:
            dict with keys: taskid, status, result (counts dict when
            status is ``'success'``, error payload when ``'failed'``).
        """
        job = self._job_for(taskid)
        status = job.status()
        status_name = (status.name if hasattr(status, "name") else str(status)).upper()

        if status_name == "COMPLETED":
            from uniqc.backend_adapter.task.normalizers import normalize_logicalqubit

            unified = normalize_logicalqubit(
                job.result().get_counts(),
                task_id=taskid,
                backend_name=self._default_backend,
            )
            return {
                "taskid": taskid,
                "status": TASK_STATUS_SUCCESS,
                "result": dict(unified.counts),
            }
        if status_name in ("FAILED", "CANCELLED", "ERROR"):
            return {
                "taskid": taskid,
                "status": TASK_STATUS_FAILED,
                "result": {"error": f"LogicalQubit job {status_name.lower()}"},
            }
        # QUEUED / PENDING / RUNNING / unknown → still in flight
        return {"taskid": taskid, "status": TASK_STATUS_RUNNING}

    def query_batch(self, taskids: str | list[str]) -> dict[str, Any]:
        """Query multiple tasks and merge results.

        Overall status is the worst case: ``failed`` > ``running`` >
        ``success``.
        """
        if isinstance(taskids, str):
            taskids = [taskids]

        taskinfo: dict[str, Any] = {"status": TASK_STATUS_SUCCESS, "result": []}

        for taskid in taskids:
            result_i = self.query(taskid)

            if result_i["status"] == TASK_STATUS_FAILED:
                taskinfo["status"] = TASK_STATUS_FAILED
                taskinfo["result"] = result_i.get("result")
                break
            elif result_i["status"] == TASK_STATUS_RUNNING:
                taskinfo["status"] = TASK_STATUS_RUNNING

            if taskinfo["status"] == TASK_STATUS_SUCCESS:
                payload = result_i.get("result", [])
                if isinstance(payload, list):
                    taskinfo["result"].extend(payload)
                elif isinstance(payload, dict):
                    taskinfo["result"].append(payload)

        return taskinfo

    # -------------------------------------------------------------------------
    # Dry-run validation
    # -------------------------------------------------------------------------

    def dry_run(self, originir: str, *, shots: int = 1000, **kwargs: Any) -> DryRunResult:
        """Dry-run validation for LogicalQubit backends.

        Validates offline: OriginIR parses and maps onto lqcloud gates,
        and the shot count fits the server limit. lqcloud's
        ``QuantumCircuit`` construction is purely local — this method
        makes NO network calls.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        from uniqc.backend_adapter.circuit_adapter import LogicalQubitCircuitAdapter
        from uniqc.backend_adapter.task.adapters.base import _dry_run_failed, _dry_run_success

        backend_name = _resolve_backend(kwargs, self._default_backend) or "(unspecified)"

        if shots <= 0:
            return _dry_run_failed(
                "shots must be positive",
                details=f"Invalid shots value for LogicalQubit: {shots}",
                backend_name=backend_name,
            )
        if shots > MAX_SHOTS:
            return _dry_run_failed(
                f"shots ({shots}) exceeds backend maximum ({MAX_SHOTS})",
                details=f"Shot count validation failed: {shots} > {MAX_SHOTS}",
                backend_name=backend_name,
            )

        try:
            circuit = self.translate_circuit(originir)
        except Exception as e:
            return _dry_run_failed(
                str(e),
                details=(
                    f"OriginIR translation to an lqcloud QuantumCircuit failed for "
                    f"backend '{backend_name}': {e}. The circuit may use gates not "
                    "supported by LogicalQubit."
                ),
                backend_name=backend_name,
            )

        warnings: tuple[str, ...] = ()
        if _resolve_backend(kwargs, self._default_backend) is None:
            warnings = (
                "No backend_name given; dry-run validated circuit structure only. "
                "Backend existence is checked at submission time.",
            )

        return _dry_run_success(
            (
                f"Dry-run passed for '{backend_name}': OriginIR translates cleanly "
                f"to an lqcloud QuantumCircuit. Qubits={circuit.num_qubits}, shots={shots}"
            ),
            backend_name=backend_name,
            circuit_qubits=circuit.num_qubits,
            supported_gates=tuple(sorted(LogicalQubitCircuitAdapter.SUPPORTED_GATES)),
            warnings=warnings,
        )
