"""Shared fixtures for ``uniqc.test.cli``.

Disables AI hints (which otherwise leak through every assertion) and forces
``_subcommand_given`` to behave correctly under ``typer.testing.CliRunner``,
where ``sys.argv`` is not rewritten by the runner.

These fixtures are opt-in via the ``cli`` mark to avoid clobbering the
pre-existing ``test_main_cli_fixes`` tests that intentionally exercise the
AI-hints config plumbing.
"""

from __future__ import annotations

import pytest

# Files that depend on the auto-stubs below. Anything else in uniqc/test/cli/
# keeps the original behaviour (real env / real sys.argv).
_AUTO_STUB_MODULES = {
    "test_backend_cli",
    "test_calibrate_cli",
    "test_chip_service_and_cache",
    "test_doctor_cli",
}


def _is_target_module(request) -> bool:
    return request.node.module.__name__.rsplit(".", 1)[-1] in _AUTO_STUB_MODULES


@pytest.fixture(autouse=True)
def _disable_ai_hints(request, monkeypatch):
    if not _is_target_module(request):
        return
    monkeypatch.delenv("UNIQC_AI_HINTS", raising=False)
    monkeypatch.setattr("uniqc.cli.output.config_ai_hints_enabled", lambda: False)


@pytest.fixture(autouse=True)
def _force_subcommand_detection(request, monkeypatch):
    if not _is_target_module(request):
        return
    monkeypatch.setattr("uniqc.cli.backend._subcommand_given", lambda: True)
