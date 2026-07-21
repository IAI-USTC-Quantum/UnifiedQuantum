"""Quafu compatibility must stay lazy and warn only on explicit use."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def _run_isolated(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-W", "always::DeprecationWarning", "-c", textwrap.dedent(code)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_import_uniqc_does_not_load_or_warn_for_quafu() -> None:
    result = _run_isolated(
        """
        import sys
        import uniqc

        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" not in sys.modules
        """
    )
    assert result.returncode == 0, result.stderr
    assert "quafu_adapter is deprecated" not in result.stderr


def test_non_quafu_backend_discovery_does_not_load_or_warn_for_quafu() -> None:
    result = _run_isolated(
        """
        import sys
        import uniqc
        import uniqc.config
        from uniqc.backend_adapter.backend_registry import fetch_all_backends

        uniqc.list_backends()
        uniqc.get_backend("dummy", use_cache=False)
        uniqc.config.has_platform_credentials = lambda platform: platform == "quafu"
        fetch_all_backends()
        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" not in sys.modules
        """
    )
    assert result.returncode == 0, result.stderr
    assert "quafu_adapter is deprecated" not in result.stderr


def test_adapter_package_lazy_export_warns_on_explicit_quafu_import() -> None:
    result = _run_isolated(
        """
        import sys
        from uniqc.backend_adapter.task import adapters

        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" not in sys.modules
        assert adapters.QuafuAdapter.__name__ == "QuafuAdapter"
        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" in sys.modules
        """
    )
    assert result.returncode == 0, result.stderr
    assert "quafu_adapter is deprecated" in result.stderr
    assert "uniqc 0.1.0" in result.stderr


def test_public_quafu_compatibility_object_warns_when_instantiated() -> None:
    result = _run_isolated(
        """
        import sys
        import uniqc

        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" not in sys.modules
        uniqc.QuafuOptions()
        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" in sys.modules
        """
    )
    assert result.returncode == 0, result.stderr
    assert "quafu_adapter is deprecated" in result.stderr


def test_workflow_imports_do_not_load_quafu_adapter() -> None:
    result = _run_isolated(
        """
        import sys
        from uniqc.algorithms.workflows import readout_em_workflow, xeb_workflow

        assert readout_em_workflow is not None
        assert xeb_workflow is not None
        assert "uniqc.backend_adapter.task.adapters.quafu_adapter" not in sys.modules
        """
    )
    assert result.returncode == 0, result.stderr
    assert "quafu_adapter is deprecated" not in result.stderr


def test_non_quafu_cli_does_not_warn() -> None:
    for args in (["--help"], ["backend", "list", "--platform", "dummy"]):
        result = subprocess.run(
            [sys.executable, "-W", "always::DeprecationWarning", "-m", "uniqc.cli", *args],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "quafu_adapter is deprecated" not in result.stderr
