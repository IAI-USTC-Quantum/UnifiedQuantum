"""Regression tests for :mod:`uniqc.qem.zne`.

The current implementation in ``uniqc/qem/zne.py`` is a placeholder that
intentionally raises :class:`NotImplementedError` from
:class:`uniqc.qem.zne.ZNE.__init__` (tracking issue E-U4 in
``uniqc-report.md``). These tests do two things:

* lock in the current placeholder behaviour so future refactors don't
  accidentally regress the "raise on construction" contract; and
* document the expected behaviour for each extrapolation strategy
  (linear, Richardson, exponential) as :func:`pytest.skip` calls so the
  moment the implementation lands the tests can be flipped to active.

The skipped sub-cases describe the analytic ground truths the real
implementation should reproduce when wired up.
"""

from __future__ import annotations

import math

import pytest

from uniqc.qem import zne as zne_module
from uniqc.qem.zne import ZNE


def _resolve(*names: str):
    """Return the first attribute on :mod:`zne_module` matching ``names``."""
    for name in names:
        if hasattr(zne_module, name):
            return getattr(zne_module, name)
    return None


def test_zne_placeholder_raises_not_implemented() -> None:
    """``ZNE(...)`` is documented as not-yet-implemented; lock that in."""
    with pytest.raises(NotImplementedError):
        ZNE()


def test_extrapolation_invalid_depth_raises() -> None:
    """A ZNE extrapolator must reject scale arrays with fewer than 2 points.

    With only a single observation there is no slope to fit, so any
    correct implementation should raise (typically ``ValueError``).
    Until ``extrapolate`` exists this test self-skips so it surfaces
    automatically the moment the API lands.
    """
    extrapolate = _resolve("extrapolate", "zne_extrapolate", "richardson_extrapolation")
    if extrapolate is None:
        pytest.skip("zne.extrapolate is not implemented yet (placeholder module)")
    with pytest.raises((ValueError, TypeError)):
        extrapolate([1.0], [0.5])  # type: ignore[misc]


def test_linear_extrapolation_matches_analytic() -> None:
    """Linear fit on ``(scale, energy) = (1,1.0), (2,1.5), (3,2.0)``.

    The line is ``E = 0.5*scale + 0.5`` so the zero-noise intercept is
    exactly ``0.5``. This pins the behaviour of any linear ZNE method.
    """
    linear = _resolve("linear_extrapolation", "linear", "extrapolate_linear")
    if linear is None:
        pytest.skip("Linear ZNE extrapolation is not implemented yet")
    result = linear([1.0, 2.0, 3.0], [1.0, 1.5, 2.0])  # type: ignore[misc]
    assert math.isclose(float(result), 0.5, abs_tol=1e-9)


def test_richardson_recovers_exact_for_polynomial() -> None:
    """Richardson on four points sampling ``p(s) = 1 + 0.1 s + 0.01 s²``.

    Richardson extrapolation of a polynomial of degree ≤ ``n-1`` over
    ``n`` scale factors recovers the constant term exactly. With
    scales ``[1,2,3,4]`` and the quadratic above the zero-noise value
    is exactly ``1.0``.
    """
    richardson = _resolve("richardson_extrapolation", "richardson", "extrapolate_richardson")
    if richardson is None:
        pytest.skip("Richardson ZNE extrapolation is not implemented yet")

    scales = [1.0, 2.0, 3.0, 4.0]
    energies = [1.0 + 0.1 * s + 0.01 * s * s for s in scales]
    result = richardson(scales, energies)  # type: ignore[misc]
    assert math.isclose(float(result), 1.0, abs_tol=1e-9)


def test_exponential_decay_extrapolates_to_intercept() -> None:
    """Exponential fit on ``E(s) = 2.0 - exp(-0.5 s)`` should give ≈ 1.0.

    The asymptotic value as ``s → 0`` is ``2.0 - 1.0 = 1.0``; the
    sampled points are chosen so the closed-form fit is unambiguous.
    """
    exponential = _resolve("exponential_extrapolation", "exponential", "extrapolate_exponential")
    if exponential is None:
        pytest.skip("Exponential ZNE extrapolation is not implemented yet")

    scales = [1.0, 2.0, 3.0, 4.0]
    energies = [2.0 - math.exp(-0.5 * s) for s in scales]
    result = exponential(scales, energies)  # type: ignore[misc]
    assert math.isclose(float(result), 1.0, abs_tol=1e-3)
