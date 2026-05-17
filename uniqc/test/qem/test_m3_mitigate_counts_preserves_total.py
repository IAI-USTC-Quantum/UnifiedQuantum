"""Regression test for ``M3Mitigator.mitigate_counts`` clip-then-rescale order.

Before the H-3 fix, ``mitigate_counts`` rescaled the linear-inversion
output to the observed total *first* and then clipped negatives to zero.
Whenever ``C^{-1} · n_obs`` produced any negative entry, clipping after
rescaling silently dropped that mass and the returned counts no longer
summed to the observed total.  The fix swaps the order: clip first, then
rescale, mirroring the existing ``mitigate_probabilities`` pattern.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np

from uniqc.qem import M3Mitigator


def _write_calibration(path, confusion_matrix) -> None:
    data = {
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "backend": "dummy:local:simulator",
        "type": "readout_2q",
        "qubit": 0,
        "confusion_matrix": [list(map(float, row)) for row in confusion_matrix],
        "assignment_fidelity": 0.9,
    }
    with open(path, "w") as f:
        json.dump(data, f)


def test_mitigate_counts_clips_then_preserves_total(tmp_path) -> None:
    # A 2x2 confusion matrix with significant asymmetric off-diagonals.
    # For observed counts [950, 50] this produces a negative entry in
    # C^{-1} · n_obs, which exposes the clip-after-rescale bug.
    C = np.array(
        [
            [0.90, 0.40],
            [0.10, 0.60],
        ]
    )
    cache_file = tmp_path / "cal.json"
    _write_calibration(cache_file, C)

    mit = M3Mitigator(cache_path=str(cache_file), max_age_hours=24.0)

    total = 1000
    counts = {0: 950, 1: 50}

    # Sanity check: the raw linear inversion really does produce a negative.
    raw = np.linalg.inv(C) @ np.array([counts[0], counts[1]], dtype=float)
    assert (raw < 0).any(), f"Test setup is invalid — needs an inversion that yields a negative entry; got raw={raw}"

    corrected = mit.mitigate_counts(counts)

    total_corr = sum(corrected.values())
    assert total_corr == 1000, f"Total counts not preserved after mitigation: {total_corr} vs {total}"
    assert all(v >= 0 for v in corrected.values()), f"Negative entries leaked through clipping: {corrected}"
