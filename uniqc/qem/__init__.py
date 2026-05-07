"""Quantum Error Mitigation (QEM) module.

Provides readout error mitigation via confusion-matrix inversion (M3).
Uses calibration data from ``uniqc.calibration`` with TTL-based freshness enforcement.
"""

from uniqc.qem.m3 import M3Mitigator, StaleCalibrationError
from uniqc.qem.readout_em import ReadoutEM
from uniqc.qem.zne import ZNE

__all__ = [
    "M3Mitigator",
    "StaleCalibrationError",
    "ReadoutEM",
    "ZNE",
]
