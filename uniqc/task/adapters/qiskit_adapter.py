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

from uniqc.task.adapters.base import (
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCESS,
    QuantumAdapter,
)
from uniqc.task.config import load_ibm_config
from uniqc.task.optional_deps import MissingDependencyError, check_qiskit

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

        from uniqc.originir import OriginIR_BaseParser

        parser = OriginIR_BaseParser()
        parser.parse(originir)
        qasm_str = parser.to_qasm()

        return qiskit.QuantumCircuit.from_qasm_str(qasm_str)

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit(
        self, circuit: qiskit.QuantumCircuit, *, shots: int = 1000, **kwargs: Any
    ) -> str:
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

    def submit_batch(
        self, circuits: list[qiskit.QuantumCircuit], *, shots: int = 1000, **kwargs: Any
    ) -> list[str]:
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
            raise ValueError(
                f"maximum shots number exceeded, should less than {max_shots}"
            )

        if circuit_optimize:
            circuits = qiskit.compiler.transpile(
                circuits, backend=backend, optimization_level=3
            )

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
            circuits = qiskit.compiler.transpile(
                circuits, backend=backend, optimization_level=1
            )

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
            "result": results,
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
                taskinfo["result"].extend(result_i.get("result", []))
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
                raise RuntimeError(
                    f"Failed to execute, errorinfo = {taskinfo.get('result')}"
                )

            # Retry on transient errors
            if retry > 0:
                retry -= 1
                time.sleep(interval)
            else:
                raise RuntimeError("Retry count exhausted.")
