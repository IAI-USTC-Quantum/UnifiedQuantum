"""Calibration module for UnifiedQuantum.

Provides active chip calibration experiments:
- XEB (cross-entropy benchmarking) for 1q and 2q gate fidelity
- Readout calibration for measurement error characterization

Results are saved to ``~/.uniqc/calibration_cache/`` with ISO-8601 timestamps.
"""

from uniqc.calibration import readout, xeb
from uniqc.calibration.results import (
    CalibrationResult,
    ReadoutCalibrationResult,
    XEBResult,
    find_cached_results,
    load_calibration_result,
    save_calibration_result,
)

__all__ = [
    "xeb",
    "readout",
    "CalibrationResult",
    "XEBResult",
    "ReadoutCalibrationResult",
    "save_calibration_result",
    "load_calibration_result",
    "find_cached_results",
]
