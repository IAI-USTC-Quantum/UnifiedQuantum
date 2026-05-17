"""Tests for ``uniqc.gateway.api.backends`` via FastAPI ``TestClient``."""

from __future__ import annotations

import pytest

from uniqc.backend_adapter.backend_info import BackendInfo, Platform, QubitTopology


@pytest.fixture
def fake_caches(monkeypatch):
    """Provide deterministic cached backends + chip metadata."""
    backends_by_plat: dict[Platform, list[BackendInfo]] = {
        Platform.ORIGINQ: [
            BackendInfo(
                platform=Platform.ORIGINQ,
                name="wuyuan",
                description="WK-C72",
                num_qubits=72,
                topology=(QubitTopology(0, 1), QubitTopology(1, 2)),
                status="available",
                is_hardware=True,
                avg_1q_fidelity=0.998,
                avg_2q_fidelity=0.985,
            ),
        ],
        Platform.IBM: [
            BackendInfo(
                platform=Platform.IBM,
                name="ibm_torino",
                num_qubits=133,
                status="online",
                is_hardware=True,
            ),
        ],
        Platform.QUAFU: [],
        Platform.QUARK: [],
    }

    def _get_cached(platform: Platform):
        return backends_by_plat.get(platform, [])

    def _is_stale(platform_str: str):
        return False

    monkeypatch.setattr("uniqc.gateway.api.backends.get_cached_backends", _get_cached)
    monkeypatch.setattr("uniqc.gateway.api.backends.is_stale", _is_stale)
    monkeypatch.setattr("uniqc.gateway.api.backends.chip_cache_info", lambda: {})
    return backends_by_plat


def test_list_backends_returns_all_platforms(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends")
    assert r.status_code == 200
    payload = r.json()
    # Every Platform enum value is a key
    for plat in Platform:
        assert plat.value in payload


def test_list_backends_includes_originq(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends")
    payload = r.json()
    names = [b["name"] for b in payload["originq"]]
    assert "wuyuan" in names


def test_live_backends_flat_list(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends/live")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    names = {b["name"] for b in data}
    assert "wuyuan" in names
    assert "ibm_torino" in names
    for entry in data:
        assert "cache_stale" in entry


def test_get_backend_existing(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends/originq:wuyuan")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["name"] == "wuyuan"
    assert payload["cache_stale"] is False


def test_get_backend_not_found(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends/originq:bogus")
    assert r.status_code == 404


def test_get_backend_bad_id_format(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends/no-colon")
    assert r.status_code == 400


def test_get_backend_unknown_platform(fastapi_client, fake_caches):
    r = fastapi_client.get("/api/backends/wat:something")
    assert r.status_code == 400


def test_get_backend_dummy_lookup(fastapi_client, monkeypatch):
    from uniqc.backend_adapter.backend_info import BackendInfo, Platform

    fake = BackendInfo(
        platform=Platform.DUMMY,
        name="dummy:local:simulator",
        description="local sim",
        num_qubits=20,
        status="available",
        is_simulator=True,
        extra={"dummy_backend_id": "dummy:local:simulator"},
    )
    monkeypatch.setattr("uniqc.gateway.api.backends.list_dummy_backend_infos", lambda: [fake])
    monkeypatch.setattr("uniqc.gateway.api.backends.chip_cache_info", lambda: {})

    r = fastapi_client.get("/api/backends/dummy:local:simulator")
    assert r.status_code == 200, r.text
    assert r.json()["cache_stale"] is False


def test_get_backend_dummy_not_found(fastapi_client, monkeypatch):
    monkeypatch.setattr("uniqc.gateway.api.backends.list_dummy_backend_infos", lambda: [])
    monkeypatch.setattr("uniqc.gateway.api.backends.chip_cache_info", lambda: {})

    r = fastapi_client.get("/api/backends/dummy:ghost")
    assert r.status_code == 404


def test_refresh_backends_aggregates(fastapi_client, monkeypatch):
    calls: list[tuple[str, bool]] = []

    def _fetch(plat, force_refresh=False):
        calls.append((plat.value, force_refresh))
        if plat.value == "ibm":
            raise RuntimeError("ibm down")
        return ([], True) if plat.value == "quafu" else ([1, 2], True)

    monkeypatch.setattr("uniqc.gateway.api.backends.fetch_platform_backends", _fetch)

    r = fastapi_client.post("/api/backends/refresh")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "updated" in body
    assert any("ibm" in w for w in body["warnings"])


def test_refresh_backends_single_platform(fastapi_client, monkeypatch):
    monkeypatch.setattr(
        "uniqc.gateway.api.backends.fetch_platform_backends",
        lambda plat, force_refresh=False: ([1, 2, 3], True),
    )
    r = fastapi_client.post("/api/backends/refresh?platform=originq")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3


def test_refresh_backends_unknown_platform(fastapi_client):
    r = fastapi_client.post("/api/backends/refresh?platform=not-a-platform")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_health_endpoint(fastapi_client):
    r = fastapi_client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_endpoint(fastapi_client):
    r = fastapi_client.get("/api/version")
    assert r.status_code == 200
    payload = r.json()
    assert "version" in payload
    assert payload["github_url"].startswith("https://github.com/")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def test_fidelity_normalizer_handles_percent():
    from uniqc.gateway.api.backends import _fidelity

    assert _fidelity(0.98) == pytest.approx(0.98)
    assert _fidelity(98.0) == pytest.approx(0.98)
    assert _fidelity(None) is None
    assert _fidelity(-1) is None
    assert _fidelity(float("nan")) is None


def test_microseconds_normalizer_scales_seconds():
    from uniqc.gateway.api.backends import _microseconds

    assert _microseconds(42.0) == pytest.approx(42.0)
    # 5e-5 seconds → 50 µs
    assert _microseconds(5e-5) == pytest.approx(50)
    assert _microseconds(None) is None
    assert _microseconds(-1) is None
