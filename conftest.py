"""Pytest project-level configuration.

Honours these markers (declared in ``pytest.ini``):

* ``real_cloud_execution`` — skipped unless ``--real-cloud-test`` is passed.
* ``cloud`` — same gate as ``real_cloud_execution``.
* ``requires_pyqpanda3`` — skipped if pyqpanda3 is not installed.
* ``requires_qiskit`` — skipped if qiskit + qiskit_ibm_runtime are missing.
* ``requires_quafu`` — skipped if pyquafu is not installed.
* ``requires_pytorch`` — skipped if torch is missing.
* ``requires_torchquantum`` — skipped if torch or torchquantum is missing.
* ``requires_cpp`` — skipped if uniqc_cpp is missing.

Tests that use a ``dummy:<provider>:<chip>`` backend must declare the
appropriate provider ``requires_*`` marker themselves. That path requires the
provider SDK and a current chip cache even though it does not submit a cloud
job, and pytest cannot infer that dependency reliably from arbitrary test code.
"""

from __future__ import annotations

import importlib.util
import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--real-cloud-test",
        action="store_true",
        default=False,
        help="Run tests that submit real quantum circuits to cloud backends.",
    )


def _have(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _have_all(*names: str) -> bool:
    return all(_have(n) for n in names)


def _is_ci() -> bool:
    return any(os.environ.get(v) for v in ("CI", "GITHUB_ACTIONS", "JENKINS_HOME"))


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    run_real_cloud = config.getoption("--real-cloud-test")

    skips = {
        "real_cloud_execution": pytest.mark.skip(
            reason=(
                "submits real quantum circuits; pass --real-cloud-test "
                "(and configure the provider's API key) to run"
            )
        ),
        "cloud": pytest.mark.skip(
            reason=(
                "requires cloud credentials / network; pass --real-cloud-test"
            )
        ),
        "requires_pyqpanda3": pytest.mark.skip(
            reason=(
                "pyqpanda3 SDK is not installed; install with "
                "`pip install pyqpanda3>=0.3.5` or "
                "`pip install 'unified-quantum[originq]'`"
            )
        ),
        "requires_qiskit": pytest.mark.skip(
            reason=(
                "qiskit / qiskit_ibm_runtime not installed; install with "
                "`pip install unified-quantum`"
            )
        ),
        "requires_quafu": pytest.mark.skip(
            reason=(
                "pyquafu legacy SDK not installed; install with "
                "`pip install pyquafu` (deprecated; pulls numpy<2)"
            )
        ),
        "requires_pytorch": pytest.mark.skip(
            reason="torch not installed; install with `pip install torch`"
        ),
        "requires_torchquantum": pytest.mark.skip(
            reason=(
                "torch or torchquantum not installed; install with "
                "`pip install 'unified-quantum[pytorch]'`"
            )
        ),
        "requires_cpp": pytest.mark.skip(
            reason="uniqc_cpp C++ extension not built / installed",
        ),
    }
    available = {
        "requires_pyqpanda3": _have("pyqpanda3"),
        "requires_qiskit": _have_all("qiskit", "qiskit_ibm_runtime"),
        "requires_quafu": _have("quafu"),
        "requires_pytorch": _have("torch"),
        "requires_torchquantum": _have_all("torch", "torchquantum"),
        "requires_cpp": _have("uniqc_cpp"),
    }
    # Credential markers: skipped when the provider's API token isn't
    # configured (env or ~/.uniqc/config.yaml).
    try:
        from uniqc.backend_adapter.preflight import has_provider_credentials
    except Exception:
        def has_provider_credentials(_p: str) -> bool:  # type: ignore[no-redef]
            return False
    cred_markers = {
        "requires_originq_credentials": "originq",
        "requires_quafu_credentials": "quafu",
        "requires_quark_credentials": "quark",
        "requires_ibm_credentials": "ibm",
    }
    cred_skips = {
        marker: pytest.mark.skip(
            reason=(
                f"{provider} API credentials not configured. Run "
                f"`uniqc config set {provider}.token <TOKEN>` or set the "
                "env var to enable this test."
            )
        )
        for marker, provider in cred_markers.items()
    }
    cred_present = {
        marker: has_provider_credentials(provider)
        for marker, provider in cred_markers.items()
    }

    for item in items:
        kw = item.keywords
        if "real_cloud_execution" in kw and not run_real_cloud:
            item.add_marker(skips["real_cloud_execution"])
        if "cloud" in kw and not run_real_cloud:
            item.add_marker(skips["cloud"])
        for marker, present in available.items():
            if marker in kw and not present:
                item.add_marker(skips[marker])
        for marker, present in cred_present.items():
            if marker in kw and not present:
                item.add_marker(cred_skips[marker])
