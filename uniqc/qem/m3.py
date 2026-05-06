"""M3 readout error mitigator.

Provides confusion-matrix-based readout error mitigation with TTL-based
calibration freshness enforcement.
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Any

import numpy as np

from uniqc.exceptions import StaleCalibrationError  # noqa: F401 — re-export

__all__ = ["M3Mitigator", "StaleCalibrationError"]


def _get_field(cal: Any, name: str) -> Any:
    """Read ``name`` from ``cal`` whether it is a dataclass or a dict."""
    if cal is None:
        raise ValueError("calibration result is None")
    if hasattr(cal, name):
        return getattr(cal, name)
    return cal[name]


class M3Mitigator:
    """M3 (Matrix Misassignment Mitigation) readout error mitigator.

    Uses a calibration confusion matrix to correct measurement outcomes via
    linear inversion. The calibration data can be provided directly or loaded
    from the calibration cache.

    Args:
        calibration_result: Pre-loaded ``ReadoutCalibrationResult``.
        cache_path: Path to a cached calibration JSON file.
        max_age_hours: Maximum acceptable age of calibration data in hours.
            If the cached data is older, ``StaleCalibrationError`` is raised.
        backend: Backend name used for cache lookup.
        qubit: Qubit index or pair (for cache lookup).

    Raises:
        StaleCalibrationError: If calibration data exceeds ``max_age_hours``.
        FileNotFoundError: If cache_path does not exist.
    """

    def __init__(
        self,
        calibration_result: Any | None = None,
        cache_path: str | pathlib.Path | None = None,
        max_age_hours: float = 24.0,
        backend: str = "dummy",
        qubit: int | tuple[int, int] | None = None,
        cache_dir: str | pathlib.Path | None = None,
    ) -> None:
        if calibration_result is not None:
            self._cal = calibration_result
            calibrated_at = ""
            try:
                calibrated_at = _get_field(calibration_result, "calibrated_at")
            except (KeyError, AttributeError):
                calibrated_at = ""
            if calibrated_at and max_age_hours is not None:
                self._check_age(calibrated_at, max_age_hours)
        elif cache_path is not None:
            self._cal = self._load_from_path(cache_path, max_age_hours)
        else:
            self._cal = None

        self._backend = backend
        self._qubit = qubit
        self._max_age_hours = max_age_hours
        self._cache_dir = cache_dir

    @property
    def calibration_result(self) -> Any:
        if self._cal is None:
            self._cal = self._load_from_cache(
                self._backend,
                self._qubit,
                self._max_age_hours,
                self._cache_dir,
            )
        return self._cal

    def mitigate_counts(
        self, counts: dict[int, int]
    ) -> dict[int, float]:
        """Apply M3 mitigation to measurement counts.

        Uses linear inversion: ``n_corrected = C⁻¹ · n_obs``.
        The result is normalized so the total counts are preserved.

        Args:
            counts: Dict mapping outcome (int bitstring) → observed count.

        Returns:
            Dict mapping outcome → corrected count (float, preserved total).
        """
        cal = self.calibration_result
        C = np.array(_get_field(cal, "confusion_matrix"))
        n = len(C)

        # Build observed vector
        n_obs = np.zeros(n)
        for outcome, cnt in counts.items():
            n_obs[int(outcome)] = float(cnt)

        total = n_obs.sum()
        if total == 0:
            return {}

        # Linear inversion: n_corrected = C^{-1} · n_obs
        try:
            C_inv = np.linalg.inv(C)
        except np.linalg.LinAlgError:
            # Singular matrix — fall back to identity
            C_inv = np.eye(n)

        n_corr = C_inv @ n_obs
        # Renormalize to preserve total
        if n_corr.sum() > 0:
            n_corr = n_corr * (total / n_corr.sum())

        # Clip negative values (can occur with ill-conditioned matrices)
        n_corr = np.clip(n_corr, 0, None)

        return {int(i): float(v) for i, v in enumerate(n_corr)}

    def mitigate_probabilities(
        self, probs: dict[str, float] | dict[int, float]
    ) -> dict[int, float]:
        """Apply M3 mitigation to a probability dictionary.

        Args:
            probs: Dict mapping outcome → probability.

        Returns:
            Dict mapping outcome (int) → corrected probability.
        """
        cal = self.calibration_result
        C = np.array(_get_field(cal, "confusion_matrix"))
        n = len(C)

        p_obs = np.zeros(n)
        for outcome, p in probs.items():
            p_obs[int(outcome)] = float(p)

        try:
            C_inv = np.linalg.inv(C)
        except np.linalg.LinAlgError:
            C_inv = np.eye(n)

        p_corr = C_inv @ p_obs
        # Renormalize
        p_corr = np.clip(p_corr, 0, None)
        total = p_corr.sum()
        if total > 0:
            p_corr /= total

        return {int(i): float(v) for i, v in enumerate(p_corr)}

    def _load_from_path(
        self, path: str | pathlib.Path, max_age_hours: float
    ) -> dict[str, Any]:
        """Load and validate calibration from a file path."""
        import json

        with open(path) as f:
            d = json.load(f)
        self._check_age(d.get("calibrated_at", ""), max_age_hours)
        return d

    def _load_from_cache(
        self,
        backend: str,
        qubit: int | tuple | None,
        max_age_hours: float,
        cache_dir: str | pathlib.Path | None = None,
    ) -> dict[str, Any]:
        """Find and load the freshest calibration result from cache."""
        import json

        from uniqc.calibration.results import find_cached_results

        if qubit is None:
            raise ValueError("qubit must be provided when loading from cache")

        result_type = "readout_2q" if isinstance(qubit, tuple) else "readout_1q"

        paths = find_cached_results(
            backend,
            result_type,
            max_age_hours=max_age_hours,
            cache_dir=cache_dir,
        )
        if not paths:
            raise FileNotFoundError(
                f"No fresh calibration result found for backend={backend}, "
                f"qubit={qubit}, max_age_hours={max_age_hours}. "
                f"Run calibration first."
            )

        matching_paths: list[pathlib.Path] = []
        expected_qubit = tuple(qubit) if isinstance(qubit, tuple) else qubit
        for path in paths:
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                continue
            cached_qubit = data.get("qubit")
            if isinstance(cached_qubit, list):
                cached_qubit = tuple(cached_qubit)
            if cached_qubit == expected_qubit:
                matching_paths.append(path)

        if not matching_paths:
            raise FileNotFoundError(
                f"No fresh calibration result found for backend={backend}, "
                f"qubit={qubit}, max_age_hours={max_age_hours}. "
                f"Run calibration first."
            )

        # Use the most recent exact qubit/pair match.
        latest = max(matching_paths, key=lambda p: p.stat().st_mtime)
        return self._load_from_path(latest, max_age_hours)

    def _check_age(self, calibrated_at: str, max_age_hours: float) -> None:
        """Raise StaleCalibrationError if the calibration is too old."""
        if not calibrated_at:
            return
        try:
            # Parse ISO-8601
            ts = datetime.fromisoformat(calibrated_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            # Ensure tz-aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_hours = (now - ts).total_seconds() / 3600
            if age_hours > max_age_hours:
                raise StaleCalibrationError(
                    f"Calibration data is {age_hours:.1f} hours old "
                    f"(max_age_hours={max_age_hours}). "
                    f"Calibrated at: {calibrated_at}"
                )
        except ValueError:
            pass  # Can't parse timestamp — skip age check
