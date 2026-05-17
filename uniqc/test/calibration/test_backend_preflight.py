"""Tests for the backend-preflight gate."""

from __future__ import annotations

from unittest import mock

import pytest

from uniqc.backend_adapter.preflight import (
    BackendPreflightError,
    MissingDependencyError,
    ensure_backend_ready,
    parse_backend_target,
)

# ---------------------------------------------------------------------------
# Identifier parsing
# ---------------------------------------------------------------------------


class TestParseBackendTarget:
    def test_local_aliases(self):
        for alias in (
            "local",
            "local:simulator",
            "dummy:local:simulator",
        ):
            t = parse_backend_target(alias)
            assert t.kind == "local"
            assert t.provider is None
            assert t.chip_name is None
            assert not t.needs_provider_sdk

    def test_bare_dummy_rejected(self):
        for alias in ("dummy", "dummy:local"):
            with pytest.raises(ValueError, match="not allowed"):
                parse_backend_target(alias)

    def test_local_topology(self):
        t = parse_backend_target("dummy:local:virtual-line-5")
        assert t.kind == "local_topology"
        assert t.topology_spec == "virtual-line-5"

    def test_local_topology_legacy_rejected(self):
        # Legacy 'dummy:virtual-line-N' (no :local:) is now rejected
        # with a hint pointing at the canonical form.
        with pytest.raises(ValueError, match="dummy:local:virtual-line-5"):
            parse_backend_target("dummy:virtual-line-5")

    def test_local_mps(self):
        t = parse_backend_target("dummy:local:mps-linear-8:chi=16")
        assert t.kind == "local_mps"
        assert "mps-linear-8" in t.topology_spec

    def test_legacy_mps_colon_rejected(self):
        # 'mps:linear-N' (colon) is the old form; should be rejected with hint.
        with pytest.raises(ValueError, match="mps-linear-8"):
            parse_backend_target("dummy:local:mps:linear-8")
        with pytest.raises(ValueError, match="dummy:local:mps-linear-8"):
            parse_backend_target("dummy:mps:linear-8")

    def test_dummy_provider(self):
        t = parse_backend_target("dummy:originq:WK_C180")
        assert t.kind == "dummy_provider"
        assert t.provider == "originq"
        assert t.chip_name == "WK_C180"
        assert t.needs_provider_sdk

    def test_provider_only(self):
        t = parse_backend_target("originq")
        assert t.kind == "provider"
        assert t.provider == "originq"
        assert t.chip_name is None

    def test_provider_with_chip(self):
        t = parse_backend_target("originq:WK_C180")
        assert t.kind == "provider"
        assert t.provider == "originq"
        assert t.chip_name == "WK_C180"

    def test_empty_or_invalid(self):
        with pytest.raises(ValueError):
            parse_backend_target("")
        with pytest.raises(ValueError):
            parse_backend_target("dummy:local:nonsense-5")
        with pytest.raises(ValueError):
            parse_backend_target("dummy:originq")  # missing chip


# ---------------------------------------------------------------------------
# ensure_backend_ready
# ---------------------------------------------------------------------------


class TestEnsureBackendReady:
    def test_local_passes_when_uniqc_cpp_present(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: True,
        )
        assert ensure_backend_ready("local") is None
        assert ensure_backend_ready("dummy:local:simulator") is None

    def test_local_raises_when_uniqc_cpp_missing(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: False,
        )
        with pytest.raises(MissingDependencyError, match="uniqc_cpp"):
            ensure_backend_ready("local")

    def test_dummy_provider_raises_without_sdk(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_pyqpanda3",
            lambda: False,
        )
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: True,
        )
        with pytest.raises(MissingDependencyError) as excinfo:
            ensure_backend_ready("dummy:originq:WK_C180")
        # Install hint must mention pyqpanda3.
        assert "pyqpanda3" in str(excinfo.value)

    def test_provider_raises_without_sdk(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_pyqpanda3",
            lambda: False,
        )
        with pytest.raises(MissingDependencyError):
            ensure_backend_ready("originq:WK_C180")

    def test_unknown_provider_raises(self, monkeypatch):
        with pytest.raises(BackendPreflightError, match="Unknown provider"):
            ensure_backend_ready("madeupcloud:cool_chip")

    def test_dummy_provider_returns_cached_chip(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_pyqpanda3",
            lambda: True,
        )
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: True,
        )
        sentinel = mock.Mock(spec=[], chip_name="WK_C180")
        with (
            mock.patch(
                "uniqc.backend_adapter.preflight._load_chip_cache",
                return_value=(sentinel, mock.Mock(exists=lambda: True)),
            ),
            mock.patch(
                "uniqc.backend_adapter.preflight._chip_age_hours",
                return_value=0.5,
            ),
        ):
            result = ensure_backend_ready(
                "dummy:originq:WK_C180",
                max_age_hours=24.0,
            )
        assert result is sentinel

    def test_refresh_attempt_propagates_provider_error(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_pyqpanda3",
            lambda: True,
        )
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: True,
        )
        # Cache miss → refresh attempt → simulated provider error.
        with (
            mock.patch(
                "uniqc.backend_adapter.preflight._load_chip_cache",
                return_value=(None, mock.Mock(exists=lambda: False)),
            ),
            mock.patch(
                "uniqc.backend_adapter.preflight._refresh_chip",
                side_effect=BackendPreflightError("simulated provider failure"),
            ),
            pytest.raises(BackendPreflightError, match="simulated"),
        ):
            ensure_backend_ready("dummy:originq:WK_C180")

    def test_refresh_disabled_raises_when_cache_missing(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_pyqpanda3",
            lambda: True,
        )
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: True,
        )
        with (
            mock.patch(
                "uniqc.backend_adapter.preflight._load_chip_cache",
                return_value=(None, mock.Mock(exists=lambda: False)),
            ),
            pytest.raises(BackendPreflightError, match="missing"),
        ):
            ensure_backend_ready(
                "dummy:originq:WK_C180",
                refresh=False,
            )

    def test_stale_cache_triggers_refresh(self, monkeypatch):
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_pyqpanda3",
            lambda: True,
        )
        monkeypatch.setattr(
            "uniqc.backend_adapter.preflight.check_uniqc_cpp",
            lambda: True,
        )
        sentinel_old = mock.Mock(spec=[], chip_name="WK_C180")
        sentinel_new = mock.Mock(spec=[], chip_name="WK_C180")
        with (
            mock.patch(
                "uniqc.backend_adapter.preflight._load_chip_cache",
                return_value=(sentinel_old, mock.Mock(exists=lambda: True)),
            ),
            mock.patch(
                "uniqc.backend_adapter.preflight._chip_age_hours",
                return_value=999.0,
            ),
            mock.patch(
                "uniqc.backend_adapter.preflight._refresh_chip",
                return_value=sentinel_new,
            ) as ref,
        ):
            result = ensure_backend_ready(
                "dummy:originq:WK_C180",
                max_age_hours=24.0,
            )
        assert result is sentinel_new
        ref.assert_called_once()
