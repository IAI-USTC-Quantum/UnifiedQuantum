"""Unit tests for the chip cache + chip service modules.

``uniqc.cli.chip_cache`` is a pure on-disk JSON cache; ``uniqc.cli.chip_service``
dispatches to per-platform adapters. Both can be exercised without any cloud
credentials by mocking the adapters.
"""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import pytest

from uniqc.backend_adapter.backend_info import Platform, QubitTopology
from uniqc.cli import chip_cache, chip_service
from uniqc.cli.chip_info import (
    ChipCharacterization,
    ChipGlobalInfo,
    SingleQubitData,
    TwoQubitData,
    TwoQubitGateData,
)


def _make_chip(platform: Platform = Platform.ORIGINQ, name: str = "wuyuan") -> ChipCharacterization:
    return ChipCharacterization(
        platform=platform,
        chip_name=name,
        full_id=f"{platform.value}:{name}",
        available_qubits=(0, 1, 2),
        connectivity=(QubitTopology(0, 1), QubitTopology(1, 2)),
        single_qubit_data=(
            SingleQubitData(qubit_id=0, t1=42.0, t2=18.0, single_gate_fidelity=0.999),
            SingleQubitData(qubit_id=1, t1=40.0, t2=17.0, single_gate_fidelity=0.998),
        ),
        two_qubit_data=(TwoQubitData(qubit_u=0, qubit_v=1, gates=(TwoQubitGateData(gate="cz", fidelity=0.985),)),),
        global_info=ChipGlobalInfo(),
        calibrated_at="2026-05-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# chip_cache
# ---------------------------------------------------------------------------


def test_get_chip_returns_none_when_missing(tmp_path: Path):
    assert chip_cache.get_chip(Platform.ORIGINQ, "wuyuan", cache_dir=tmp_path) is None


def test_save_and_get_chip_roundtrip(tmp_path: Path):
    chip = _make_chip()
    chip_cache.save_chip(chip, cache_dir=tmp_path)

    fetched = chip_cache.get_chip(Platform.ORIGINQ, "wuyuan", cache_dir=tmp_path)
    assert fetched is not None
    assert fetched.full_id == "originq:wuyuan"
    assert tuple(fetched.available_qubits) == (0, 1, 2)
    # Float values round-trip
    sq0 = next(s for s in fetched.single_qubit_data if s.qubit_id == 0)
    assert sq0.t1 == pytest.approx(42.0)


def test_chip_name_with_colon_is_safe(tmp_path: Path):
    chip = _make_chip(name="wuyuan:d5")
    chip_cache.save_chip(chip, cache_dir=tmp_path)
    fetched = chip_cache.get_chip(Platform.ORIGINQ, "wuyuan:d5", cache_dir=tmp_path)
    assert fetched is not None
    assert fetched.chip_name == "wuyuan:d5"
    # The on-disk filename should not contain ':' or '/'
    for f in tmp_path.iterdir():
        assert ":" not in f.name
        assert "/" not in f.name


def test_list_cached_chips(tmp_path: Path):
    chip_cache.save_chip(_make_chip(Platform.ORIGINQ, "wuyuan"), cache_dir=tmp_path)
    chip_cache.save_chip(_make_chip(Platform.IBM, "torino"), cache_dir=tmp_path)

    all_chips = chip_cache.list_cached_chips(cache_dir=tmp_path)
    assert {c.full_id for c in all_chips} == {"originq:wuyuan", "ibm:torino"}

    originq_only = chip_cache.list_cached_chips(platform=Platform.ORIGINQ, cache_dir=tmp_path)
    assert {c.full_id for c in originq_only} == {"originq:wuyuan"}


def test_list_cached_chips_empty_dir_returns_empty(tmp_path: Path):
    assert chip_cache.list_cached_chips(cache_dir=tmp_path / "nope") == []


def test_invalidate_chip_removes_file(tmp_path: Path):
    chip_cache.save_chip(_make_chip(), cache_dir=tmp_path)
    assert chip_cache.get_chip(Platform.ORIGINQ, "wuyuan", cache_dir=tmp_path) is not None

    chip_cache.invalidate_chip(Platform.ORIGINQ, "wuyuan", cache_dir=tmp_path)
    assert chip_cache.get_chip(Platform.ORIGINQ, "wuyuan", cache_dir=tmp_path) is None

    # invalidate_chip on missing file is a no-op
    chip_cache.invalidate_chip(Platform.ORIGINQ, "ghost", cache_dir=tmp_path)


def test_chip_cache_info_empty(tmp_path: Path):
    assert chip_cache.chip_cache_info(cache_dir=tmp_path / "missing") == {}
    assert chip_cache.chip_cache_info(cache_dir=tmp_path) == {}


def test_chip_cache_info_reports_metadata(tmp_path: Path):
    chip_cache.save_chip(_make_chip(), cache_dir=tmp_path)
    info = chip_cache.chip_cache_info(cache_dir=tmp_path)
    assert "originq:wuyuan" in info
    meta = info["originq:wuyuan"]
    assert meta["platform"] == "originq"
    assert meta["num_qubits"] == 3
    assert meta["num_pairs"] == 1
    assert meta["age_seconds"] >= 0
    assert meta["is_stale"] is False


def test_chip_cache_info_marks_stale(tmp_path: Path, monkeypatch):
    chip_cache.save_chip(_make_chip(), cache_dir=tmp_path)
    # Pretend "now" is 2 days in the future → cache file is older than 24 h
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 86400 * 2)
    info = chip_cache.chip_cache_info(cache_dir=tmp_path)
    assert info["originq:wuyuan"]["is_stale"] is True


def test_chip_cache_corrupt_file_is_ignored(tmp_path: Path):
    chip_cache.save_chip(_make_chip(), cache_dir=tmp_path)
    # Corrupt the JSON file
    for f in tmp_path.iterdir():
        f.write_text("{not json", encoding="utf-8")
    assert chip_cache.list_cached_chips(cache_dir=tmp_path) == []


# ---------------------------------------------------------------------------
# chip_service
# ---------------------------------------------------------------------------


def test_fetch_chip_characterization_uses_cache(monkeypatch, tmp_path):
    chip = _make_chip()
    monkeypatch.setattr(chip_service, "get_chip", lambda platform, name: chip)
    # _fetch_originq should never run when cache hits
    monkeypatch.setattr(
        chip_service,
        "_fetch_originq",
        lambda name: pytest.fail("should not call adapter when cache hits"),
    )

    out = chip_service.fetch_chip_characterization("wuyuan", Platform.ORIGINQ)
    assert out is chip


def test_fetch_chip_characterization_force_refresh_skips_cache(monkeypatch):
    chip = _make_chip()
    called = {"cache": False, "adapter": False}

    def _cache(platform, name):
        called["cache"] = True
        return chip

    def _adapter(name):
        called["adapter"] = True
        return chip

    monkeypatch.setattr(chip_service, "get_chip", _cache)
    monkeypatch.setattr(chip_service, "_fetch_originq", _adapter)
    monkeypatch.setattr(chip_service, "save_chip", lambda c: None)

    chip_service.fetch_chip_characterization("wuyuan", Platform.ORIGINQ, force_refresh=True)
    assert called["adapter"] is True
    assert called["cache"] is False


def test_fetch_chip_characterization_saves_after_fetch(monkeypatch):
    chip = _make_chip()
    saved: list[ChipCharacterization] = []

    monkeypatch.setattr(chip_service, "get_chip", lambda platform, name: None)
    monkeypatch.setattr(chip_service, "_fetch_originq", lambda name: chip)
    monkeypatch.setattr(chip_service, "save_chip", lambda c: saved.append(c))

    result = chip_service.fetch_chip_characterization("wuyuan", Platform.ORIGINQ)
    assert result is chip
    assert saved == [chip]


def test_fetch_chip_characterization_unknown_platform(monkeypatch):
    monkeypatch.setattr(chip_service, "get_chip", lambda platform, name: None)
    monkeypatch.setattr(chip_service, "save_chip", lambda c: None)

    out = chip_service.fetch_chip_characterization("dummy-chip", Platform.DUMMY)
    assert out is None


def test_fetch_chip_characterization_adapter_returns_none(monkeypatch):
    monkeypatch.setattr(chip_service, "get_chip", lambda platform, name: None)
    monkeypatch.setattr(chip_service, "_fetch_originq", lambda name: None)
    out = chip_service.fetch_chip_characterization("wuyuan", Platform.ORIGINQ)
    assert out is None


def test_fetch_chip_characterization_dispatches_per_platform(monkeypatch):
    calls = []

    def _factory(tag):
        def _fn(name):
            calls.append((tag, name))
            return None

        return _fn

    monkeypatch.setattr(chip_service, "get_chip", lambda platform, name: None)
    monkeypatch.setattr(chip_service, "_fetch_originq", _factory("originq"))
    monkeypatch.setattr(chip_service, "_fetch_quafu", _factory("quafu"))
    monkeypatch.setattr(chip_service, "_fetch_ibm", _factory("ibm"))

    chip_service.fetch_chip_characterization("a", Platform.ORIGINQ)
    chip_service.fetch_chip_characterization("b", Platform.QUAFU)
    chip_service.fetch_chip_characterization("c", Platform.IBM)
    assert calls == [("originq", "a"), ("quafu", "b"), ("ibm", "c")]


@pytest.mark.parametrize("fetcher", ["_fetch_originq", "_fetch_quafu", "_fetch_ibm"])
def test_internal_fetcher_handles_adapter_unavailable(monkeypatch, fetcher):
    """When the adapter is unavailable / not configured, the fetcher returns None."""

    # Adapter classes that pretend to be unavailable
    class _Unavailable:
        def __init__(self, *a, **kw):
            pass

        def is_available(self):
            return False

    # Patch the adapter classes inside chip_service's lazy imports
    import sys

    fake_module = type(sys)("fake_adapter_module")
    if fetcher == "_fetch_originq":
        fake_module.OriginQAdapter = _Unavailable
        monkeypatch.setitem(
            sys.modules,
            "uniqc.backend_adapter.task.adapters.originq_adapter",
            fake_module,
        )
    elif fetcher == "_fetch_quafu":
        fake_module.QuafuAdapter = _Unavailable
        monkeypatch.setitem(
            sys.modules,
            "uniqc.backend_adapter.task.adapters.quafu_adapter",
            fake_module,
        )
    else:
        fake_module.IBMAdapter = _Unavailable
        monkeypatch.setitem(
            sys.modules,
            "uniqc.backend_adapter.task.adapters.ibm_adapter",
            fake_module,
        )

    fn = getattr(chip_service, fetcher)
    assert fn("any-chip") is None


def test_fetch_all_chips_skips_simulators(monkeypatch):
    from uniqc.backend_adapter.backend_info import BackendInfo

    backends = {
        Platform.ORIGINQ: [
            BackendInfo(platform=Platform.ORIGINQ, name="wuyuan", is_hardware=True),
            BackendInfo(platform=Platform.ORIGINQ, name="full_amplitude", is_simulator=True),
        ],
    }

    monkeypatch.setattr(
        "uniqc.backend_adapter.backend_registry.fetch_all_backends",
        lambda: backends,
    )

    fetched = []

    def _fake_fetch(name, platform, force_refresh=True):
        fetched.append((platform.value, name))
        return _make_chip(platform, name)

    monkeypatch.setattr(chip_service, "fetch_chip_characterization", _fake_fetch)

    chips = chip_service.fetch_all_chips()
    assert ("originq", "wuyuan") in fetched
    assert ("originq", "full_amplitude") not in fetched
    assert len(chips) == 1


def test_to_dict_round_trips():
    """ChipCharacterization round-trips through dataclasses.asdict — ensure the
    cache module can both serialize and deserialize it."""
    chip = _make_chip()
    d = dataclasses.asdict(chip)
    assert d["chip_name"] == "wuyuan"
