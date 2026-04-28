"""IBM Quantum backend adapter using QiskitRuntimeService.

Uses ``QiskitRuntimeService`` from ``qiskit-ibm-runtime`` to list backends
and submit/query tasks.  This is the recommended IBM approach as of 2024+,
superseding the raw REST API which is blocked by Cloudflare on quantum.ibm.com.

QiskitRuntimeService reference:
    https://docs.quantum.ibm.com/qiskit-ibm-runtime
"""

from __future__ import annotations

import os
import warnings
from typing import Any

from uniqc.task.adapters.base import (
    QuantumAdapter,
)
from uniqc.task.config import load_ibm_config


class IBMAdapter(QuantumAdapter):
    """Adapter for IBM Quantum using QiskitRuntimeService.

    This adapter sets up proxy environment variables from the IBM config
    before initialising ``QiskitRuntimeService``, which internally handles
    IAM authentication and Cloudflare-protected endpoints.
    """

    name = "ibm"

    def __init__(self, proxy: dict[str, str] | str | None = None) -> None:
        # Sync YAML tokens → env vars so load_ibm_config() finds IBM_TOKEN.
        from uniqc.config import sync_tokens_to_env
        sync_tokens_to_env()
        config = load_ibm_config()
        self._token: str = config["api_token"]
        self._proxy: dict[str, str] | str | None = proxy
        self._service: Any = None  # lazily initialised

    # -------------------------------------------------------------------------
    # Proxy setup
    # -------------------------------------------------------------------------

    def _apply_proxy(self) -> list[str]:
        """Set HTTP_PROXY/HTTPS_PROXY env vars and return list of set keys."""
        env_keys: list[str] = []
        if self._proxy is None:
            return env_keys
        if isinstance(self._proxy, str):
            proxy_url = self._proxy
        elif self._proxy:
            proxy_url = self._proxy.get("https") or self._proxy.get("http", "")
        else:
            proxy_url = ""
        if proxy_url:
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            env_keys = ["HTTP_PROXY", "HTTPS_PROXY"]
        return env_keys

    def _remove_proxy(self, env_keys: list[str]) -> None:
        """Remove proxy env vars that we set ourselves."""
        for key in env_keys:
            os.environ.pop(key, None)

    # -------------------------------------------------------------------------
    # Lazy service initialisation
    # -------------------------------------------------------------------------

    def _get_service(self) -> Any:
        """Return a cached QiskitRuntimeService instance, initialising if needed."""
        if self._service is not None:
            return self._service

        env_keys = self._apply_proxy()
        try:
            # Suppress the samplomatic numpy compat warning — it doesn't affect functionality.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*samplomatic.*",
                    category=UserWarning,
                )
                from qiskit_ibm_runtime import QiskitRuntimeService
            self._service = QiskitRuntimeService(token=self._token)
        finally:
            self._remove_proxy(env_keys)

        return self._service

    # -------------------------------------------------------------------------
    # Availability
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the IBM Quantum account is accessible."""
        try:
            self._get_service().backends()
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Backend listing
    # -------------------------------------------------------------------------

    def list_backends(self) -> list[dict[str, Any]]:
        """Return raw IBM Quantum backend metadata via QiskitRuntimeService.

        Returns:
            List of dicts with keys: ``name``, ``num_qubits``, ``status``,
            ``simulator``, ``description``, and others from the API response.
        """
        service = self._get_service()
        raw_backends: list[dict[str, Any]] = []
        for b in service.backends():
            # Determine canonical status string
            try:
                status = "available" if b.status().operational else "unavailable"
            except Exception:
                status = "unknown"

            # processor_type can be a dict or string depending on backend
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

            # online_date if available
            try:
                od = b.online_date
                if od:
                    entry["online_date"] = str(od)
            except Exception:
                pass

            raw_backends.append(entry)

        return raw_backends

    # -------------------------------------------------------------------------
    # Circuit translation (not implemented)
    # -------------------------------------------------------------------------

    def translate_circuit(self, originir: str) -> Any:
        raise NotImplementedError(
            "IBMAdapter.translate_circuit is not yet implemented. "
            "Use the QiskitAdapter from qiskit_ibm_provider for circuit "
            "translation and task execution."
        )

    # -------------------------------------------------------------------------
    # Task submission (not implemented)
    # -------------------------------------------------------------------------

    def submit(self, circuit: Any, *, shots: int = 1000, **kwargs: Any) -> str:
        raise NotImplementedError(
            "IBMAdapter.submit is not yet implemented. "
            "Use the QiskitAdapter for task submission."
        )

    def submit_batch(
        self, circuits: list[Any], *, shots: int = 1000, **kwargs: Any
    ) -> list[str]:
        raise NotImplementedError(
            "IBMAdapter.submit_batch is not yet implemented. "
            "Use the QiskitAdapter for batch submission."
        )

    def query(self, taskid: str) -> dict[str, Any]:
        raise NotImplementedError(
            "IBMAdapter.query is not yet implemented. "
            "Use the QiskitAdapter for task queries."
        )

    def query_batch(self, taskids: list[str]) -> dict[str, Any]:
        raise NotImplementedError(
            "IBMAdapter.query_batch is not yet implemented. "
            "Use the QiskitAdapter for batch queries."
        )
