"""Tests for XEB exponential fitter."""

import numpy as np
import pytest

from uniqc.calibration.xeb.fitter import (
    compute_hellinger_fidelity,
    fit_exponential,
)


class TestHellingerFidelity:
    def test_identical_distributions(self):
        p = np.array([0.5, 0.3, 0.2])
        assert compute_hellinger_fidelity(p, p) == pytest.approx(1.0)

    def test_orthogonal_distributions(self):
        p = np.array([1.0, 0.0, 0.0])
        q = np.array([0.0, 1.0, 0.0])
        assert compute_hellinger_fidelity(p, q) == pytest.approx(0.0)

    def test_perfect_overlap(self):
        p = np.array([0.5, 0.5])
        q = np.array([0.5, 0.5])
        assert compute_hellinger_fidelity(p, q) == pytest.approx(1.0)

    def test_partial_overlap(self):
        p = np.array([1.0, 0.0])
        q = np.array([0.5, 0.5])
        # Hellinger = (sqrt(1*0.5) + sqrt(0*0.5))^2 = (sqrt(0.5))^2 = 0.5
        assert compute_hellinger_fidelity(p, q) == pytest.approx(0.5)

    def test_uniform_distributions(self):
        p = np.array([0.25, 0.25, 0.25, 0.25])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        assert compute_hellinger_fidelity(p, q) == pytest.approx(1.0)


class TestExponentialFit:
    def test_perfect_fidelity_no_decay(self):
        """F(m) = 1 for all m → r should be ~1.0."""
        depths = [5, 10, 20, 50]
        fidelities = [1.0] * len(depths)
        result = fit_exponential(depths, fidelities)
        assert result["r"] == pytest.approx(1.0, abs=0.01)
        assert result["method"] in ("scipy_curve_fit", "numpy_fallback", "mean_fallback")

    def test_exponential_decay_known_r(self):
        """Synthetic data with known r = 0.99, A=1, B=0."""
        r_true = 0.99
        A, B = 1.0, 0.0
        depths = [5, 10, 20, 50, 100]
        fidelities = [A * (r_true ** m) + B + np.random.normal(0, 0.001)
                      for m in depths]
        result = fit_exponential(depths, fidelities)
        assert 0.95 < result["r"] < 1.0
        assert result["r"] == pytest.approx(r_true, abs=0.02)

    def test_single_point_returns_mean(self):
        depths = [10]
        fidelities = [0.95]
        result = fit_exponential(depths, fidelities)
        assert result["method"] == "mean_fallback"
        assert result["r"] == pytest.approx(0.95)

    def test_empty_input(self):
        result = fit_exponential([], [])
        assert result["r"] == 0.0

    def test_high_decay(self):
        """Fast decay: r should be significantly less than 1."""
        r_true = 0.7
        depths = [2, 5, 10, 20]
        np.random.seed(42)
        fidelities = [0.7 ** m + np.random.normal(0, 0.01) for m in depths]
        result = fit_exponential(depths, fidelities)
        assert 0.5 < result["r"] < 0.9
