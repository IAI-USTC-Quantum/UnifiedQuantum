"""Qiskit backend adapter.

Translates OriginIR circuits to Qiskit QuantumCircuit objects and submits
via the ``qiskit`` / ``qiskit_ibm_runtime`` packages.  No raw REST calls.

Installation:
    pip install unified-quantum[qiskit]
"""

from __future__ import annotations

__all__ = ["QiskitAdapter"]

import time
from typing import TYPE_CHECKING, Any

from uniqc.backend_adapter.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    DryRunResult,
    QuantumAdapter,
)
from uniqc.backend_adapter.task.config import load_ibm_config
from uniqc.backend_adapter.task.optional_deps import MissingDependencyError, check_qiskit

if TYPE_CHECKING:
    import qiskit


class QiskitAdapter(QuantumAdapter):
    """Adapter for IBM Quantum backends via Qiskit.

    Proxy Configuration:
        Proxies can be passed via the `proxy` parameter:
        - Dict with 'http' and/or 'https' keys
        - Or a single proxy URL string for both protocols

    Raises:
        MissingDependencyError: If qiskit or qiskit_ibm_runtime is not installed.

    Example:
        >>> adapter = QiskitAdapter(proxy={
        ...     "http": "http://proxy.example.com:8080",
        ...     "https": "https://proxy.example.com:8080"
        ... })
    """

    name = "ibm"

    def __init__(self, proxy: dict[str, str] | str | None = None) -> None:
        """Initialize the Qiskit adapter.

        Args:
            proxy: Optional proxy configuration.
                - Dict with 'http' and/or 'https' keys
                - Or a single proxy URL string

        Raises:
            MissingDependencyError: If qiskit is not installed.
        """
        if not check_qiskit():
            raise MissingDependencyError("qiskit", "qiskit")

        config = load_ibm_config()
        self._api_token: str = config["api_token"]
        self._proxy: dict[str, str] | str | None = proxy

        from qiskit_ibm_runtime import QiskitRuntimeService

        if proxy:
            self._setup_proxy(proxy)

        self._service = QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=self._api_token,
        )

    def _setup_proxy(self, proxy: dict[str, str] | str) -> None:
        """Configure proxy settings for Qiskit/IBM provider.

        Args:
            proxy: Proxy configuration dict or URL string.
        """
        import os

        if isinstance(proxy, dict):
            https_proxy = proxy.get("https")
            http_proxy = proxy.get("http")
            proxy_url = https_proxy or http_proxy
        else:
            proxy_url = proxy

        if proxy_url:
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["http_proxy"] = proxy_url
            os.environ["https_proxy"] = proxy_url

    def is_available(self) -> bool:
        """Check if the Qiskit adapter is available (IBM service initialized)."""
        return check_qiskit() and hasattr(self, "_service") and self._service is not None

    # -------------------------------------------------------------------------
    # Circuit translation
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> qiskit.QuantumCircuit:
        """Translate an OriginIR string to a Qiskit QuantumCircuit.

        The conversion path is OriginIR → QASM string → Qiskit QuantumCircuit.
        """
        import qiskit

        from uniqc.compile.originir import OriginIR_BaseParser

        parser = OriginIR_BaseParser()
        parser.parse(originir)
        qasm_str = parser.to_qasm()

        return qiskit.QuantumCircuit.from_qasm_str(qasm_str)

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(self, circuit: qiskit.QuantumCircuit, *, shots: int = 1000, **kwargs: Any) -> str:
        """Submit a single circuit to IBM Quantum."""
        chip_id: str | None = kwargs.get("chip_id")
        auto_mapping: Any = kwargs.get("auto_mapping", False)
        circuit_optimize: bool = kwargs.get("circuit_optimize", True)
        task_name: str | None = kwargs.get("task_name")

        return self._submit_impl(
            circuits=[circuit],
            chip_id=chip_id,
            shots=shots,
            auto_mapping=auto_mapping,
            circuit_optimize=circuit_optimize,
            task_name=task_name,
        )

    def submit_batch(self, circuits: list[qiskit.QuantumCircuit], *, shots: int = 1000, **kwargs: Any) -> list[str]:
        """Submit multiple circuits as a batch.

        IBM executes all circuits in a single job, so this returns a single-element
        list containing that job's ID. The batch result is retrieved via that ID.

        Returns:
            list[str]: Single-element list with the IBM job ID.
        """
        chip_id: str | None = kwargs.get("chip_id")
        auto_mapping: Any = kwargs.get("auto_mapping", False)
        circuit_optimize: bool = kwargs.get("circuit_optimize", True)
        task_name: str | None = kwargs.get("task_name")

        job_id = self._submit_impl(
            circuits=circuits,
            chip_id=chip_id,
            shots=shots,
            auto_mapping=auto_mapping,
            circuit_optimize=circuit_optimize,
            task_name=task_name,
        )
        return [job_id]

    def _submit_impl(
        self,
        circuits: list[qiskit.QuantumCircuit],
        *,
        chip_id: str | None,
        shots: int,
        auto_mapping: Any,
        circuit_optimize: bool,
        task_name: str | None,
    ) -> str:
        """Internal implementation shared by submit() and submit_batch()."""
        import qiskit

        backends_name = [b.name for b in self._service.backends()]
        if chip_id not in backends_name:
            raise ValueError(f"no such chip, should be one of {backends_name}")

        backend = self._service.backend(chip_id)

        max_shots = backend.configuration().max_shots
        if shots > max_shots:
            raise ValueError(f"maximum shots number exceeded, should less than {max_shots}")

        if circuit_optimize:
            circuits = qiskit.compiler.transpile(circuits, backend=backend, optimization_level=3)

        if auto_mapping is True:
            circuits = qiskit.compiler.transpile(
                circuits,
                backend=backend,
                layout_method="sabre",
                optimization_level=1,
            )
        elif isinstance(auto_mapping, list):
            circuits = qiskit.compiler.transpile(
                circuits,
                backend=backend,
                initial_layout=auto_mapping,
                optimization_level=1,
            )
        else:
            circuits = qiskit.compiler.transpile(circuits, backend=backend, optimization_level=1)

        from qiskit_ibm_runtime import Sampler

        sampler = Sampler(mode=backend)
        job = sampler.run(circuits, shots=shots)
        return job.job_id()

    # -------------------------------------------------------------------------
    # Task query
    # -------------------------------------------------------------------------

    def query(self, taskid: str) -> dict[str, Any]:
        """Query a single IBM Quantum job's status."""
        job = self._service.job(taskid)
        status = job.status()

        status_name = status.name if hasattr(status, "name") else str(status)

        if status_name not in ("DONE", "COMPLETED"):
            return {"status": status_name, "value": status.value if hasattr(status, "value") else status_name}

        raw_result = job.result()
        results = []

        # Qiskit Runtime Sampler returns PrimitiveResult — iterate over pub results
        for pub_result in raw_result:
            data = pub_result.data
            # Each data field is a BitArray (one per measurement)
            counts: dict[str, int] = {}
            shots = None
            n_bits = None

            for field_name in dir(data):
                if field_name.startswith("_"):
                    continue
                bit_array = getattr(data, field_name)
                if hasattr(bit_array, "num_shots"):
                    shots = bit_array.num_shots
                    n_bits = bit_array.num_bits
                    arr = bit_array._array  # shape: (shots, 1) or (shots,)
                    arr = arr.flatten()
                    for val in arr:
                        val_int = int(val)
                        # Convert to bitstring: q[0] as most significant bit
                        bitstring = format(val_int, f"0{n_bits}b")
                        # Reverse so q[0] is first character (MSB convention)
                        bitstring = bitstring[::-1]
                        counts[bitstring] = counts.get(bitstring, 0) + 1
                    break

            if shots is None:
                counts = {}
            results.append(counts)

        return {
            "status": TASK_STATUS_SUCCESS,
            "result": results[0] if results else {},
            "time": job.creation_date.strftime("%a %d %b %Y, %I:%M%p") if hasattr(job, "creation_date") else "",
            "backend_name": job.backend().name if hasattr(job, "backend") else "",
        }

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        """Query multiple IBM Quantum jobs and merge results."""
        taskinfo: dict[str, Any] = {"status": TASK_STATUS_SUCCESS, "result": []}
        for taskid in taskids:
            result_i = self.query(taskid)
            status = result_i.get("status", "")
            if status in ("ERROR", "CANCELLED", "FAILED"):
                taskinfo["status"] = TASK_STATUS_FAILED
                break
            elif status in (
                "INITIALIZING",
                "QUEUED",
                "VALIDATING",
                "RUNNING",
                "EXECUTING",
            ):
                taskinfo["status"] = TASK_STATUS_RUNNING
            if taskinfo["status"] == TASK_STATUS_SUCCESS:
                taskinfo["result"].append(result_i.get("result", {}))
        return taskinfo

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
        """Poll task status until completion or timeout."""
        starttime = time.time()
        taskids = [taskid] if isinstance(taskid, str) else taskid

        while True:
            elapsed = time.time() - starttime
            if elapsed > timeout:
                raise TimeoutError("Reach the maximum timeout.")

            taskinfo = self.query_batch(taskids)

            if taskinfo["status"] == TASK_STATUS_RUNNING:
                time.sleep(interval)
                continue
            if taskinfo["status"] == TASK_STATUS_SUCCESS:
                return taskinfo["result"]
            if taskinfo["status"] == TASK_STATUS_FAILED:
                raise RuntimeError(f"Failed to execute, errorinfo = {taskinfo.get('result')}")

            # Retry on transient errors
            if retry > 0:
                retry -= 1
                time.sleep(interval)
            else:
                raise RuntimeError("Retry count exhausted.")

    # -------------------------------------------------------------------------
    # Dry-run validation
    # -------------------------------------------------------------------------

    def dry_run(self, originir: str, *, shots: int = 1000, **kwargs: Any) -> DryRunResult:
        """Dry-run validation for IBM Quantum backends.

        Validates offline by:
        1. Parsing OriginIR -> Qiskit QuantumCircuit.
        2. Checking chip_id is in available backends (local config lookup).
        3. Checking shots <= max_shots (local config lookup).
        4. Checking qubit count against backend limits.
        5. Attempting transpilation against the backend's basis_gates
           (purely local — catches unsupported gates).

        This method makes NO network calls. ``service.backend(chip_id)``
        and ``backend.configuration()`` are local config reads.

        Note:
            Any dry-run success followed by actual submission failure is a
            critical bug. Please report it at the UnifiedQuantum issue tracker.
        """
        import qiskit

        from uniqc.backend_adapter.task.adapters.base import _dry_run_failed, _dry_run_success

        chip_id: str | None = kwargs.get("chip_id")
        backend_name = chip_id or "simulator"

        # Step 1: Parse OriginIR -> Qiskit QuantumCircuit
        try:
            qiskit_circuit = self.translate_circuit(originir)
        except Exception as e:
            return _dry_run_failed(
                str(e),
                details=f"Failed to translate OriginIR to Qiskit QuantumCircuit: {e}",
                backend_name=backend_name,
            )

        circuit_qubits = qiskit_circuit.num_qubits

        # Step 2: Determine backend configuration (local — no network call)
        try:
            if chip_id:
                backend = self._service.backend(chip_id)
                backend_config = backend.configuration()
                max_shots = backend_config.max_shots
                basis_gates = backend_config.basis_gates
                num_qubits = backend_config.num_qubits
            else:
                # Fall back to generic simulator basis gates if no chip_id given
                max_shots = 100000
                basis_gates = [
                    "cx",
                    "u1",
                    "u2",
                    "u3",
                    "id",
                    "x",
                    "y",
                    "z",
                    "h",
                    "s",
                    "sdg",
                    "t",
                    "tdg",
                    "reset",
                ]
                num_qubits = 127
        except Exception as e:
            return _dry_run_failed(
                str(e),
                details=f"Failed to access backend configuration for '{chip_id}': {e}",
                backend_name=backend_name,
            )

        # Step 3: Shots limit check
        if shots > max_shots:
            return _dry_run_failed(
                f"shots ({shots}) exceeds backend maximum ({max_shots})",
                details=f"Shot count validation failed: {shots} > {max_shots}",
                backend_name=backend_name,
            )

        # Step 4: Qubit count check
        if circuit_qubits > num_qubits:
            return _dry_run_failed(
                f"circuit requires {circuit_qubits} qubits but backend '{chip_id}' has {num_qubits}",
                details=f"Qubit count validation failed: circuit={circuit_qubits}, backend={num_qubits}",
                backend_name=backend_name,
            )

        # Step 5: Transpile against basis_gates (fully offline)
        # This catches unsupported gates without needing a real backend.
        try:
            from qiskit.transpiler import CouplingMap

            coupling_map = CouplingMap.from_heavy_hex(num_qubits) if chip_id else None
            qiskit.compiler.transpile(
                qiskit_circuit,
                basis_gates=basis_gates,
                coupling_map=coupling_map,
                optimization_level=0,
            )
            transpile_warnings: tuple[str, ...] = ()
        except Exception as e:
            return _dry_run_failed(
                f"transpilation failed: {e}",
                details=(
                    f"Circuit uses gates not supported by '{chip_id or 'simulator'}' "
                    f"basis gates. Basis gates: {basis_gates}. "
                    f"Transpilation error: {e}"
                ),
                backend_name=backend_name,
            )

        return _dry_run_success(
            (
                f"Dry-run passed for '{chip_id or 'simulator'}': "
                f"circuit translates cleanly and transpiles to basis gates. "
                f"Qubits={circuit_qubits}, shots={shots}"
            ),
            backend_name=backend_name,
            circuit_qubits=circuit_qubits,
            warnings=transpile_warnings,
        )
