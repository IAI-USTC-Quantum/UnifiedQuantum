"""Disk cache for platform backend information.

Cache file layout
----------------
``~/.uniqc/cache/backends.json``
    Top-level dict with one key per platform::

        {
          "originq": {
            "updated_at": "2026-04-28T12:00:00Z",
            "backends": [BackendInfo, ...]
          },
          "quafu": { ... },
          "ibm": { ... }
        }

Cache TTL
---------
Each platform entry is considered stale after 24 hours.  The ``update()``
function bypasses this check when called explicitly (``uniqc backend update``).
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path
from typing import Any

from uniqc.backend_info import BackendInfo, Platform

DEFAULT_CACHE_DIR = Path.home() / ".uniqc" / "cache"
CACHE_FILE = "backends.json"
TTL_SECONDS = 24 * 60 * 60  # 24 hours


# ---------------------------------------------------------------------------
# Low-level file I/O
# ---------------------------------------------------------------------------

def _read_cache(cache_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return the parsed cache file, or an empty dict if absent/invalid."""
    path = (cache_dir or DEFAULT_CACHE_DIR) / CACHE_FILE
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        warnings.warn(f"Corrupt backend cache ({path}): {exc}", stacklevel=2)
        return {}


def _write_cache(data: dict[str, dict[str, Any]], cache_dir: Path | None = None) -> None:
    """Atomically write the cache file."""
    cache_dir = (cache_dir or DEFAULT_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / CACHE_FILE
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except OSError as exc:
        warnings.warn(f"Failed to write backend cache: {exc}", stacklevel=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_stale(platform: str, cache_dir: Path | None = None) -> bool:
    """Return True when the cached data for ``platform`` is absent or expired."""
    cache = _read_cache(cache_dir)
    entry = cache.get(platform)
    if not entry:
        return True
    updated_at = entry.get("updated_at", 0)
    return (time.time() - updated_at) > TTL_SECONDS


def get_cached_backends(
    platform: Platform,
    cache_dir: Path | None = None,
) -> list[BackendInfo]:
    """Return the cached BackendInfo list for ``platform``, or an empty list."""
    cache = _read_cache(cache_dir)
    raw = cache.get(platform.value, {}).get("backends", [])
    return [BackendInfo.from_dict(b) for b in raw]


def update_cache(
    platform: Platform,
    backends: list[BackendInfo],
    cache_dir: Path | None = None,
) -> None:
    """Write ``backends`` to the cache under ``platform``."""
    cache = _read_cache(cache_dir)
    cache[platform.value] = {
        "updated_at": time.time(),
        "backends": [b.to_dict() for b in backends],
    }
    _write_cache(cache, cache_dir)


def invalidate(platform: Platform, cache_dir: Path | None = None) -> None:
    """Remove the cached entry for ``platform``."""
    cache = _read_cache(cache_dir)
    cache.pop(platform.value, None)
    _write_cache(cache, cache_dir)


def invalidate_all(cache_dir: Path | None = None) -> None:
    """Clear the entire backend cache."""
    _write_cache({}, cache_dir)


def cache_info(cache_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return a human-readable summary of what's in the cache.

    Returns a dict mapping platform name to metadata (updated_at as a
    human-readable timestamp, is_stale bool, num_backends int).
    """
    cache = _read_cache(cache_dir)
    now = time.time()
    result: dict[str, dict[str, Any]] = {}
    for platform_str, entry in cache.items():
        updated_at = entry.get("updated_at", 0)
        age_seconds = now - updated_at
        result[platform_str] = {
            "updated_at": updated_at,
            "age_seconds": age_seconds,
            "is_stale": age_seconds > TTL_SECONDS,
            "num_backends": len(entry.get("backends", [])),
        }
    return result
