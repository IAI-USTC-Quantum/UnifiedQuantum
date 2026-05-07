"""Zero-Noise Extrapolation (ZNE) — placeholder.

ZNE is on the QEM roadmap but not yet implemented.
TODO: implement gate-folding noise scaling + Richardson / exponential extrapolation
and integrate with :class:`uniqc.backend_adapter.task.result_types.UnifiedResult`
in the same pipeline style as :class:`uniqc.qem.M3Mitigator.apply`.
"""

from __future__ import annotations

__all__ = ["ZNE"]


class ZNE:
    """Zero-Noise Extrapolation mitigator (not yet implemented)."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: D401, ARG002
        raise NotImplementedError(
            "ZNE (Zero-Noise Extrapolation) is not yet implemented in uniqc. "
            "Tracking issue: see uniqc-report.md (E-U4). "
            "For now, use M3Mitigator / ReadoutEM for readout error mitigation."
        )
