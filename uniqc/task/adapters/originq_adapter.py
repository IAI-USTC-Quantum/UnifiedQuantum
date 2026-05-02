"""OriginQ Cloud backend adapter.

Submits OriginIR circuits to the OriginQ Cloud service using pyqpanda3.

Installation:
    pip install unified-quantum[originq]
"""

from __future__ import annotations

__all__ = ["OriginQAdapter"]

import time
import warnings
from typing import Any

from uniqc.backend_info import ORIGINQ_SIMULATOR_NAMES
from uniqc.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
)
from uniqc.task.config import load_originq_config
from uniqc.task.optional_deps import require


def _avg(values: list[float]) -> float | None:
    """Return the arithmetic mean of a list, or None if the list is empty."""
    return sum(values) / len(values) if values else None


class OriginQAdapter(QuantumAdapter):
    """Adapter for OriginQ Cloud (本源量子云) using pyqpanda3.

    This adapter uses pyqpanda3's QCloudService API for cloud task submission,
    which simplifies configuration by only requiring an API key.

    Note:
        The pyqpanda3 package is required for this adapter.
        Install with: pip install unified-quantum[originq]
    """

    name = "originq"

    def __init__(self) -> None:
        config = load_originq_config()
        self._api_key = config["api_key"]
        self._task_group_size = config.get("task_group_size", 200)
        self._available_qubits = config.get("available_qubits", [])

        # Lazy-loaded pyqpanda3 components
        self._service: Any = None
        self._QCloudOptions: Any = None
        self._QCloudJob: Any = None
        self._JobStatus: Any = None
        self._DataBase: Any = None
        self._convert_originir: Any = None

        # State for the current/last submitted job
        self._last_backend_name: str = "origin:wuyuan:d5"
        self._last_n_qubits: int | None = None

    def _ensure_imports(self) -> None:
        """Lazily import pyqpanda3 modules.

        Hardware and simulator backends are both accessed via ``QCloudService.backend()``.
        The returned ``QCloudBackend`` object exposes ``run()`` regardless of backend
        type — there is no separate simulator class.

        Version requirement (``pyqpanda3>=0.3.5``) is enforced via ``pyproject.toml``,
        not here. ``require()`` accepts only a module name.
        """
        if self._service is None:
            try:
                require("pyqpanda3", "originq")
                from pyqpanda3.intermediate_compiler import convert_originir_string_to_qprog
                from pyqpanda3.qcloud import (
                    DataBase,
                    JobStatus,
                    QCloudJob,
                    QCloudOptions,
                    QCloudService,
                )

                self._service = QCloudService(api_key=self._api_key)
                self._QCloudOptions = QCloudOptions
                self._QCloudJob = QCloudJob
                self._JobStatus = JobStatus
                self._DataBase = DataBase
                self._convert_originir = convert_originir_string_to_qprog
            except Exception as e:
                raise RuntimeError(f"Failed to initialize pyqpanda3 for OriginQ: {e}") from e

    def is_available(self) -> bool:
        """Check if the OriginQ adapter is available (credentials configured).

        Returns:
            bool: True if api_key is configured.
        """
        return bool(self._api_key)

    def list_backends(self) -> list[dict[str, Any]]:
        """Return raw OriginQ Cloud backend metadata.

        For each hardware backend (non-simulator), fetches chip_info() to
        populate qubit count, topology, fidelity, and coherence data.

        Returns:
            List of dicts with keys: ``name``, ``available``, ``num_qubits``,
            ``topology`` (list of [u, v] edge pairs), ``available_qubits``,
            ``avg_1q_fidelity``, ``avg_2q_fidelity``, ``avg_readout_fidelity``,
            ``coherence_t1``, ``coherence_t2``.
        """
        self._ensure_imports()
        raw: dict[str, bool] = self._service.backends()
        results: list[dict[str, Any]] = []

        for name, available in raw.items():
            entry: dict[str, Any] = {"name": name, "available": available}

            if name not in ORIGINQ_SIMULATOR_NAMES:
                try:
                    backend = self._service.backend(name)
                    ci = backend.chip_info()
                    entry["num_qubits"] = ci.qubits_num()
                    entry["topology"] = ci.get_chip_topology()
                    entry["available_qubits"] = ci.available_qubits()

                    # Fidelity and coherence from single/double qubit info
                    sq_list = ci.single_qubit_info()
                    entry["avg_1q_fidelity"] = _avg([sq.get_single_gate_fidelity() for sq in sq_list])
                    entry["avg_readout_fidelity"] = _avg([sq.get_readout_fidelity() for sq in sq_list])
                    entry["coherence_t1"] = _avg([sq.get_t1() for sq in sq_list])
                    entry["coherence_t2"] = _avg([sq.get_t2() for sq in sq_list])

                    dq_list = ci.double_qubits_info()
                    entry["avg_2q_fidelity"] = _avg([dq.get_fidelity() for dq in dq_list]) if dq_list else None
                except Exception:  # noqa: BLE001
                    # chip_info() may not be available for all backends
                    entry["num_qubits"] = 0
                    entry["topology"] = []
                    entry["available_qubits"] = []
                    entry["avg_1q_fidelity"] = None
                    entry["avg_2q_fidelity"] = None
                    entry["avg_readout_fidelity"] = None
                    entry["coherence_t1"] = None
                    entry["coherence_t2"] = None

            results.append(entry)

        return results

    # -------------------------------------------------------------------------
    # Circuit translation (OriginIR to QProg)
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> Any:
        """Convert OriginIR string to QProg using pyqpanda3.

        Args:
            originir: OriginIR format circuit string.

        Returns:
            QProg object for pyqpanda3.
        """
        self._ensure_imports()
        return self._convert_originir(originir)

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(self, circuit: str, *, shots: int = 1000, **kwargs: Any) -> str:
        """Submit a single circuit to OriginQ Cloud.

        Args:
            circuit: OriginIR format circuit string.
            shots: Number of measurement shots.
            **kwargs: Additional options:
                - backend_name: Backend name (e.g., 'origin:wuyuan:d5')
                - circuit_optimize: Enable circuit optimization (default: True)
                - measurement_amend: Enable measurement amendment (default: False)
                - auto_mapping: Enable automatic qubit mapping (default: False)

        Returns:
            Task ID string.
        """
        self._ensure_imports()

        backend_name = kwargs.get("backend_name", "origin:wuyuan:d5")

        # Simulator backends use the same QCloudBackend.run() API as hardware
        if backend_name in ORIGINQ_SIMULATOR_NAMES:
            return self._submit_simulator(backend_name, circuit, shots=shots)

        circuit_optimize = kwargs.get("circuit_optimize", True)
        measurement_amend = kwargs.get("measurement_amend", False)
        auto_mapping = kwargs.get("auto_mapping", False)

        # Get backend and cache backend name + qubit count for use in query()
        backend = self._service.backend(backend_name)
        self._last_backend_name = backend_name
        # chip_info() may fail if the backend has no chip data loaded.
        # Catch and ignore — we only need the job ID for tracking.
        try:
            self._last_n_qubits = backend.chip_info().qubits_num()
        except Exception:
            self._last_n_qubits = None

        # Convert OriginIR to QProg
        qprog = self.translate_circuit(circuit)

        # Configure options
        options = self._create_options(
            amend=measurement_amend,
            mapping=auto_mapping,
            optimization=circuit_optimize,
        )

        # Submit job
        job = backend.run(qprog, shots=shots, options=options)
        return job.job_id()

    def _submit_simulator(self, backend_name: str, circuit: str, *, shots: int = 1000) -> str:
        """Submit a circuit to an OriginQ simulator backend (full_amplitude, etc.).

        Simulator backends use the same ``QCloudBackend.run()`` API as hardware
        backends — there is no separate simulator class in pyqpanda3.

        Args:
            backend_name: Simulator backend name (e.g., ``"full_amplitude"``).
            circuit: OriginIR format circuit string.
            shots: Number of measurement shots.

        Returns:
            Task ID string.
        """
        self._ensure_imports()
        qprog = self.translate_circuit(circuit)
        backend = self._service.backend(backend_name)
        job = backend.run(qprog, shots=shots)
        return job.job_id()

    def submit_batch(self, circuits: list[str], *, shots: int = 1000, **kwargs: Any) -> str | list[str]:
        """Submit circuits as a group.

        Note: pyqpanda3 handles batch submission internally. This method
        submits circuits sequentially if needed for grouping.

        Args:
            circuits: List of OriginIR format circuit strings.
            shots: Number of measurement shots.
            **kwargs: Additional options (see submit()).

        Returns:
            Single task ID or list of task IDs if split into groups.
        """
        self._ensure_imports()

        backend_name = kwargs.get("backend_name", "origin:wuyuan:d5")

        # Simulator backends use the same QCloudBackend.run() API as hardware
        if backend_name in ORIGINQ_SIMULATOR_NAMES:
            return self._submit_batch_simulator(backend_name, circuits, shots=shots)

        circuit_optimize = kwargs.get("circuit_optimize", True)
        measurement_amend = kwargs.get("measurement_amend", False)
        auto_mapping = kwargs.get("auto_mapping", False)

        # Get backend and cache backend name + qubit count
        backend = self._service.backend(backend_name)
        self._last_backend_name = backend_name
        try:
            self._last_n_qubits = backend.chip_info().qubits_num()
        except Exception:
            self._last_n_qubits = None

        options = self._create_options(
            amend=measurement_amend,
            mapping=auto_mapping,
            optimization=circuit_optimize,
        )

        # If circuits fit in one group, submit all together
        if len(circuits) <= self._task_group_size:
            qprogs = [self.translate_circuit(c) for c in circuits]
            job = backend.run(qprogs, shots=shots, options=options)
            return job.job_id()

        # Split into groups
        task_ids: list[str] = []
        for i in range(0, len(circuits), self._task_group_size):
            group = circuits[i : i + self._task_group_size]
            qprogs = [self.translate_circuit(c) for c in group]
            job = backend.run(qprogs, shots=shots, options=options)
            task_ids.append(job.job_id())

        return task_ids

    def _submit_batch_simulator(self, backend_name: str, circuits: list[str], *, shots: int = 1000) -> list[str]:
        """Submit circuits to an OriginQ simulator backend.

        Args:
            backend_name: Simulator backend name.
            circuits: List of OriginIR format circuit strings.
            shots: Number of measurement shots.

        Returns:
            List of task IDs.
        """
        task_ids: list[str] = []
        for circuit in circuits:
            task_ids.append(self._submit_simulator(backend_name, circuit, shots=shots))
        return task_ids

    def _create_options(self, amend: bool, mapping: bool, optimization: bool) -> Any:
        """Create QCloudOptions from adapter parameters.

        Args:
            amend: Enable measurement amendment.
            mapping: Enable automatic qubit mapping.
            optimization: Enable circuit optimization.

        Returns:
            QCloudOptions instance.
        """
        options = self._QCloudOptions()
        options.set_amend(amend)
        options.set_mapping(mapping)
        options.set_optimization(optimization)
        return options

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    def query(self, taskid: str) -> dict[str, Any]:
        """Query a single task's status.

        Args:
            taskid: Task ID to query.

        Returns:
            dict with keys: taskid, status, result (if completed)
        """
        self._ensure_imports()

        job = self._QCloudJob(taskid)

        # Always use job.query() (not job.status()) — it returns a QCloudResult
        # with the authoritative status from the cloud, even for failed/unknown
        # status codes that job.status() cannot parse.
        qr = job.query()
        status_name = qr.job_status().name
        error_msg = qr.error_message()
        counts = qr.get_counts()

        if status_name == "FINISHED":
            return {
                "taskid": taskid,
                "status": TASK_STATUS_SUCCESS,
                "result": self._format_counts(counts),
            }
        elif status_name == "FAILED" or status_name == "???":
            # For "???" (unknown status), check if there's an error message or
            # empty counts — both indicate the task failed.
            if error_msg or not counts:
                return {
                    "taskid": taskid,
                    "status": TASK_STATUS_FAILED,
                    "result": {"error": error_msg or "Job failed on cloud (unknown status)"},
                }
            # If no error and has counts, treat as success despite unknown status
            return {
                "taskid": taskid,
                "status": TASK_STATUS_SUCCESS,
                "result": self._format_counts(counts),
            }
        else:
            # RUNNING, QUEUING, WAITING → treat as running
            return {
                "taskid": taskid,
                "status": TASK_STATUS_RUNNING,
            }

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        """Query multiple tasks and merge results.

        Args:
            taskids: List of task IDs to query.

        Returns:
            Combined result dict with status and merged results.
        """
        taskinfo: dict[str, Any] = {"status": TASK_STATUS_SUCCESS, "result": []}

        for taskid in taskids:
            result_i = self.query(taskid)

            if result_i["status"] == TASK_STATUS_FAILED:
                taskinfo["status"] = TASK_STATUS_FAILED
                break
            elif result_i["status"] == TASK_STATUS_RUNNING:
                taskinfo["status"] = TASK_STATUS_RUNNING

            if taskinfo["status"] == TASK_STATUS_SUCCESS:
                taskinfo["result"].extend(result_i.get("result", []))

        return taskinfo

    def _format_counts(self, counts: Any) -> dict[str, int]:
        """Format pyqpanda3 counts to a simple {bitstring: shots} dict.

        Args:
            counts: Counts from QCloudResult.get_counts().

        Returns:
            Dict mapping bitstrings to shot counts, e.g. {"0000": 512, "1111": 480}.
        """
        if isinstance(counts, dict):
            return dict(counts)
        elif isinstance(counts, list):
            # Handle list of counts (for batch results) — merge all into one dict
            merged: dict[str, int] = {}
            for c in counts:
                if isinstance(c, dict):
                    for k, v in c.items():
                        merged[k] = merged.get(k, 0) + v
            return merged
        else:
            return {str(counts): 1}

    # -------------------------------------------------------------------------
    # Synchronous wait
    # -------------------------------------------------------------------------

    def query_sync(
        self,
        taskid: str | list[str],
        interval: float = 2.0,
        timeout: float = 60.0,
        retry: int = 5,
    ) -> list[dict[str, Any]]:
        """Poll task status until completion or timeout.

        Args:
            taskid: Task ID or list of task IDs.
            interval: Polling interval in seconds.
            timeout: Maximum wait time in seconds.
            retry: Number of retries on query failure.

        Returns:
            List of result dicts.

        Raises:
            TimeoutError: If timeout is reached.
            RuntimeError: If task fails or retry exhausted.
        """
        taskids = [taskid] if isinstance(taskid, str) else taskid
        starttime = time.time()

        while True:
            elapsed = time.time() - starttime
            if elapsed > timeout:
                raise TimeoutError("Reached the maximum timeout.")

            time.sleep(interval)

            taskinfo = self.query_batch(taskids)

            if taskinfo["status"] == TASK_STATUS_RUNNING:
                continue
            if taskinfo["status"] == TASK_STATUS_SUCCESS:
                return taskinfo.get("result", [])
            if taskinfo["status"] == TASK_STATUS_FAILED:
                raise RuntimeError(f"Failed to execute, errorinfo = {taskinfo.get('result')}")

            if retry > 0:
                retry -= 1
                warnings.warn(f"Query failed. Retry remains {retry} times.", stacklevel=2)
            else:
                raise RuntimeError("Retry count exhausted.")

    # -------------------------------------------------------------------------
    # Chip characterization
    # -------------------------------------------------------------------------

    def get_chip_characterization(self, backend_name: str):
        """Return per-qubit and per-pair calibration data for a hardware backend.

        Parameters
        ----------
        backend_name:
            Full backend name, e.g. ``"origin:wuyuan:d5"``.

        Returns
        -------
        ChipCharacterization or None
            None if the backend is not found or chip info is unavailable.
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

        self._ensure_imports()
        backend = self._service.backend(backend_name)

        try:
            ci = backend.chip_info()
        except Exception:
            return None

        # Available qubits
        available_qubits = tuple(ci.available_qubits())

        # Connectivity
        raw_topo = ci.get_chip_topology() or []
        connectivity = tuple(QubitTopology(u=u, v=v) for u, v in raw_topo)

        # Per-qubit data
        single_qubit_data: list[SingleQubitData] = []
        for sq in ci.single_qubit_info() or []:
            fid_0 = sq.get_readout_fidelity_0() if hasattr(sq, "get_readout_fidelity_0") else None
            fid_1 = sq.get_readout_fidelity_1() if hasattr(sq, "get_readout_fidelity_1") else None
            avg_ro = sq.get_readout_fidelity() if hasattr(sq, "get_readout_fidelity") else None
            single_qubit_data.append(
                SingleQubitData(
                    qubit_id=sq.get_qubit_id() if hasattr(sq, "get_qubit_id") else 0,
                    t1=sq.get_t1(),
                    t2=sq.get_t2(),
                    single_gate_fidelity=sq.get_single_gate_fidelity(),
                    readout_fidelity_0=fid_0,
                    readout_fidelity_1=fid_1,
                    avg_readout_fidelity=avg_ro,
                )
            )

        # Per-pair data
        # Build a qubit-pair lookup from the topology so we can look up
        # (u, v) by index even when double_qubits_info() objects lack
        # get_qubit_u() / get_qubit_v() methods (the fallback used before).
        topo_by_index: dict[int, tuple[int, int]] = {i: (u, v) for i, (u, v) in enumerate(raw_topo)}

        two_qubit_data: list[TwoQubitData] = []
        for idx, dq in enumerate(ci.double_qubits_info() or []):
            fid = dq.get_fidelity() if hasattr(dq, "get_fidelity") else None
            # Prefer the dedicated accessors if available; otherwise use topology index
            if hasattr(dq, "get_qubit_u") and hasattr(dq, "get_qubit_v"):
                u = dq.get_qubit_u()
                v = dq.get_qubit_v()
            else:
                u, v = topo_by_index.get(idx, (0, 0))
            two_qubit_data.append(
                TwoQubitData(
                    qubit_u=u,
                    qubit_v=v,
                    gates=(TwoQubitGateData(gate="cx", fidelity=fid),),
                )
            )

        # Global info
        single_gates: list[str] = []
        two_gates: list[str] = []
        sq_gate_time: float | None = None
        tq_gate_time: float | None = None
        try:
            cfg = backend.configuration()
            gates = cfg.supported_gates() if hasattr(cfg, "supported_gates") else []
            for g in gates:
                g_lower = g.lower()
                if (
                    g_lower in {"h", "x", "y", "z", "s", "sx", "t", "i", "rx", "ry", "rz", "u1", "u2", "u3"}
                    and g not in single_gates
                ):
                    single_gates.append(g)
                elif g_lower in {"cnot", "cz", "iswap", "ecr", "swap"} and g not in two_gates:
                    two_gates.append(g)
            if hasattr(cfg, "single_qubit_gate_time"):
                sq_gate_time = float(cfg.single_qubit_gate_time())
            if hasattr(cfg, "two_qubit_gate_time"):
                tq_gate_time = float(cfg.two_qubit_gate_time())
        except Exception:
            pass

        return ChipCharacterization(
            platform=Platform.ORIGINQ,
            chip_name=backend_name,
            full_id=f"originq:{backend_name}",
            available_qubits=available_qubits,
            connectivity=connectivity,
            single_qubit_data=tuple(single_qubit_data),
            two_qubit_data=tuple(two_qubit_data),
            global_info=ChipGlobalInfo(
                single_qubit_gates=tuple(single_gates),
                two_qubit_gates=tuple(two_gates),
                single_qubit_gate_time=sq_gate_time,
                two_qubit_gate_time=tq_gate_time,
            ),
            calibrated_at=datetime.now(timezone.utc).isoformat(),
        )

    # -------------------------------------------------------------------------
    # Dry-run validation
    # -------------------------------------------------------------------------

    def dry_run(self, originir: str, *, shots: int = 1000, **kwargs: Any) -> DryRunResult:
        """Dry-run validation for OriginQ Cloud backends.

        Validates offline by calling translate_circuit() which internally calls
        convert_originir_string_to_qprog() — a purely local pyqpanda3 call.
        The pyqpanda3 compiler will reject unknown gates.

        This method makes NO network calls.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        from uniqc.circuit_adapter import OriginQCircuitAdapter
        from uniqc.task.adapters.base import _dry_run_failed, _dry_run_success

        backend_name = kwargs.get("backend_name", "origin:wuyuan:d5")

        # Extract qubit count from OriginIR QINIT line (no API call)
        circuit_qubits: int | None = None
        try:
            for line in originir.splitlines():
                line = line.strip()
                if line.startswith("QINIT"):
                    parts = line.split()
                    if len(parts) >= 2:
                        circuit_qubits = int(parts[1])
                    break
        except Exception:
            pass

        # Attempt translation — this is a purely local pyqpanda3 call
        try:
            self.translate_circuit(originir)
        except Exception as e:
            return _dry_run_failed(
                str(e),
                details=(
                    f"OriginIR translation to QProg failed for backend '{backend_name}': {e}. "
                    "The circuit may use gates not supported by pyqpanda3."
                ),
                backend_name=backend_name,
            )

        return _dry_run_success(
            (
                f"Dry-run passed for '{backend_name}': OriginIR translates cleanly "
                f"to QProg. Qubits={circuit_qubits}, shots={shots}"
            ),
            backend_name=backend_name,
            circuit_qubits=circuit_qubits,
            supported_gates=tuple(sorted(OriginQCircuitAdapter.SUPPORTED_GATES)),
        )
