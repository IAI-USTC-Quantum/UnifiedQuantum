"""Exponential decay fitter for cross-entropy benchmarking results.

Fits the model F(m) = A * r^m + B to a sequence of circuit fidelities
measured at different depths m, where r is the per-layer fidelity.
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "compute_hellinger_fidelity",
    "fit_exponential",
]


def compute_hellinger_fidelity(
    p_theory: np.ndarray,
    p_noisy: np.ndarray,
) -> float:
    """Compute the Hellinger fidelity between two probability distributions.

    F = (sum_i sqrt(p_i * q_i))^2

    This is the Sørensen-Dice coefficient applied to probability vectors.
    It equals 1 when the distributions are identical and approaches 0
    for orthogonal distributions.

    Args:
        p_theory: Ideal (noiseless) probability vector.
        p_noisy: Noisy (measured) probability vector.

    Returns:
        A float in [0, 1]. Higher is more similar.
    """
    p_theory = np.asarray(p_theory, dtype=np.float64)
    p_noisy = np.asarray(p_noisy, dtype=np.float64)

    # Clip to avoid sqrt of negative due to numerical noise
    p_theory = np.clip(p_theory, 0, 1)
    p_noisy = np.clip(p_noisy, 0, 1)

    overlap = np.sqrt(p_theory * p_noisy).sum()
    return float(overlap ** 2)


def fit_exponential(
    depths: list[int],
    fidelities: list[float],
    *,
    shots: int | None = None,
) -> dict[str, Any]:
    """Fit the exponential decay model F(m) = A * r^m + B.

    The model describes how the fidelity decays with circuit depth m.
    The parameter ``r`` (0 < r <= 1) is the per-layer fidelity.
    F = 1 at m=0 (perfect fidelity) and decays exponentially.

    Args:
        depths: List of circuit depths (m values).
        fidelities: List of Hellinger fidelities measured at each depth.
            Average over multiple circuits at the same depth before passing.

    Returns:
        dict with keys:
            - r: per-layer fidelity (0 < r <= 1)
            - A: amplitude coefficient
            - B: asymptotic offset
            - r_stderr: standard error on r
            - n_points: number of (depth, fidelity) data points used
    """
    depths_arr = np.asarray(depths, dtype=np.float64)
    fidelities_arr = np.asarray(fidelities, dtype=np.float64)

    if len(depths_arr) < 2:
        return {
            "r": float(np.mean(fidelities_arr)) if len(fidelities_arr) else 0.0,
            "A": 0.0,
            "B": 0.0,
            "r_stderr": 0.0,
            "n_points": len(depths_arr),
            "method": "mean_fallback",
        }

    # Use scipy if available
    try:
        from scipy.optimize import curve_fit
    except ImportError:
        return _fit_exponential_numpy(depths_arr, fidelities_arr)

    def model(m, A, r, B):
        return A * np.power(r, m) + B

    # Initial guess: A ≈ 1-B, B ≈ min(fidelities), r ≈ mid-range
    B0 = float(np.min(fidelities_arr))
    ratio = np.mean(fidelities_arr[1:] / np.maximum(fidelities_arr[:-1], 1e-12))
    r0 = float(np.clip(ratio, 0.5, 0.999))
    A0 = 1.0 - B0

    p0 = [A0, r0, B0]
    # Bounds: A > 0, 0 < r <= 1, B >= 0
    lower = [0.0, 0.001, 0.0]
    upper = [2.0, 1.0, 0.5]

    try:
        popt, pcov = curve_fit(
            model,
            depths_arr,
            fidelities_arr,
            p0=p0,
            bounds=(lower, upper),
            maxfev=10000,
        )
        A, r, B = popt
        # Standard error on r
        if pcov.shape == (3, 3):
            r_var = pcov[1, 1]
            r_stderr = float(np.sqrt(max(r_var, 0)))
        else:
            r_stderr = 0.0
        return {
            "r": float(r),
            "A": float(A),
            "B": float(B),
            "r_stderr": r_stderr,
            "n_points": len(depths_arr),
            "method": "scipy_curve_fit",
        }
    except Exception:
        return _fit_exponential_numpy(depths_arr, fidelities_arr)


def _fit_exponential_numpy(
    depths_arr: np.ndarray,
    fidelities_arr: np.ndarray,
) -> dict[str, Any]:
    """Fallback exponential fit using numpy (no scipy).

    Approximates F(m) = r^m by log(F) ≈ m * log(r).
    Uses weighted linear regression on log(F - B) where B is estimated.
    """
    # Estimate B as the minimum fidelity (asymptotic floor)
    B = float(np.min(fidelities_arr))
    residuals = fidelities_arr - B

    # Mask out non-positive residuals
    valid = residuals > 1e-9
    if valid.sum() < 2:
        return {
            "r": float(np.mean(fidelities_arr)),
            "A": 0.0,
            "B": B,
            "r_stderr": 0.0,
            "n_points": int(valid.sum()),
            "method": "numpy_fallback",
        }

    log_vals = np.log(residuals[valid])
    m_vals = depths_arr[valid]

    # Weighted linear regression: log(residual) ≈ log(A) + m * log(r)
    n = len(m_vals)
    m_mean = m_vals.mean()
    log_mean = log_vals.mean()
    ss_m = ((m_vals - m_mean) ** 2).sum()
    if ss_m < 1e-12:
        return {"r": 1.0, "A": 0.0, "B": B, "r_stderr": 0.0, "n_points": n, "method": "numpy_fallback"}

    cov_ml = ((m_vals - m_mean) * (log_vals - log_mean)).sum()
    slope = cov_ml / ss_m
    intercept = log_mean - slope * m_mean

    log_r = slope
    r = float(np.exp(np.clip(log_r, np.log(0.001), 0)))
    A = float(np.exp(intercept))

    # Simple stderr estimate from residuals
    predicted = A * np.power(r, depths_arr) + B
    residuals_all = fidelities_arr - predicted
    r_stderr = float(np.std(residuals_all) / np.sqrt(n)) if n > 2 else 0.0

    return {
        "r": r,
        "A": A,
        "B": B,
        "r_stderr": r_stderr,
        "n_points": n,
        "method": "numpy_fallback",
    }
