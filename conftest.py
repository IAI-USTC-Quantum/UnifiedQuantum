"""Pytest project-level configuration."""

from __future__ import annotations

import importlib.util

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--real-cloud-test",
        action="store_true",
        default=False,
        help="Run tests that submit real quantum circuits to cloud backends.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_real_cloud = config.getoption("--real-cloud-test")
    skip_real_execution = pytest.mark.skip(
        reason="submits real quantum circuits; pass --real-cloud-test to run"
    )
    skip_quafu = pytest.mark.skip(
        reason="pyquafu legacy extra is not installed; install unified-quantum[quafu] to run"
    )

    quafu_available = importlib.util.find_spec("quafu") is not None
    for item in items:
        if "real_cloud_execution" in item.keywords and not run_real_cloud:
            item.add_marker(skip_real_execution)
        if "requires_quafu" in item.keywords and not quafu_available:
            item.add_marker(skip_quafu)
