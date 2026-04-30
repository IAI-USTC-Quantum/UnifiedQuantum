"""Chip characterization service.

Fetches per-chip calibration data (per-qubit T1/T2, gate fidelities, readout
errors, connectivity) from each quantum cloud platform and returns a unified
:class:`~uniqc.cli.chip_info.ChipCharacterization`.

Usage
-----
::

    from uniqc.cli.chip_service import fetch_chip_characterization
    chip = fetch_chip_characterization("wuyuan:d5", "originq")
    chip = fetch_chip_characterization("ibm:sherbrooke", "ibm")

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from uniqc.backend_info import Platform
from uniqc.cli.chip_cache import get_chip, save_chip

if TYPE_CHECKING:
    from uniqc.cli.chip_info import ChipCharacterization


def fetch_chip_characterization(
    backend_name: str,
    platform: Platform,
    force_refresh: bool = False,
) -> ChipCharacterization | None:
    """Fetch chip characterization for a named backend.

    Parameters
    ----------
    backend_name:
        Bare backend name as reported by the platform, e.g. ``"wuyuan:d5"``
        (OriginQ), ``"ScQ-P18"`` (Quafu), ``"ibm-sherbrooke"`` (IBM).
    platform:
        One of :attr:`~uniqc.backend_info.Platform.ORIGINQ`,
        :attr:`~uniqc.backend_info.Platform.QUAFU`,
        :attr:`~uniqc.backend_info.Platform.IBM`.
    force_refresh:
        If False (the default), return cached data when available.
        If True, always re-fetch from the platform API.

    Returns
    -------
    ChipCharacterization or None
        None is returned when the platform adapter is unavailable (e.g. no
        credentials configured) or when the backend name is not found.
    """
    # Try cache first (unless force_refresh)
    if not force_refresh:
        cached = get_chip(platform, backend_name)
        if cached is not None:
            return cached

    # Dispatch to platform-specific adapter
    if platform == Platform.ORIGINQ:
        chip = _fetch_originq(backend_name)
    elif platform == Platform.QUAFU:
        chip = _fetch_quafu(backend_name)
    elif platform == Platform.IBM:
        chip = _fetch_ibm(backend_name)
    else:
        chip = None

    if chip is not None:
        save_chip(chip)

    return chip


# ---------------------------------------------------------------------------
# Platform-specific fetchers
# ---------------------------------------------------------------------------

def _fetch_originq(backend_name: str):
    """Fetch chip characterization from OriginQ Cloud."""
    try:
        from uniqc.task.adapters.originq_adapter import OriginQAdapter
    except (ImportError, Exception):
        return None

    try:
        adapter = OriginQAdapter()
    except (ImportError, Exception):
        return None

    if not adapter.is_available():
        return None

    try:
        return adapter.get_chip_characterization(backend_name)
    except Exception:
        return None


def _fetch_quafu(backend_name: str):
    """Fetch chip characterization from Quafu."""
    try:
        from uniqc.task.adapters.quafu_adapter import QuafuAdapter
    except (ImportError, Exception):
        return None

    try:
        adapter = QuafuAdapter()
    except (ImportError, Exception):
        return None

    if not adapter.is_available():
        return None

    try:
        return adapter.get_chip_characterization(backend_name)
    except Exception:
        return None


def _fetch_ibm(backend_name: str):
    """Fetch chip characterization from IBM Quantum."""
    try:
        from uniqc.task.adapters.ibm_adapter import IBMAdapter
    except (ImportError, Exception):
        return None

    try:
        adapter = IBMAdapter()
    except (ImportError, Exception):
        return None

    if not adapter.is_available():
        return None

    try:
        return adapter.get_chip_characterization(backend_name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Multi-chip fetchers (used by CLI update command)
# ---------------------------------------------------------------------------

def fetch_all_chips(
    platform: Platform | None = None,
    force_refresh: bool = True,
) -> list[ChipCharacterization]:
    """Fetch characterization for all backends of one or all platforms.

    Used by ``uniqc chip update --platform``.
    """
    from uniqc.backend_registry import fetch_all_backends

    results: list[ChipCharacterization] = []
    all_backends = fetch_all_backends() if platform is None else {}

    if platform is not None:
        from uniqc.backend_registry import fetch_platform_backends
        backends, _ = fetch_platform_backends(platform)
        if backends:
            all_backends[platform] = backends
    else:
        all_backends = fetch_all_backends()

    for plat, backends in all_backends.items():
        for backend in backends:
            if backend.is_simulator:
                continue
            chip = fetch_chip_characterization(backend.name, plat, force_refresh=force_refresh)
            if chip is not None:
                results.append(chip)

    return results
