"""Calibration result schemas for UnifiedQuantum.

All calibration results include a `calibrated_at` ISO-8601 timestamp
set by the calibration module. Results are saved to ~/.uniqc/calibration_cache/.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Literal

__all__ = [
    "CalibrationResult",
    "XEBResult",
    "ReadoutCalibrationResult",
]


def _now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Base class for all calibration results."""

    calibrated_at: str  # ISO-8601 UTC timestamp, set by calibration module
    backend: str  # e.g. "dummy", "origin:wuyuan:wk180"
    type: str  # "xeb_1q" | "xeb_2q" | "xeb_2q_parallel" | "readout_1q" | "readout_2q"

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CalibrationResult:
        raise NotImplementedError(f"from_dict not implemented for {cls.__name__}")


# ---------------------------------------------------------------------------
# XEB
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class XEBResult(CalibrationResult):
    """Result of a cross-entropy benchmarking experiment."""

    qubit: int | None = None  # None for parallel multi-pair XEB
    pairs: list[tuple[int, int]] | None = None  # for parallel XEB
    type: Literal["xeb_1q", "xeb_2q", "xeb_2q_parallel"] = "xeb_1q"
    # Exponential fit: F(m) = A * r^m + B
    fidelity_per_layer: float = 0.0  # r from exponential fit (0 < r <= 1)
    fidelity_std_error: float = 0.0
    fit_a: float = 0.0
    fit_b: float = 0.0
    fit_r: float = 0.0
    depths: tuple[int, ...] = ()
    n_circuits: int = 0
    shots: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        # Convert tuples to lists for JSON
        d["pairs"] = list(self.pairs) if self.pairs is not None else None
        d["depths"] = list(self.depths)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> XEBResult:
        d = dict(d)
        d["depths"] = tuple(d["depths"])
        d["pairs"] = [(int(a), int(b)) for a, b in d["pairs"]] if d.get("pairs") else None
        return cls(**d)


# ---------------------------------------------------------------------------
# Readout Calibration
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class ReadoutCalibrationResult(CalibrationResult):
    """Result of a readout calibration experiment.

    Attributes:
        type: "readout_1q" or "readout_2q"
        qubit: int for 1q, tuple[int, int] for 2q
        confusion_matrix:
            1q: 2x2 matrix where rows=measured, cols=prepared.
                ``confusion_matrix[i][j] = P(measure=i | prep=j)``, so the
                diagonal is ``[P(0|0), P(1|1)]``.
            2q: 4x4 matrix where rows=measured, cols=prepared (|00⟩,|01⟩,|10⟩,|11⟩)
        assignment_fidelity: average diagonal element = (p00+p11)/2 (1q) or avg(diagonal) (2q)
    """

    type: Literal["readout_1q", "readout_2q"] = "readout_1q"
    qubit: int | tuple[int, int] = 0
    confusion_matrix: tuple[tuple[float, ...], ...] = ()  # 2x2 or 4x4
    assignment_fidelity: float = 0.0

    def __getitem__(self, name: str) -> Any:
        """Dict-like access for backward compatibility."""
        if hasattr(self, name):
            return getattr(self, name)
        raise KeyError(name)

    def __contains__(self, name: str) -> bool:
        """Support ``"key" in result`` for backward compatibility."""
        return hasattr(self, name)

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["confusion_matrix"] = [list(row) for row in self.confusion_matrix]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReadoutCalibrationResult:
        d = dict(d)
        d["confusion_matrix"] = tuple(tuple(row) for row in d["confusion_matrix"])
        q = d["qubit"]
        d["qubit"] = tuple(q) if isinstance(q, list) else int(q)
        return cls(**d)


# ---------------------------------------------------------------------------
# Cache I/O helpers
# ---------------------------------------------------------------------------

_CALIBRATION_CACHE_DIR = pathlib.Path.home() / ".uniqc" / "calibration_cache"


def ensure_cache_dir() -> pathlib.Path:
    """Ensure the calibration cache directory exists."""
    _CALIBRATION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CALIBRATION_CACHE_DIR


def save_calibration_result(
    result: CalibrationResult,
    *,
    type_prefix: str,
    cache_dir: pathlib.Path | str | None = None,
) -> str:
    """Save a calibration result to the cache and return the file path."""
    if cache_dir is None:
        cache_dir = ensure_cache_dir()
    else:
        cache_dir = pathlib.Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
    qid = _qubit_identifier(result)
    ts = (
        result.calibrated_at
        .replace("+00:00", "Z")
        .replace(":", "")
        .replace("-", "")
    )
    filename = f"{type_prefix}_{result.backend}_{qid}_{ts}.json"
    path = cache_dir / filename
    with open(path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)
    return str(path)


def _qubit_identifier(result: CalibrationResult) -> str:
    if isinstance(result, XEBResult):
        if result.pairs is not None:
            return "pairs-" + "-".join(f"{a}-{b}" for a, b in result.pairs)
        return f"q{result.qubit}"
    if isinstance(result, ReadoutCalibrationResult):
        if isinstance(result.qubit, tuple):
            return f"pair-{result.qubit[0]}-{result.qubit[1]}"
        return f"q{result.qubit}"
    return "unknown"


def load_calibration_result(path: str | pathlib.Path) -> CalibrationResult:
    """Load a calibration result from a cache file."""
    with open(path) as f:
        d = json.load(f)
    t = d["type"]
    if t.startswith("xeb"):
        return XEBResult.from_dict(d)
    return ReadoutCalibrationResult.from_dict(d)


def find_cached_results(
    backend: str,
    result_type: str,
    *,
    max_age_hours: float | None = None,
    cache_dir: pathlib.Path | str | None = None,
) -> list[pathlib.Path]:
    """Find cached calibration result files matching backend + type.

    Optionally filters by age.
    """
    if cache_dir is None:
        cache_dir = ensure_cache_dir()
    else:
        cache_dir = pathlib.Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{result_type}_{backend}_"
    results = []
    for p in cache_dir.iterdir():
        if p.is_file() and p.name.startswith(prefix):
            if max_age_hours is not None:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                age_hours = (now - mtime).total_seconds() / 3600
                if age_hours > max_age_hours:
                    continue
            results.append(p)
    return sorted(results)
