"""TianYan (天衍) backend adapter.

Submits QCIS circuits to the TianYan quantum cloud platform using cqlib.

Installation:
    pip install unified-quantum[tianyan]
"""

from __future__ import annotations

__all__ = ["TianyanAdapter"]

from typing import Any

from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
)
from uniqc.backend_adapter.task.optional_deps import check_cqlib, require

#: Default machine for direct adapter use when no ``machine_name`` is given.
#: ``tianyan_sw`` is a cloud simulator (free tier). ``submit_task`` users
#: normally pass ``backend='tianyan:<machine>'`` which overrides this.
_DEFAULT_MACHINE = "tianyan_sw"

#: Cloud simulator machine names reported by the platform.
TIANYAN_SIMULATOR_NAMES = frozenset(
    {
        "tianyan_sw",
        "tianyan_sa",
        "tianyan_s",
        "tianyan_tn",
        "tianyan_tnn",
    }
)


def _resolve_machine(kwargs: dict[str, Any], default: str) -> str:
    """Resolve the target machine from submit kwargs (canonical key first)."""
    for key in ("machine_name", "backend_name", "chip_id", "chip"):
        value = kwargs.get(key)
        if value:
            return str(value)
    return default


class TianyanAdapter(QuantumAdapter):
    """Adapter for the TianYan quantum cloud platform (天衍) using cqlib.

    Credentials are read from ``uniqc.config.load_tianyan_config()``
    (``tianyan.login_key``). Both the cqlib SDK import and the credential
    load are lazy so that importing this module never requires the SDK or
    a configured account.

    Note:
        The cqlib package is required for this adapter.
        Install with: pip install unified-quantum[tianyan]
    """

    name = "tianyan"
    # cqlib batch submission is limited; keep one platform job per circuit.
    max_native_batch_size: int = 1

    def __init__(self, machine_name: str | None = None) -> None:
        """Initialize the TianYan adapter.

        Args:
            machine_name: Default machine for submit() calls that don't
                specify one (e.g. ``"tianyan176"``). Defaults to the
                ``tianyan_sw`` cloud simulator.
        """
        self._default_machine = machine_name or _DEFAULT_MACHINE
        # One TianYanPlatform session per machine (get-or-create).
        self._platforms: dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # SDK / credential bootstrap (all lazy)
    # -------------------------------------------------------------------------

    def _load_login_key(self) -> str:
        """Load the TianYan login key from the uniqc config."""
        from uniqc.config import load_tianyan_config

        return load_tianyan_config()["login_key"]

    def _get_platform(self, machine_name: str | None = None) -> Any:
        """Return the cached ``TianYanPlatform`` for ``machine_name``."""
        name = machine_name or self._default_machine
        platform = self._platforms.get(name)
        if platform is None:
            require("cqlib", "tianyan")
            from cqlib import TianYanPlatform

            platform = TianYanPlatform(login_key=self._load_login_key(), machine_name=name)
            self._platforms[name] = platform
        return platform

    def is_available(self) -> bool:
        """Return True if cqlib is installed and a login_key is configured."""
        if not check_cqlib():
            return False
        try:
            self._load_login_key()
        except Exception:
            return False
        return True

    # -------------------------------------------------------------------------
    # Backend discovery
    # -------------------------------------------------------------------------

    def list_backends(self) -> list[dict[str, Any]]:
        """Return raw TianYan machine metadata.

        ``query_quantum_computer_list()`` returns rows of
        ``[id, price, status, name]`` (e.g.
        ``['1764555284795101186', 'free', 'running', 'tianyan176']``).
        Known simulator machines are appended when the API omits them.

        Returns:
            List of dicts with keys: ``name``, ``available``, ``status``,
            ``machine_id``, ``price``, ``is_simulator``, ``num_qubits``.
        """
        import re

        platform = self._get_platform()
        rows = platform.query_quantum_computer_list() or []
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            fields = list(row) + [None] * 4
            machine_id, price, status, name = fields[:4]
            name = str(name)
            available = str(status).strip().lower() == "running"
            is_sim = name in TIANYAN_SIMULATOR_NAMES
            digits = re.search(r"(\d+)$", name)
            results.append(
                {
                    "name": name,
                    "available": available,
                    "status": str(status),
                    "machine_id": str(machine_id),
                    "price": price,
                    "is_simulator": is_sim,
                    "num_qubits": int(digits.group(1)) if (digits and not is_sim) else 0,
                }
            )
            seen.add(name)
        for sim_name in sorted(TIANYAN_SIMULATOR_NAMES - seen):
            results.append(
                {
                    "name": sim_name,
                    "available": True,
                    "status": "running",
                    "machine_id": "",
                    "price": "free",
                    "is_simulator": True,
                    "num_qubits": 0,
                }
            )
        return results

    # -------------------------------------------------------------------------
    # Chip characterization
    # -------------------------------------------------------------------------

    def get_chip_characterization(self, chip_name: str):
        """Return per-qubit and per-pair calibration data for a TianYan machine.

        Uses cqlib's authenticated ``download_config`` endpoint. (The
        unauthenticated ``get_machine_config``/gplot endpoint sits behind a
        web-application firewall and is not usable from SDK clients.)

        Parameters
        ----------
        chip_name:
            TianYan machine name, e.g. ``"tianyan176"``.

        Returns
        -------
        ChipCharacterization or None
            None when cqlib is unavailable or the machine config cannot be
            downloaded.
        """
        from uniqc.backend_adapter.backend_info import Platform, QubitTopology
        from uniqc.cli.chip_info import (
            ChipCharacterization,
            ChipGlobalInfo,
            SingleQubitData,
            TwoQubitData,
            TwoQubitGateData,
        )

        try:
            conf = self._get_platform(chip_name).download_config(machine=chip_name)
        except Exception:
            return None
        if not isinstance(conf, dict) or not isinstance(conf.get("overview"), dict):
            return None

        overview = conf["overview"]

        def _qidx(label: Any) -> int | None:
            text = str(label).strip()
            return int(text[1:]) if text.startswith("Q") and text[1:].isdigit() else None

        def _metric_map(node: Any) -> dict[str, float]:
            """Align a ``{qubit_used, param_list}`` section into a label->value map."""
            if not isinstance(node, dict):
                return {}
            used = node.get("qubit_used") or []
            values = node.get("param_list") or []
            out: dict[str, float] = {}
            for label, value in zip(used, values, strict=False):
                try:
                    out[str(label)] = float(value)
                except (TypeError, ValueError):
                    continue
            return out

        def _pct_to_fidelity(pct: float | None) -> float | None:
            return (1.0 - pct / 100.0) if pct is not None else None

        disabled_q = {q.strip() for q in str(conf.get("disabledQubits") or "").split(",") if q.strip()}
        disabled_c = {c.strip() for c in str(conf.get("disabledCouplers") or "").split(",") if c.strip()}

        all_qubits = sorted(i for i in (_qidx(q) for q in overview.get("qubits") or []) if i is not None)
        available = tuple(i for i in all_qubits if f"Q{i}" not in disabled_q)

        # coupler_map: {"G0": ["Q6", "Q0"], ...}; drop disabled couplers and
        # edges touching disabled qubits.
        edges: dict[tuple[int, int], str] = {}
        for cid, pair in (overview.get("coupler_map") or {}).items():
            if cid in disabled_c or not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            u, v = _qidx(pair[0]), _qidx(pair[1])
            if u is None or v is None or u == v or f"Q{u}" in disabled_q or f"Q{v}" in disabled_q:
                continue
            edges[tuple(sorted((u, v)))] = str(cid)

        qubit_section = conf.get("qubit") or {}
        t1_map = _metric_map((qubit_section.get("relatime") or {}).get("T1"))
        t2_map = _metric_map((qubit_section.get("relatime") or {}).get("T2"))
        sq_err = _metric_map((qubit_section.get("singleQubit") or {}).get("gate error"))
        ro_err = _metric_map(((conf.get("readout") or {}).get("readoutArray") or {}).get("Readout Error"))
        cz_err = _metric_map(((conf.get("twoQubitGate") or {}).get("czGate") or {}).get("gate error"))

        single_qubit_data = tuple(
            SingleQubitData(
                qubit_id=i,
                t1=t1_map.get(f"Q{i}"),
                t2=t2_map.get(f"Q{i}"),
                single_gate_fidelity=_pct_to_fidelity(sq_err.get(f"Q{i}")),
                avg_readout_fidelity=_pct_to_fidelity(ro_err.get(f"Q{i}")),
            )
            for i in available
        )
        two_qubit_data = tuple(
            TwoQubitData(
                qubit_u=u,
                qubit_v=v,
                gates=(TwoQubitGateData(gate="cz", fidelity=_pct_to_fidelity(cz_err.get(cid))),),
            )
            for (u, v), cid in sorted(edges.items())
        )

        return ChipCharacterization(
            platform=Platform.TIANYAN,
            chip_name=chip_name,
            full_id=f"tianyan:{chip_name}",
            available_qubits=available,
            connectivity=tuple(QubitTopology(u=u, v=v) for u, v in sorted(edges)),
            single_qubit_data=single_qubit_data,
            two_qubit_data=two_qubit_data,
            global_info=ChipGlobalInfo(single_qubit_gates=("sx", "rz"), two_qubit_gates=("cz",)),
            calibrated_at=conf.get("calibrationTime"),
        )

    # -------------------------------------------------------------------------
    # Circuit translation (OriginIR to QCIS)
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> str:
        """Convert an OriginIR string to QCIS text (purely local).

        Args:
            originir: OriginIR format circuit string.

        Returns:
            QCIS text for ``TianYanPlatform.submit_job``.
        """
        from uniqc.backend_adapter.circuit_adapter import originir_to_qcis

        return originir_to_qcis(originir)

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(self, circuit: str, *, shots: int = 1000, **kwargs: Any) -> str:
        """Submit a single circuit to TianYan.

        Args:
            circuit: QCIS text (as produced by
                :class:`~uniqc.backend_adapter.circuit_adapter.TianyanCircuitAdapter`).
                OriginIR input (detected by its ``QINIT`` header) is
                translated first for convenience.
            shots: Number of measurement shots.
            **kwargs: Additional options:
                - machine_name: Target machine (e.g. ``"tianyan176"``)
                - task_name / exp_name: Optional experiment name
                - lab_id: Optional lab id passed through to cqlib

        Returns:
            cqlib query_id string.
        """
        machine_name = _resolve_machine(kwargs, self._default_machine)
        platform = self._get_platform(machine_name)

        qcis = str(circuit) if "QINIT" not in str(circuit) else self.translate_circuit(str(circuit))

        query_ids = platform.submit_job(
            circuit=qcis,
            exp_name=kwargs.get("task_name") or kwargs.get("exp_name") or "",
            num_shots=int(shots),
            lab_id=kwargs.get("lab_id"),
        )
        # cqlib returns a *list* of query ids (one per submitted circuit) and
        # this adapter submits exactly one circuit per job, so unwrap the
        # single element. A falsy return (0) means the platform rejected the
        # submission.
        if not query_ids:
            raise RuntimeError(
                f"TianYan rejected the submission for machine '{machine_name}' (submit_job returned {query_ids!r})."
            )
        if isinstance(query_ids, (list, tuple)):
            if len(query_ids) != 1:
                raise RuntimeError(f"Expected exactly one TianYan query id, got {len(query_ids)}: {query_ids!r}")
            return str(query_ids[0])
        return str(query_ids)

    def submit_batch(self, circuits: list[str], *, shots: int = 1000, **kwargs: Any) -> list[str]:
        """Submit circuits one by one (one query_id per circuit).

        cqlib's batch interface is limited, so uniqc slices batches into
        per-circuit jobs (``max_native_batch_size == 1``).
        """
        return [self.submit(circuit, shots=shots, **kwargs) for circuit in circuits]

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    @staticmethod
    def _query_experiment_entry(platform: Any, query_id: str) -> dict[str, Any] | None:
        """Non-blocking status query via cqlib's private request helper.

        cqlib's public ``query_experiment`` blocks until completion, so we
        call the underlying REST endpoint directly — the same one
        ``query_experiment`` itself polls. ``TianYanPlatform._send_request``
        and ``QUERY_EXP_PATH`` are *private* cqlib APIs; they are
        encapsulated in this single method so a future public non-blocking
        API only requires changing this one place.

        Returns the matching entry of ``data.experimentResultModelList``,
        or ``None`` when the response carries no result for ``query_id``
        yet (still queued / running).
        """
        resp = platform._send_request(
            path=platform.QUERY_EXP_PATH,
            data={"query_ids": [query_id]},
            method="POST",
        )
        if not isinstance(resp, dict):
            return None
        data = resp.get("data")
        if not isinstance(data, dict):
            return None
        entries = data.get("experimentResultModelList")
        if not entries:
            return None
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("experimentTaskId", "")) == str(query_id):
                return entry
        # Defensive: some responses omit the task id on a single-entry list.
        if len(entries) == 1 and isinstance(entries[0], dict) and "experimentTaskId" not in entries[0]:
            return entries[0]
        return None

    def query(self, taskid: str) -> dict[str, Any]:
        """Query a single task's status (non-blocking).

        Args:
            taskid: cqlib query_id.

        Returns:
            dict with keys: taskid, status, result (counts dict when
            status is ``'success'``, error payload when ``'failed'``).
        """
        platform = self._get_platform()
        entry = self._query_experiment_entry(platform, taskid)
        if entry is None:
            return {"taskid": taskid, "status": TASK_STATUS_RUNNING}

        result_status = entry.get("resultStatus")
        if result_status:
            from uniqc.backend_adapter.task.normalizers import tianyan_result_status_to_counts

            return {
                "taskid": taskid,
                "status": TASK_STATUS_SUCCESS,
                "result": tianyan_result_status_to_counts(result_status),
            }

        # Entry exists but carries no shot data yet: only an explicit
        # failure marker flips the task to failed; anything else is still
        # running (defensive — an empty/partial response is not an error).
        status_text = str(entry.get("status") or entry.get("taskStatus") or "").strip().lower()
        if status_text in ("failed", "failure", "error", "cancelled", "canceled"):
            error_msg = entry.get("errorMessage") or entry.get("errorMsg") or entry.get("message")
            return {
                "taskid": taskid,
                "status": TASK_STATUS_FAILED,
                "result": {"error": str(error_msg or f"Task failed on TianYan (status={status_text})")},
            }
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
        """Dry-run validation for TianYan backends.

        Validates offline: OriginIR parses, all gates map to QCIS, and
        qubit indices fit the ``QINIT`` size. Makes NO network calls and
        does not require cqlib or credentials.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        from uniqc.backend_adapter.circuit_adapter import TianyanCircuitAdapter, originir_to_qcis
        from uniqc.backend_adapter.task.adapters.base import _dry_run_failed, _dry_run_success

        machine_name = _resolve_machine(kwargs, self._default_machine)

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

        try:
            originir_to_qcis(originir)
        except Exception as e:
            return _dry_run_failed(
                str(e),
                details=(
                    f"OriginIR to QCIS translation failed for machine '{machine_name}': {e}. "
                    "The circuit may use gates not supported by TianYan."
                ),
                backend_name=machine_name,
            )

        warnings: list[str] = []
        if shots <= 0:
            return _dry_run_failed(
                "shots must be positive",
                details=f"Invalid shots value for TianYan: {shots}",
                backend_name=machine_name,
            )
        warnings.append(
            f"Machine '{machine_name}' existence/availability is not verified during dry-run "
            "(offline); it is checked at submission time."
        )

        return _dry_run_success(
            (
                f"Dry-run passed for '{machine_name}': OriginIR translates cleanly "
                f"to QCIS. Qubits={circuit_qubits}, shots={shots}"
            ),
            backend_name=machine_name,
            circuit_qubits=circuit_qubits,
            supported_gates=tuple(sorted(TianyanCircuitAdapter.SUPPORTED_GATES)),
            warnings=tuple(warnings),
        )
