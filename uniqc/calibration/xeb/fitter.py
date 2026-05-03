"""Exponential decay fitter for cross-entropy benchmarking results.

Fits the model F(m) = A * r^m + B to a sequence of circuit fidelities
measured at different depths m, where r is the per-layer fidelity.
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "compute_hellinger_fidelity",
    "compute_linear_xeb",
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


def compute_linear_xeb(
    p_ideal: np.ndarray,
    p_observed: np.ndarray,
    *,
    normalized: bool = True,
    eps: float = 1e-12,
) -> float:
    """Compute the standard linear XEB estimator.

    Unnormalized linear XEB is ``N * sum_x p_observed(x) p_ideal(x) - 1``.
    For small-qubit calibration circuits, the Porter-Thomas assumption is often
    weak, so the default uses the normalized estimator:

    ``(dot(p_observed, p_ideal) - 1/N) / (dot(p_ideal, p_ideal) - 1/N)``.

    The normalized form has baseline 0 for uniform/random output and 1 for
    exactly ideal output. If the ideal distribution is uniform, the normalized
    estimator is undefined and ``nan`` is returned.
    """
    p_ideal = np.asarray(p_ideal, dtype=np.float64)
    p_observed = np.asarray(p_observed, dtype=np.float64)

    if len(p_ideal) != len(p_observed):
        raise ValueError("p_ideal and p_observed must have the same length")
    if len(p_ideal) == 0:
        return float("nan")

    p_ideal = np.clip(p_ideal, 0, None)
    p_observed = np.clip(p_observed, 0, None)
    ideal_total = p_ideal.sum()
    observed_total = p_observed.sum()
    if ideal_total <= eps or observed_total <= eps:
        return float("nan")
    p_ideal = p_ideal / ideal_total
    p_observed = p_observed / observed_total

    n_states = len(p_ideal)
    overlap = float(np.dot(p_observed, p_ideal))
    uniform_overlap = 1.0 / n_states

    if not normalized:
        return float(n_states * overlap - 1.0)

    ideal_contrast = float(np.dot(p_ideal, p_ideal) - uniform_overlap)
    if abs(ideal_contrast) <= eps:
        return float("nan")
    return float((overlap - uniform_overlap) / ideal_contrast)


def fit_exponential(
    depths: list[int],
    fidelities: list[float],
    *,
    shots: int | None = None,
    baseline: float | None = 0.0,
) -> dict[str, Any]:
    """Fit the exponential decay model F(m) = A * r^m + B.

    The model describes how the fidelity decays with circuit depth m.
    The parameter ``r`` (0 < r <= 1) is the per-layer fidelity.
    F = 1 at m=0 (perfect fidelity) and decays exponentially.

    Args:
        depths: List of circuit depths (m values).
        fidelities: List of XEB values measured at each depth.
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
    finite = np.isfinite(depths_arr) & np.isfinite(fidelities_arr)
    depths_arr = depths_arr[finite]
    fidelities_arr = fidelities_arr[finite]

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
        return _fit_exponential_numpy(depths_arr, fidelities_arr, baseline=baseline)

    def model_fixed_baseline(m, A, r):
        return A * np.power(r, m) + float(baseline)

    def model_free_baseline(m, A, r, B):
        return A * np.power(r, m) + B

    # Initial guess: A ≈ F(0)-B, r ≈ adjacent ratio
    B0 = float(np.min(fidelities_arr)) if baseline is None else float(baseline)
    shifted = fidelities_arr - B0
    ratio = np.mean(shifted[1:] / np.maximum(shifted[:-1], 1e-12))
    r0 = float(np.clip(ratio, 0.5, 0.999))
    A0 = float(max(fidelities_arr[0] - B0, 1e-6))

    if baseline is None:
        p0 = [A0, r0, B0]
        lower = [-2.0, 0.001, -1.0]
        upper = [2.0, 1.0, 1.0]
        model = model_free_baseline
    else:
        p0 = [A0, r0]
        lower = [-2.0, 0.001]
        upper = [2.0, 1.0]
        model = model_fixed_baseline

    try:
        popt, pcov = curve_fit(
            model,
            depths_arr,
            fidelities_arr,
            p0=p0,
            bounds=(lower, upper),
            maxfev=10000,
        )
        if baseline is None:
            A, r, B = popt
            r_index = 1
        else:
            A, r = popt
            B = float(baseline)
            r_index = 1
        # Standard error on r
        if pcov.shape[0] > r_index:
            r_var = pcov[r_index, r_index]
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
        return _fit_exponential_numpy(depths_arr, fidelities_arr, baseline=baseline)


def _fit_exponential_numpy(
    depths_arr: np.ndarray,
    fidelities_arr: np.ndarray,
    *,
    baseline: float | None = 0.0,
) -> dict[str, Any]:
    """Fallback exponential fit using numpy (no scipy).

    Fits F(m) = A * r^m + B using linear regression on log(F - B),
    with a robust per-layer fidelity estimate derived from all adjacent
    (depth, fidelity) pairs. When the data is non-monotonic (positive slope
    due to noise/variance), the pairwise ratio method provides a sensible r
    instead of falling back to r=1.0.
    """
    B = float(np.min(fidelities_arr)) if baseline is None else float(baseline)

    # ---- Method 1: linear regression on log(F - B) ----
    residuals = fidelities_arr - B
    positive = residuals > 1e-12
    if positive.sum() < 2:
        return {
            "r": 0.0,
            "A": float(fidelities_arr[0] - B) if len(fidelities_arr) else 0.0,
            "B": B,
            "r_stderr": 0.0,
            "n_points": len(depths_arr),
            "method": "numpy_insufficient_positive_points",
        }

    log_vals = np.log(residuals[positive])
    m_vals = depths_arr[positive].astype(float)
    f_vals = fidelities_arr[positive].astype(float)
    n = len(m_vals)
    m_mean = m_vals.mean()
    log_mean = log_vals.mean()
    ss_m = ((m_vals - m_mean) ** 2).sum()

    cov_ml = 0.0
    if ss_m >= 1e-12:
        cov_ml = float(((m_vals - m_mean) * (log_vals - log_mean)).sum())
        slope = cov_ml / float(ss_m)
        intercept = log_mean - slope * m_mean
        r_lin = float(np.exp(np.clip(slope, np.log(0.001), 0)))
        A_lin = float(np.exp(intercept))
    else:
        r_lin = 1.0
        A_lin = 0.0

    # ---- Method 2: pairwise geometric-mean r (robust to non-monotonic data) ----
    # For F(m) = A * r^m + B, take adjacent pairs:
    #   (F_i - B) / (F_j - B) ≈ r^(m_i - m_j)
    #   => r ≈ ((F_i - B) / (F_j - B)) ^ (1/(m_i - m_j))
    log_ratios: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            delta_m = float(m_vals[j] - m_vals[i])
            if abs(delta_m) <= 1e-12:
                continue
            num = max(f_vals[i] - B, 1e-12)
            den = max(f_vals[j] - B, 1e-12)
            log_ratios.append((np.log(num) - np.log(den)) / delta_m)

    if log_ratios:
        mean_log_r = float(np.mean(log_ratios))
        r_pair = float(np.exp(np.clip(mean_log_r, np.log(0.001), 0)))
    else:
        r_pair = 1.0

    # Prefer the linear regression result when the slope is negative (physically
    # expected for XEB decay). When slope >= 0 the data is non-monotonic and the
    # pairwise estimate is more reliable.
    if ss_m >= 1e-12 and cov_ml < 0:
        r = r_lin
        A = A_lin
        method = "numpy_fallback"
    else:
        # Pairwise estimate is the primary result for non-monotonic data.
        # Use it to back-solve A from the first data point: A = (F_0 - B) / r^m0
        r = r_pair
        A = float((f_vals[0] - B) / max(r ** m_vals[0], 1e-12))
        method = "numpy_fallback_pairwise"

    # Stderr estimate
    predicted = A * np.power(r, m_vals) + B
    residuals_all = f_vals - predicted
    r_stderr = float(np.std(residuals_all) / np.sqrt(n)) if n > 2 else 0.0

    return {
        "r": r,
        "A": A,
        "B": B,
        "r_stderr": r_stderr,
        "n_points": n,
        "method": method,
    }
