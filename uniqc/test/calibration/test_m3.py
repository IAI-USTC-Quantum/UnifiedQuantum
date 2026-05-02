"""Tests for M3 readout error mitigator."""

import json
import tempfile
from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from uniqc.qem import M3Mitigator, StaleCalibrationError


def _write_cache(path, calibrated_at: str) -> None:
    data = {
        "calibrated_at": calibrated_at,
        "backend": "dummy",
        "type": "readout_1q",
        "qubit": 0,
        "confusion_matrix": [[1.0, 0.0], [0.0, 1.0]],
        "assignment_fidelity": 1.0,
    }
    with open(path, "w") as f:
        json.dump(data, f)


class TestM3Mitigation:
    def test_identity_matrix_passes_through(self, tmp_path):
        """With identity confusion matrix, counts should be unchanged."""
        cache_file = tmp_path / "test.json"
        _write_cache(cache_file, datetime.now(timezone.utc).isoformat())

        mit = M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)
        counts = {0: 800, 1: 200}
        corrected = mit.mitigate_counts(counts)

        assert corrected[0] == pytest.approx(800.0, rel=0.01)
        assert corrected[1] == pytest.approx(200.0, rel=0.01)

    def test_non_identity_correction(self, tmp_path):
        """Non-identity confusion matrix should shift counts."""
        cache_file = tmp_path / "test.json"
        # Asymmetric confusion: P(0|1) = 0.2, P(1|0) = 0.1
        data = {
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
            "backend": "dummy",
            "type": "readout_1q",
            "qubit": 0,
            "confusion_matrix": [
                [0.9, 0.2],
                [0.1, 0.8],
            ],
            "assignment_fidelity": 0.85,
        }
        with open(cache_file, "w") as f:
            json.dump(data, f)

        mit = M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)
        counts = {0: 500, 1: 500}
        corrected = mit.mitigate_counts(counts)

        # After correction, counts should be closer to [500, 500]
        # (they may not be exactly that due to the specific matrix)
        total = sum(corrected.values())
        assert total == pytest.approx(1000.0)  # Total preserved
        assert 0 <= corrected[0] <= 1000
        assert 0 <= corrected[1] <= 1000

    def test_probability_interface(self, tmp_path):
        """mitigate_probabilities should work similarly to mitigate_counts."""
        cache_file = tmp_path / "test.json"
        _write_cache(cache_file, datetime.now(timezone.utc).isoformat())

        mit = M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)
        probs = {0: 0.8, 1: 0.2}
        corrected = mit.mitigate_probabilities(probs)

        total = sum(corrected.values())
        assert total == pytest.approx(1.0)
        assert 0 <= corrected[0] <= 1.0
        assert 0 <= corrected[1] <= 1.0

    def test_total_count_preserved(self, tmp_path):
        """The sum of corrected counts should equal the original total."""
        cache_file = tmp_path / "test.json"
        _write_cache(cache_file, datetime.now(timezone.utc).isoformat())

        mit = M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)
        original_total = 1000
        counts = {0: 700, 1: 300}
        corrected = mit.mitigate_counts(counts)

        assert sum(corrected.values()) == pytest.approx(original_total, rel=0.001)

    def test_stale_calibration_error(self, tmp_path):
        """Cache older than max_age_hours should raise StaleCalibrationError."""
        cache_file = tmp_path / "test.json"
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        _write_cache(cache_file, old_time)

        with pytest.raises(StaleCalibrationError) as exc_info:
            M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)
        assert "48" in str(exc_info.value) or "24" in str(exc_info.value)


class TestM3MitigatorWithRealMatrix:
    """Test with realistic confusion matrices."""

    def test_2x2_realistic_matrix(self, tmp_path):
        """Test with a realistic noisy 2×2 confusion matrix."""
        cache_file = tmp_path / "realistic.json"
        # Realistic: P(0|0)=0.98, P(1|1)=0.96, P(0|1)=0.04, P(1|0)=0.02
        data = {
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
            "backend": "dummy",
            "type": "readout_1q",
            "qubit": 0,
            "confusion_matrix": [
                [0.98, 0.04],
                [0.02, 0.96],
            ],
            "assignment_fidelity": 0.97,
        }
        with open(cache_file, "w") as f:
            json.dump(data, f)

        mit = M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)
        counts = {0: 980, 1: 20}
        corrected = mit.mitigate_counts(counts)

        total = sum(corrected.values())
        assert total == pytest.approx(1000.0, rel=0.001)
        # Corrected counts should be closer to [1000, 0]
        assert corrected[0] > corrected[1]
