"""Quafu backend adapter.

Translates OriginIR circuits to Quafu QuantumCircuit objects and submits
via the ``quafu`` package (User / Task API).  No raw REST calls.

Installation:
    pip install unified-quantum[quafu]
"""

from __future__ import annotations

__all__ = ["QuafuAdapter"]

from typing import TYPE_CHECKING, Any

from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
)
from uniqc.backend_adapter.task.config import load_quafu_config
from uniqc.backend_adapter.task.optional_deps import MissingDependencyError, check_quafu

if TYPE_CHECKING:
    pass  # type hints use string annotations via `from __future__ import annotations`


# Static qubit count map for offline dry-run qubit validation.
# Sources: BAQIS ScQ public chip specifications.
CHIP_QUBIT_COUNTS: dict[str, int] = {
    "ScQ-P10": 10,
    "ScQ-P18": 18,
    "ScQ-P136": 136,
    "ScQ-P10C": 10,
    "Dongling": 24,
    "ScQ-Sim10": 10,
    "ScQ-Sim": 25,
    "ScQ-P5": 5,
    "ScQ-P102": 102,
    "ScQ-P21": 21,
    "ScQ-P3": 3,
    "ScQ-TEST": 5,
    "Baiwang": 100,
    "Miaofeng": 44,
    "Haituo": 136,
    "Baihua": 10,
    "Yunmeng": 18,
    "Xiang": 21,
}


def _avg(values: list[float]) -> float | None:
    """Return the arithmetic mean of a list, or None if the list is empty."""
    return sum(values) / len(values) if values else None


def _compute_quafu_fidelity(chip_info: dict[str, Any]) -> dict[str, Any]:
    """Extract fidelity and coherence metrics from a Quafu get_chip_info() result.

    Available:
      - Avg. 2Q fidelity: from ``full_info.topological_structure[edge]['cz']['fidelity']``
      - Avg. T1 / T2: from ``full_info.qubits_info[q]['T1']`` / ``['T2']`` (microseconds)

    Not available from Quafu API:
      - Avg. 1Q gate fidelity
      - Avg. readout fidelity

    Returns:
        dict with keys: avg_1q_fidelity (None), avg_2q_fidelity, avg_readout_fidelity (None),
        coherence_t1, coherence_t2.
    """
    full_info: dict[str, Any] = chip_info.get("full_info") or {}

    # T1/T2 from qubits_info (values are in microseconds already)
    t1s, t2s = [], []
    qubits_info: dict[str, dict[str, Any]] = full_info.get("qubits_info") or {}
    for qdata in qubits_info.values():
        if (t1 := qdata.get("T1")) is not None:
            t1s.append(float(t1))
        if (t2 := qdata.get("T2")) is not None:
            t2s.append(float(t2))

    # 2Q fidelity from topological_structure (directed edges, take each once)
    seen: set[tuple[int, int]] = set()
    tq_fids: list[float] = []
    topo: dict[str, dict[str, Any]] = full_info.get("topological_structure") or {}
    for edge_key, gate_data in topo.items():
        parts = edge_key.split("_")
        if len(parts) == 2:
            u, v = (
                int(parts[0][1:]) if parts[0].startswith("Q") else int(parts[0]),
                int(parts[1][1:]) if parts[1].startswith("Q") else int(parts[1]),
            )
            key = (u, v)
            if key not in seen:
                seen.add(key)
                if (f := gate_data.get("cz", {}).get("fidelity")) is not None:
                    tq_fids.append(float(f))

    return {
        "avg_1q_fidelity": None,  # not available from Quafu API
        "avg_2q_fidelity": _avg(tq_fids) if tq_fids else None,
        "avg_readout_fidelity": None,  # not available from Quafu API
        "coherence_t1": _avg(t1s),
        "coherence_t2": _avg(t2s),
    }


class QuafuAdapter(QuantumAdapter):
    """Adapter for the BAQIS Quafu (ScQ) quantum cloud platform.

    Raises:
        MissingDependencyError: If quafu package is not installed.
    """

    name = "quafu"

    # Valid chip IDs (known ScQ series chips and simulators)
    VALID_CHIP_IDS = frozenset(
        {
            "ScQ-P10",
            "ScQ-P18",
            "ScQ-P136",
            "ScQ-P10C",
            "Dongling",
            "ScQ-Sim10",
            "ScQ-Sim",
            "ScQ-P5",
            "ScQ-P102",
            "ScQ-P21",
            "ScQ-P3",
            "ScQ-TEST",
            "Baiwang",
            "Miaofeng",
            "Haituo",
            "Baihua",
            "Yunmeng",
            "Xiang",
        }
    )

    # Upper limit on the number of groups retained in _task_history.
    # Beyond this threshold the oldest entry is evicted to avoid unbounded
    # memory growth in long-running processes.
    _MAX_HISTORY_GROUPS: int = 100

    @property
    def api_token(self) -> str:
        """Return the API token used for Quafu authentication.

        Returns:
            str: The Quafu API token.
        """
        return self._api_token

    def __init__(self) -> None:
        # Check if quafu is available
        if not check_quafu():
            raise MissingDependencyError("quafu", "quafu")

        config = load_quafu_config()
        self._api_token: str = config["api_token"]
        # Internal task history: group_name -> {taskid: task_index}
        # Updated on each submit_batch call so retrieve() can work without
        # requiring the caller to pass history.
        self._task_history: dict[str, dict[str, int]] = {}
        # Track insertion order so we can evict the oldest group when the
        # cap is reached (simple FIFO).
        self._history_order: list[str] = []

        from quafu import QuantumCircuit, Task, User

        self._QuantumCircuit = QuantumCircuit
        self._Task = Task
        self._User = User

    def is_available(self) -> bool:
        """Check if the Quafu adapter is available (quafu package installed).

        Returns:
            bool: True if the quafu package was successfully imported.
        """
        return check_quafu()

    def list_backends(self) -> list[dict[str, Any]]:
        """Return raw Quafu backend metadata.

        For hardware backends, fetches chip_info() to populate fidelity and
        coherence data.

        Returns:
            List of dicts with keys: ``name``, ``num_qubits``, ``status``,
            ``task_in_queue``, ``qv``, ``valid_gates``, plus fidelity/coherence
            fields (avg_1q_fidelity, avg_2q_fidelity, avg_readout_fidelity,
            coherence_t1, coherence_t2).
        """
        user = self._User(api_token=self._api_token)
        user.save_apitoken()
        raw_backends = user.get_available_backends()
        result: list[dict[str, Any]] = []
        for name, backend in raw_backends.items():
            entry: dict[str, Any] = {
                "name": name,
                "num_qubits": backend.qubit_num,
                "status": backend.status,
                "task_in_queue": backend.task_in_queue,
                "qv": backend.qv,
                "system_id": backend.system_id,
                "valid_gates": backend.get_valid_gates(),
            }
            # Attempt to fetch chip info for fidelity / coherence
            try:
                chip_info = backend.get_chip_info()
                if isinstance(chip_info, dict) and chip_info.get("full_info"):
                    entry.update(_compute_quafu_fidelity(chip_info))
            except Exception:  # noqa: BLE001
                pass
            result.append(entry)
        return result

    # -------------------------------------------------------------------------
    # Circuit translation
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> "QuantumCircuit":  # noqa: UP037,F821
        """Translate an OriginIR string to a Quafu QuantumCircuit."""
        from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser

        lines = originir.splitlines()
        qc: "QuantumCircuit | None" = None  # noqa: UP037,F821

        for line in lines:
            try:
                operation, qubit, cbit, parameter, dagger_flag, control_qubits = OriginIR_LineParser.parse_line(line)
            except NotImplementedError:
                raise RuntimeError(f"Unknown OriginIR operation in quafu adapter: {line.strip()}") from None
            if operation == "QINIT":
                qc = self._QuantumCircuit(int(qubit))  # type: ignore[arg-type]
                continue
            if qc is None:
                raise RuntimeError("QINIT must appear before any gate operation.")
            qc = self._reconstruct_qasm(qc, operation, qubit, cbit, parameter, bool(dagger_flag))

        if qc is None:
            raise RuntimeError("OriginIR string produced no circuit.")
        return qc

    def _reconstruct_qasm(
        self,
        qc: "QuantumCircuit",  # noqa: UP037,F821
        operation: str | None,
        qubit: int | list[int],
        cbit: int | None,
        parameter: float | list[float] | None,
        dagger_flag: bool = False,
    ) -> "QuantumCircuit":  # noqa: UP037,F821
        """Append a single gate to a Quafu QuantumCircuit based on parsed OriginIR.

        This method is called internally by translate_circuit() for each
        line of OriginIR after QINIT. It maps OriginIR gate names to
        Quafu QuantumCircuit method calls.

        Args:
            qc: The Quafu QuantumCircuit to modify (modified in-place).
            operation: The gate operation name (e.g., 'RX', 'H', 'CNOT').
            qubit: Target qubit index or list of indices for multi-qubit gates.
            cbit: Classical bit index for MEASURE operations.
            parameter: Rotation angle for parametric gates (e.g., RX, RY, RZ).
            dagger_flag: Whether the gate is daggered (for S, SX, T).

        Returns:
            The modified QuantumCircuit (same object as input).

        Raises:
            RuntimeError: If the operation is not supported by this adapter.

        Note:
            Supported gates: RX, RY, RZ, H, X, Y, Z, S, SX, T,
            CZ, CNOT, SWAP, ISWAP, MEASURE, BARRIER.
            CREG and None operations are silently ignored.
        """
        if operation == "RX":
            qc.rx(int(qubit), parameter)  # type: ignore[arg-type]
        elif operation == "RY":
            qc.ry(int(qubit), parameter)  # type: ignore[arg-type]
        elif operation == "RZ":
            qc.rz(int(qubit), parameter)  # type: ignore[arg-type]
        elif operation == "H":
            qc.h(int(qubit))  # type: ignore[arg-type]
        elif operation == "X":
            qc.x(int(qubit))  # type: ignore[arg-type]
        elif operation == "Y":
            qc.y(int(qubit))  # type: ignore[arg-type]
        elif operation == "Z":
            qc.z(int(qubit))  # type: ignore[arg-type]
        elif operation == "S":
            if dagger_flag:
                qc.sdg(int(qubit))  # type: ignore[arg-type]
            else:
                qc.s(int(qubit))  # type: ignore[arg-type]
        elif operation == "SX":
            if dagger_flag:
                qc.sxdg(int(qubit))  # type: ignore[arg-type]
            else:
                qc.sx(int(qubit))  # type: ignore[arg-type]
        elif operation == "T":
            if dagger_flag:
                qc.tdg(int(qubit))  # type: ignore[arg-type]
            else:
                qc.t(int(qubit))  # type: ignore[arg-type]
        elif operation == "CZ":
            qc.cz(int(qubit[0]), int(qubit[1]))  # type: ignore[index]
        elif operation == "CNOT":
            qc.cnot(int(qubit[0]), int(qubit[1]))  # type: ignore[index]
        elif operation == "SWAP":
            qc.swap(int(qubit[0]), int(qubit[1]))  # type: ignore[index]
        elif operation == "ISWAP":
            qc.iswap(int(qubit[0]), int(qubit[1]))  # type: ignore[index]
        elif operation == "MEASURE":
            qc.measure([int(qubit)], [int(cbit)])  # type: ignore[list-item]
        elif operation == "BARRIER":
            # BARRIER is a no-op for execution; skip without error
            pass
        elif operation is None or operation == "CREG":
            pass
        else:
            raise RuntimeError(f"Unknown OriginIR operation in quafu adapter: {operation}.")
        return qc

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(
        self,
        circuit: "QuantumCircuit",  # noqa: UP037,F821
        *,
        shots: int = 10000,
        wait: bool = False,
        **kwargs: Any,
    ) -> str:
        """Submit a single circuit to Quafu.

        Args:
            circuit: Quafu QuantumCircuit object.
            shots: Number of measurement shots (default: 10000).
            wait: If True, block until the server acknowledges receipt (default: False).
            **kwargs: Additional options:
                - chip_id: Quafu chip ID (required, e.g. 'ScQ-P18')
                - auto_mapping: Enable automatic qubit mapping (default: True)
                - task_name: Optional task name string

        Returns:
            Task ID string.
        """
        chip_id: str | None = kwargs.get("chip_id")
        auto_mapping: bool = kwargs.get("auto_mapping", True)
        task_name: str | None = kwargs.get("task_name")

        if chip_id not in self.VALID_CHIP_IDS:
            raise RuntimeError(
                r"Invalid chip_id. "
                r"Current quafu chip_id list: "
                r"ScQ-P10, ScQ-P18, ScQ-P136, ScQ-P10C, Dongling, "
                r"ScQ-Sim10, ScQ-Sim, ScQ-P5, ScQ-P102, ScQ-P21, ScQ-P3, ScQ-TEST, "
                r"Baiwang, Miaofeng, Haituo, Baihua, Yunmeng, Xiang"
            )

        user = self._User(api_token=self._api_token)
        user.save_apitoken()
        task = self._Task()
        task.config(backend=chip_id, shots=shots, compile=auto_mapping)

        result = task.send(circuit, wait=wait, name=task_name)  # type: ignore[arg-type]
        return result.taskid

    def submit_batch(
        self,
        circuits: list["QuantumCircuit"],  # noqa: UP037,F821
        *,
        shots: int = 10000,
        wait: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Submit multiple circuits as a group to Quafu.

        Args:
            circuits: List of Quafu QuantumCircuit objects.
            shots: Number of measurement shots per circuit (default: 10000).
            wait: If True, block until server acknowledges each submission (default: False).
            **kwargs: Additional options:
                - chip_id: Quafu chip ID (required)
                - auto_mapping: Enable automatic qubit mapping (default: True)
                - task_name: Base task name (suffixed with -0, -1, ...)
                - group_name: Group name for server-side batch tracking

        Returns:
            List of task ID strings.
        """
        chip_id: str | None = kwargs.get("chip_id")
        auto_mapping: bool = kwargs.get("auto_mapping", True)
        task_name: str | None = kwargs.get("task_name")
        group_name: str | None = kwargs.get("group_name")

        if chip_id not in self.VALID_CHIP_IDS:
            raise RuntimeError(
                r"Invalid chip_id. "
                r"Current quafu chip_id list: "
                r"ScQ-P10, ScQ-P18, ScQ-P136, ScQ-P10C, Dongling, "
                r"ScQ-Sim10, ScQ-Sim, ScQ-P5, ScQ-P102, ScQ-P21, ScQ-P3, ScQ-TEST, "
                r"Baiwang, Miaofeng, Haituo, Baihua, Yunmeng, Xiang"
            )

        user = self._User(api_token=self._api_token)
        user.save_apitoken()
        task = self._Task()
        task.config(backend=chip_id, shots=shots, compile=auto_mapping)

        taskids: list[str] = []
        for index, c in enumerate(circuits):
            result = task.send(
                c,
                wait=wait,
                name=f"{task_name}-{index}" if task_name else None,
                group=group_name,  # type: ignore[arg-type]
            )
            taskids.append(result.taskid)

        # Maintain history so query() can retrieve without caller-supplied history.
        # Apply FIFO eviction when the cap is reached.
        if group_name:
            if group_name not in self._task_history:
                if len(self._history_order) >= self._MAX_HISTORY_GROUPS:
                    oldest = self._history_order.pop(0)
                    self._task_history.pop(oldest, None)
                self._task_history[group_name] = {}
                self._history_order.append(group_name)
            for i, taskid in enumerate(taskids):
                self._task_history[group_name][taskid] = i

        return taskids

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    def query(self, taskid: str) -> dict[str, Any]:
        """Query a single Quafu task's status via SDK ``Task.retrieve()``.

        Uses the internally maintained history dict so the caller does not
        need to pass any additional context.
        """
        user = self._User(api_token=self._api_token)
        user.save_apitoken()
        task = self._Task()

        # Build a minimal history dict: try all known groups.
        # Task.retrieve(taskid, history) will look up the taskid in history.
        for group_name, id_to_idx in self._task_history.items():
            if taskid in id_to_idx:
                result = task.retrieve(taskid, history={group_name: {taskid: id_to_idx[taskid]}})
                return self._result_to_dict(result)

        # Fallback: try without history (may work if server accepts taskid alone)
        result = task.retrieve(taskid)
        return self._result_to_dict(result)

    def _result_to_dict(self, result) -> dict[str, Any]:
        """Convert a Quafu ExecResult to the adapter's standard result dict.

        This method normalizes Quafu's task status strings and extracts
        measurement results when the task has completed successfully.

        Args:
            result: A quafu.ExecResult object from Task.retrieve().

        Returns:
            dict with keys:
                - ``status``: ``'success'`` | ``'failed'`` | ``'running'``
                - ``result``: dict with ``counts`` and ``probabilities`` (when success)

        Note:
            The Quafu status strings are mapped as follows:
            - 'Completed' -> 'success'
            - 'Running', 'In Queue' -> 'running'
            - 'Failed', 'Canceled' -> 'failed'
        """
        status_map = {
            "Completed": TASK_STATUS_SUCCESS,
            "Running": TASK_STATUS_RUNNING,
            "In Queue": TASK_STATUS_RUNNING,
            "Failed": TASK_STATUS_FAILED,
            "Canceled": TASK_STATUS_FAILED,
        }
        status_str = result.task_status
        status = status_map.get(status_str, TASK_STATUS_RUNNING)
        if status == TASK_STATUS_SUCCESS:
            return {
                "status": status,
                "result": dict(result.counts),
            }
        return {"status": status}

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        """Query multiple Quafu tasks and merge results."""
        taskinfo: dict[str, Any] = {"status": TASK_STATUS_SUCCESS, "result": []}
        for taskid in taskids:
            result_i = self.query(taskid)
            if result_i["status"] == TASK_STATUS_FAILED:
                taskinfo["status"] = TASK_STATUS_FAILED
                break
            elif result_i["status"] == TASK_STATUS_RUNNING:
                taskinfo["status"] = TASK_STATUS_RUNNING
            if taskinfo["status"] == TASK_STATUS_SUCCESS:
                taskinfo["result"].append(result_i.get("result", {}))
        return taskinfo

    def query_sync(
        self,
        taskid: str | list[str],
        interval: float = 2.0,
        timeout: float = 60.0,
    ) -> list[dict[str, Any]]:
        """Poll task status until completion or timeout.

        Args:
            taskid: Task ID or list of task IDs.
            interval: Polling interval in seconds (default: 2.0).
            timeout: Maximum wait time in seconds (default: 60.0).

        Returns:
            List of result dicts (one per task ID).

        Raises:
            TimeoutError: If timeout is reached before completion.
        """
        import time

        taskids = [taskid] if isinstance(taskid, str) else taskid
        start = time.time()

        while True:
            if time.time() - start > timeout:
                raise TimeoutError(f"Task(s) timed out after {timeout}s.")

            time.sleep(interval)

            batch_result = self.query_batch(taskids)
            if batch_result["status"] != TASK_STATUS_RUNNING:
                return batch_result.get("result", [])

    # -------------------------------------------------------------------------
    # Chip characterization
    # -------------------------------------------------------------------------

    def get_chip_characterization(self, chip_name: str):
        """Return per-qubit and per-pair calibration data for a Quafu chip.

        Parameters
        ----------
        chip_name:
            Quafu chip ID, e.g. ``"ScQ-P18"``.

        Returns
        -------
        ChipCharacterization or None
        """
        from datetime import datetime, timezone

        from uniqc.backend_adapter.backend_info import Platform, QubitTopology
        from uniqc.cli.chip_info import (
            ChipCharacterization,
            ChipGlobalInfo,
            SingleQubitData,
            TwoQubitData,
            TwoQubitGateData,
        )

        user = self._User(api_token=self._api_token)
        user.save_apitoken()
        raw_backends = user.get_available_backends()

        backend = raw_backends.get(chip_name)
        if backend is None:
            return None

        try:
            chip_info = backend.get_chip_info()
        except Exception:
            return None

        full_info: dict[str, Any] = chip_info.get("full_info") or {}

        # Available qubits: Quafu doesn't expose an explicit list, so use
        # all qubits that appear in qubits_info, or range(0, qubit_num)
        num_qubits = backend.qubit_num
        qubits_info: dict[str, dict[str, Any]] = full_info.get("qubits_info") or {}
        available_qubits: list[int] = []
        if qubits_info:
            # keys are either "Q0", "Q1", ... or "0", "1", ...
            for key in qubits_info:
                qid = int(key[1:]) if key.startswith("Q") else int(key)
                available_qubits.append(qid)
            available_qubits = sorted(set(available_qubits))
        else:
            available_qubits = list(range(num_qubits))

        # Per-qubit data
        single_qubit_data: list[SingleQubitData] = []
        for key, qdata in qubits_info.items():
            qid = int(key[1:]) if key.startswith("Q") else int(key)
            single_qubit_data.append(
                SingleQubitData(
                    qubit_id=qid,
                    t1=float(qdata["T1"]) if qdata.get("T1") is not None else None,
                    t2=float(qdata["T2"]) if qdata.get("T2") is not None else None,
                    single_gate_fidelity=None,  # not available from Quafu API
                    readout_fidelity_0=None,
                    readout_fidelity_1=None,
                    avg_readout_fidelity=None,
                )
            )

        # Per-pair data from topological_structure
        two_qubit_data: list[TwoQubitData] = []
        seen: set[tuple[int, int]] = set()
        topo: dict[str, dict[str, Any]] = full_info.get("topological_structure") or {}
        for edge_key, gate_data in topo.items():
            parts = edge_key.split("_")
            if len(parts) != 2:
                continue
            u = int(parts[0][1:]) if parts[0].startswith("Q") else int(parts[0])
            v = int(parts[1][1:]) if parts[1].startswith("Q") else int(parts[1])
            key = tuple(sorted([u, v]))
            if key in seen:
                continue
            seen.add(key)
            gates: list[TwoQubitGateData] = []
            for gate_name, gate_attrs in gate_data.items():
                if isinstance(gate_attrs, dict):
                    fid = float(gate_attrs["fidelity"]) if gate_attrs.get("fidelity") is not None else None
                else:
                    fid = None
                gates.append(TwoQubitGateData(gate=gate_name, fidelity=fid))
            two_qubit_data.append(TwoQubitData(qubit_u=u, qubit_v=v, gates=tuple(gates)))

        # Global info
        valid_gates = backend.get_valid_gates() if hasattr(backend, "get_valid_gates") else []
        sq_gates, tq_gates = [], []
        for g in valid_gates:
            g_lower = g.lower()
            if g_lower in {"h", "x", "y", "z", "s", "sx", "t", "rx", "ry", "rz", "u1", "u3"} and g not in sq_gates:
                sq_gates.append(g)
            elif g_lower in {"cx", "cnot", "cz", "iswap", "swap"} and g not in tq_gates:
                tq_gates.append(g)

        # Gate times — quafu backend may expose them via gate_time attribute
        sq_time: float | None = None
        tq_time: float | None = None
        try:
            if hasattr(backend, "gate_time"):
                gt = backend.gate_time
                if isinstance(gt, dict):
                    sq_time = gt.get("single", None)
                    tq_time = gt.get("double", None)
        except Exception:
            pass

        return ChipCharacterization(
            platform=Platform.QUAFU,
            chip_name=chip_name,
            full_id=f"quafu:{chip_name}",
            available_qubits=tuple(available_qubits),
            connectivity=tuple(QubitTopology(u=u, v=v) for u, v in seen),
            single_qubit_data=tuple(single_qubit_data),
            two_qubit_data=tuple(two_qubit_data),
            global_info=ChipGlobalInfo(
                single_qubit_gates=tuple(sq_gates),
                two_qubit_gates=tuple(tq_gates),
                single_qubit_gate_time=sq_time,
                two_qubit_gate_time=tq_time,
            ),
            calibrated_at=datetime.now(timezone.utc).isoformat(),
        )

    # -------------------------------------------------------------------------
    # Dry-run validation
    # -------------------------------------------------------------------------

    def dry_run(self, originir: str, *, shots: int = 10000, **kwargs: Any) -> DryRunResult:
        """Dry-run validation for Quafu backends.

        Validates offline by:
        1. Extracting qubit count from OriginIR QINIT line (no API call).
        2. Checking chip_id in VALID_CHIP_IDS (static check).
        3. Checking qubit count against CHIP_QUBIT_COUNTS (static map).
        4. Attempting translation via translate_circuit() (no API call —
           catches unsupported gates).

        This method makes NO network calls.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        from uniqc.backend_adapter.task.adapters.base import _dry_run_failed, _dry_run_success

        chip_id: str | None = kwargs.get("chip_id")

        # Step 1: Extract qubit count from OriginIR QINIT line (no API call)
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

        # Step 2: Validate chip_id against static VALID_CHIP_IDS
        if chip_id is None:
            return _dry_run_success(
                "Dry-run passed (no chip_id): OriginIR is syntactically valid. "
                "Specify --chip-id for full chip-level validation.",
                backend_name=None,
                circuit_qubits=circuit_qubits,
                warnings=("No chip_id provided — skipping chip-level validation.",),
            )

        if chip_id not in self.VALID_CHIP_IDS:
            return _dry_run_failed(
                f"chip_id '{chip_id}' is not in the known Quafu chip list",
                details=(f"Invalid chip_id. Valid chips: {', '.join(sorted(self.VALID_CHIP_IDS))}"),
                backend_name=chip_id,
            )

        # Step 3: Qubit count check against static chip map
        if circuit_qubits is not None:
            max_qubits = CHIP_QUBIT_COUNTS.get(chip_id)
            if max_qubits is not None and circuit_qubits > max_qubits:
                return _dry_run_failed(
                    f"circuit requires {circuit_qubits} qubits but chip '{chip_id}' has {max_qubits}",
                    details=f"Qubit count validation failed: circuit={circuit_qubits}, chip={max_qubits}",
                    backend_name=chip_id,
                )

        # Step 4: Attempt translation (catches unsupported gates)
        try:
            self.translate_circuit(originir)
        except RuntimeError as e:
            err_str = str(e)
            if "Unknown OriginIR operation" in err_str or "not supported" in err_str.lower():
                return _dry_run_failed(
                    err_str,
                    details=(
                        f"Circuit contains gates not supported by Quafu adapter. "
                        f"Supported gates: {', '.join(sorted(self.SUPPORTED_GATES))}. "
                        f"Error: {e}"
                    ),
                    backend_name=chip_id,
                )
            return _dry_run_failed(
                str(e),
                details=f"Translation failed with unexpected RuntimeError: {e}",
                backend_name=chip_id,
            )
        except Exception as e:
            return _dry_run_failed(
                str(e),
                details=f"Failed to translate OriginIR to Quafu QuantumCircuit: {e}",
                backend_name=chip_id,
            )

        # Shots validation — Quafu default max is typically 100000
        MAX_QUAFU_SHOTS = 100000
        if shots > MAX_QUAFU_SHOTS:
            return _dry_run_failed(
                f"shots ({shots}) exceeds Quafu maximum ({MAX_QUAFU_SHOTS})",
                details="Shot count validation failed.",
                backend_name=chip_id,
            )

        return _dry_run_success(
            (
                f"Dry-run passed for '{chip_id}': circuit translates cleanly to "
                f"Quafu QuantumCircuit. Qubits={circuit_qubits}, shots={shots}"
            ),
            backend_name=chip_id,
            circuit_qubits=circuit_qubits,
            supported_gates=tuple(sorted(self.SUPPORTED_GATES)),
        )
