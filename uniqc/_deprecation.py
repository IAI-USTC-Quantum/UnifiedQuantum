"""Centralised deprecation helpers for UnifiedQuantum.

Every public API that is on the deprecation track to be **removed (or whose
backwards compatibility will no longer be guaranteed) in uniqc 0.1.0** should
emit its :class:`DeprecationWarning` through one of the helpers in this
module. Doing so guarantees:

* A consistent, machine-greppable phrase — every message contains the
  literal substring ``"uniqc 0.1.0"`` so that downstream tooling
  (CI, doc-checkers, user scripts) can detect the cliff version reliably.
* A single edit point if the cliff version is ever revisited.

See ``docs/source/7_releases/deprecation_policy.md`` for the project-wide
deprecation policy (the 0.0.x → 0.1.0 compatibility cliff).
"""

from __future__ import annotations

import warnings
from typing import Final

#: The release in which all currently-deprecated APIs will be removed
#: (or whose compatibility will no longer be guaranteed).
REMOVAL_VERSION: Final[str] = "0.1.0"


def _trailer(replacement: str | None) -> str:
    """Return the standard "will be removed" trailer.

    Examples
    --------
    >>> _trailer("get_simulator()")
    'It will be removed in uniqc 0.1.0; use `get_simulator()` instead.'
    >>> _trailer(None)
    'It will be removed in uniqc 0.1.0.'
    """
    base = f"It will be removed in uniqc {REMOVAL_VERSION}"
    if replacement:
        return f"{base}; use `{replacement}` instead."
    return f"{base}."


def warn_removed_in_0_1_0(
    name: str,
    *,
    replacement: str | None = None,
    detail: str | None = None,
    stacklevel: int = 2,
) -> None:
    """Emit a :class:`DeprecationWarning` for an API removed in uniqc 0.1.0.

    Args:
        name: The qualified, user-facing name of the deprecated API
            (e.g. ``"IBMAdapter"`` or ``"qft_circuit(circuit, ...)"``).
            This appears at the start of the message verbatim.
        replacement: Optional one-line replacement hint. When provided,
            it is rendered as ``"; use ``<replacement>`` instead."``.
        detail: Optional extra sentence appended before the trailer
            (use for context like "the [quafu] extra has been removed").
        stacklevel: Forwarded to :func:`warnings.warn`. The default of 2
            attributes the warning to the caller of the deprecated API.
            Pass ``3`` from a helper that itself wraps the deprecated API.

    Example
    -------
    >>> warn_removed_in_0_1_0("get_backend()", replacement="get_simulator()")
    # → DeprecationWarning: "get_backend() is deprecated. It will be
    #    removed in uniqc 0.1.0; use `get_simulator()` instead."
    """
    parts = [f"{name} is deprecated."]
    if detail:
        parts.append(detail.rstrip("."))
    parts.append(_trailer(replacement))
    message = " ".join(parts)
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)
