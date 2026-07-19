"""On-disk cache for chip characterization data.

Cache file layout
----------------
``~/.uniqc/backend/chips/{provider}-{chip_name}.json``

Each file contains a single :class:`~uniqc.cli.chip_info.ChipCharacterization` object.

The cache used to live at ``~/.uniqc/backend-cache/``; on first access the
legacy ``*.json`` files are moved to the new location automatically.

Public API
----------
get_chip(platform, chip_name)
    Return cached ChipCharacterization or None.
save_chip(chip)
    Write a ChipCharacterization to its cache file.
list_cached_chips(platform=None)
    Return all cached ChipCharacterization objects, optionally filtered by platform.
invalidate_chip(platform, chip_name)
    Remove a single chip's cache file.
chip_cache_info()
    Return age / stale metadata for all cached chips.
"""

from __future__ import annotations

import contextlib
import shutil
import time
import warnings
from pathlib import Path
from typing import Any

from uniqc.backend_adapter.backend_info import Platform
from uniqc.cli.chip_info import ChipCharacterization

DEFAULT_CACHE_DIR = Path.home() / ".uniqc" / "backend" / "chips"
LEGACY_CACHE_DIR = Path.home() / ".uniqc" / "backend-cache"

# Snapshot of the built-in default. Tests redirect ``DEFAULT_CACHE_DIR`` via
# monkeypatching; the legacy migration compares against this snapshot so it
# never moves real user state into a test's temporary directory.
_BUILTIN_CACHE_DIR = DEFAULT_CACHE_DIR
_migration_attempted = False


def _migrate_legacy_cache() -> None:
    """Move legacy ``~/.uniqc/backend-cache/*.json`` chip files once per process."""
    global _migration_attempted
    if _migration_attempted:
        return
    _migration_attempted = True
    if DEFAULT_CACHE_DIR != _BUILTIN_CACHE_DIR:
        return
    legacy_dir = LEGACY_CACHE_DIR
    if not legacy_dir.is_dir():
        return
    try:
        DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        for path in legacy_dir.iterdir():
            if path.suffix != ".json" or not path.is_file():
                continue
            target = DEFAULT_CACHE_DIR / path.name
            if target.exists():
                continue
            shutil.move(str(path), str(target))
    except OSError as exc:
        warnings.warn(f"Failed to migrate legacy chip cache ({legacy_dir}): {exc}", stacklevel=2)
        return
    # Only succeeds when the legacy directory is empty afterwards;
    # leftover non-JSON files keep it alive without a warning.
    with contextlib.suppress(OSError):
        legacy_dir.rmdir()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chip_path(cache_dir: Path | None, platform: Platform, chip_name: str) -> Path:
    """Return the path for a chip's cache file.

    The chip_name may contain colons (e.g. ``wuyuan:d5``). Replace with underscore
    for the filename to keep filesystem compatibility.
    """
    safe = chip_name.replace(":", "_").replace("/", "_")
    return (cache_dir or DEFAULT_CACHE_DIR) / f"{platform.value}-{safe}.json"


def _read_chip(path: Path) -> ChipCharacterization | None:
    """Read and deserialize a single chip cache file, or return None if absent."""
    if not path.exists():
        return None
    import json

    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return ChipCharacterization.from_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        warnings.warn(f"Corrupt chip cache {path}: {exc}", stacklevel=3)
        return None


def _write_chip(chip: ChipCharacterization, path: Path) -> None:
    """Serialize a ChipCharacterization to its cache file."""
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(chip.to_dict(), fh, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except OSError as exc:
        warnings.warn(f"Failed to write chip cache: {exc}", stacklevel=3)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_chip(
    platform: Platform,
    chip_name: str,
    cache_dir: Path | None = None,
) -> ChipCharacterization | None:
    """Return the cached ChipCharacterization for a chip, or None if not cached."""
    if cache_dir is None:
        _migrate_legacy_cache()
    path = _chip_path(cache_dir, platform, chip_name)
    return _read_chip(path)


def save_chip(
    chip: ChipCharacterization,
    cache_dir: Path | None = None,
) -> None:
    """Write a ChipCharacterization to its cache file.

    The path is derived from ``chip.platform`` and ``chip.chip_name``.
    """
    if cache_dir is None:
        _migrate_legacy_cache()
    path = _chip_path(cache_dir, chip.platform, chip.chip_name)
    _write_chip(chip, path)


def list_cached_chips(
    platform: Platform | None = None,
    cache_dir: Path | None = None,
) -> list[ChipCharacterization]:
    """Return all cached ChipCharacterization objects.

    If *platform* is given, only chips for that platform are returned.
    """
    if cache_dir is None:
        _migrate_legacy_cache()
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    if not cache_dir.is_dir():
        return []

    chips: list[ChipCharacterization] = []
    platforms = {platform.value} if platform else None

    for path in cache_dir.iterdir():
        if path.suffix != ".json":
            continue
        # filename format: {platform}-{chip_name}.json
        name = path.stem  # stem excludes suffix
        if platforms and not name.startswith(tuple(f"{p}-" for p in platforms)):
            continue
        chip = _read_chip(path)
        if chip is not None:
            chips.append(chip)

    return chips


def invalidate_chip(
    platform: Platform,
    chip_name: str,
    cache_dir: Path | None = None,
) -> None:
    """Remove the cache file for a specific chip."""
    if cache_dir is None:
        _migrate_legacy_cache()
    path = _chip_path(cache_dir, platform, chip_name)
    path.unlink(missing_ok=True)


def chip_cache_info(
    cache_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Return metadata (age, stale, chip count) for each cached chip file.

    Returns a dict keyed by ``"{platform}:{chip_name}"``.
    """
    if cache_dir is None:
        _migrate_legacy_cache()
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    if not cache_dir.is_dir():
        return {}

    info: dict[str, dict[str, Any]] = {}
    for path in cache_dir.iterdir():
        if path.suffix != ".json":
            continue
        chip = _read_chip(path)
        if chip is None:
            continue
        key = chip.full_id
        mtime = path.stat().st_mtime
        # Clamp at 0: on Windows, st_mtime can be recorded with finer
        # precision than time.time(), making the difference slightly negative
        # immediately after a write.
        age_seconds = max(0.0, time.time() - mtime)
        info[key] = {
            "platform": chip.platform.value,
            "chip_name": chip.chip_name,
            "mtime": mtime,
            "age_seconds": age_seconds,
            "is_stale": age_seconds > 86400,  # stale after 24 h
            "num_qubits": len(chip.available_qubits),
            "num_pairs": len(chip.two_qubit_data),
            "calibrated_at": chip.calibrated_at,
        }
    return info
