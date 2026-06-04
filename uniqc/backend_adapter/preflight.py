"""Backend preflight: hard checks before running anything on a backend.

This module enforces a strict policy before any execution path that
talks to a real provider (or to a `dummy:<provider>:<chip>` noisy
simulator that depends on real provider data):

1. **Required dependency installed**. If a backend identifier names
   a provider whose SDK is missing, raise
   :class:`MissingDependencyError` with a precise install hint.
2. **Chip characterization cache present and fresh**. For backends
   that carry a `<provider>:<chip>` tag, look up the cached
   :class:`ChipCharacterization`. If absent or older than
   ``max_age_hours``, attempt to refresh via the provider SDK. On
   refresh failure, raise the underlying error verbatim.
3. **No silent fallbacks**. There is no "fall back to whatever cache
   we have lying around" path: the pipeline either has the data the
   backend identifier claims or it stops.

Backend identifier grammar
--------------------------
``local``                                   pure local simulator (no chip data)
``local:simulator``                         alias of ``local``
``dummy:local:simulator``                   alias of ``local``
``dummy:local:virtual-line-N``              line-topology local simulator
``dummy:local:virtual-grid-RxC``            grid-topology local simulator
``dummy:local:mps-linear-N[:k=v...]``       MPS local simulator
``dummy:<provider>:<chip>``                 noisy local sim using provider chip data
``<provider>:<chip>``                       direct submission to the provider
``<provider>``                              provider with default chip
"""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path
from typing import Any

from uniqc.backend_adapter.backend_info import Platform
from uniqc.backend_adapter.task.optional_deps import (
    MissingDependencyError,
    check_pyqpanda3,
    check_qiskit,
    check_quafu,
    check_quark,
    check_uniqc_cpp,
)

__all__ = [
    "BackendTarget",
    "MissingDependencyError",
    "BackendPreflightError",
    "parse_backend_target",
    "ensure_backend_ready",
    "has_provider_credentials",
    "PROVIDER_INSTALL_HINTS",
]


class BackendPreflightError(RuntimeError):
    """Raised when a backend's pre-execution checks fail.

    Examples: chip cache cannot be fetched, refresh failed because the
    provider SDK threw, etc. The underlying cause is chained via
    ``__cause__`` so callers can inspect it.
    """


PROVIDER_INSTALL_HINTS: dict[str, str] = {
    "originq": (
        "OriginQ backends require the pyqpanda3 SDK. Install with:\n"
        "  pip install pyqpanda3>=0.3.5\n"
        "or, for the curated extras set:\n"
        "  pip install 'unified-quantum[originq]'"
    ),
    "ibm": ("IBM backends require qiskit + qiskit_ibm_runtime. Install with:\n  pip install 'unified-quantum[ibm]'"),
    "quafu": (
        "The Quafu adapter is deprecated. Install pyquafu directly only "
        "if you really need it:\n  pip install pyquafu  (warning: "
        "pyquafu requires numpy<2)"
    ),
    "quark": (
        "Quark backends require QuarkStudio. Install with:\n"
        "  pip install QuarkStudio  (the [quark] extra is also available "
        "if QuarkStudio is on a private index)"
    ),
}


# ---------------------------------------------------------------------------
# Credential / config detection
# ---------------------------------------------------------------------------


def has_provider_credentials(provider: str) -> bool:
    """Return True iff the provider has its API token / config set up.

    Uses the standard ``uniqc.config.load_<provider>_config()`` loaders;
    they raise when credentials are missing. Returns False for unknown
    providers (no credentials = nothing to detect). Does *not* hit the
    network.
    """
    provider = provider.lower()
    try:
        if provider == "originq":
            from uniqc.config import load_originq_config

            load_originq_config()
            return True
        if provider == "quafu":
            from uniqc.config import load_quafu_config

            load_quafu_config()
            return True
        if provider == "quark":
            from uniqc.config import load_quark_config

            load_quark_config()
            return True
        if provider == "ibm":
            from uniqc.config import load_ibm_config

            load_ibm_config()
            return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# Backend identifier parsing
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class BackendTarget:
    """Parsed backend identifier.

    ``kind`` is one of:
      - ``"local"``: pure local simulator (no provider data)
      - ``"local_topology"``: local sim with synthetic virtual topology
      - ``"local_mps"``: local MPS simulator on a linear chain
      - ``"dummy_provider"``: noisy local sim using provider chip data
      - ``"provider"``: direct submission to a real provider

    For ``dummy_provider`` and ``provider``, ``provider`` and
    ``chip_name`` are populated.
    """

    raw: str
    kind: str
    provider: str | None = None
    chip_name: str | None = None
    topology_spec: str | None = None
    mps_kwargs: dict[str, Any] | None = None

    @property
    def needs_provider_sdk(self) -> bool:
        return self.kind in ("dummy_provider", "provider")


def _is_topology_suffix(suffix: str) -> bool:
    if suffix.startswith(("virtual-line-", "virtual-grid-")):
        return True
    if suffix.startswith(("mps-linear-", "mps:linear-")):
        return True
    return False


def _canonical_topology_suffix(suffix: str) -> str:
    """Map any legacy MPS form (``mps:linear-N``) to the canonical hyphen form."""
    if suffix.startswith("mps:linear-"):
        return "mps-linear-" + suffix[len("mps:linear-") :]
    return suffix


def parse_backend_target(name: str) -> BackendTarget:
    """Parse a backend identifier into a :class:`BackendTarget`.

    Raises ``ValueError`` for malformed identifiers. The bare aliases
    ``"dummy"`` and ``"dummy:local"`` are no longer accepted — callers
    must use the canonical ``"dummy:local:simulator"`` form (or just
    ``"local"``).
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "Backend identifier must be a non-empty string. Examples: "
            "'local', 'dummy:local:simulator', 'dummy:originq:WK_C180', "
            "'originq:WK_C180'."
        )
    raw = name.strip()

    # Pure local aliases
    if raw in ("local", "local:simulator", "dummy:local:simulator"):
        return BackendTarget(raw=raw, kind="local")
    if raw in ("dummy", "dummy:local"):
        raise ValueError(
            f"Backend identifier {raw!r} is not allowed. Use the canonical "
            "'dummy:local:simulator' form (or 'local') for the unconstrained "
            "noiseless simulator. For chip-noisy simulation, pass "
            "'dummy:<provider>:<chip>' (e.g. 'dummy:originq:WK_C180')."
        )

    # dummy:local:<topology-spec>
    if raw.startswith("dummy:local:"):
        suffix = raw[len("dummy:local:") :]
        if suffix in ("simulator", ""):
            return BackendTarget(raw=raw, kind="local")
        if suffix.startswith(("virtual-line-", "virtual-grid-")):
            return BackendTarget(
                raw=raw,
                kind="local_topology",
                topology_spec=suffix,
            )
        if suffix.startswith("mps-linear-"):
            return BackendTarget(
                raw=raw,
                kind="local_mps",
                topology_spec=suffix,
            )
        # Legacy ``mps:linear-`` (colon separator) → reject with migration hint.
        if suffix.startswith("mps:linear-"):
            canonical = f"dummy:local:{_canonical_topology_suffix(suffix)}"
            raise ValueError(
                f"Backend identifier {raw!r} uses the legacy 'mps:linear-' "
                f"form. Use the canonical {canonical!r} form instead."
            )
        # Unknown local sub-kind → treat as configuration error.
        raise ValueError(
            f"Unknown local backend sub-identifier: {suffix!r}. Supported: "
            "simulator, virtual-line-N, virtual-grid-RxC, mps-linear-N."
        )

    # Backwards-compat: legacy 'dummy:virtual-line-N' / 'dummy:mps:linear-N' /
    # 'dummy:mps-linear-N' are no longer accepted — the canonical form is
    # 'dummy:local:...'.
    if raw.startswith("dummy:") and _is_topology_suffix(raw.split(":", 1)[1]):
        suffix = raw.split(":", 1)[1]
        canonical = f"dummy:local:{_canonical_topology_suffix(suffix)}"
        raise ValueError(f"Backend identifier {raw!r} is not allowed. Use the canonical {canonical!r} form instead.")

    # dummy:<provider>:<chip>
    if raw.startswith("dummy:"):
        rest = raw[len("dummy:") :]
        parts = rest.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Malformed dummy backend identifier: {raw!r}. Expected "
                "'dummy:local:simulator', 'dummy:local:virtual-line-N', "
                "or 'dummy:<provider>:<chip>'."
            )
        provider = parts[0].lower()
        chip_name = parts[1]
        return BackendTarget(
            raw=raw,
            kind="dummy_provider",
            provider=provider,
            chip_name=chip_name,
        )

    # <provider>:<chip>  or bare <provider>
    parts = raw.split(":", 1)
    provider = parts[0].lower()
    chip_name = parts[1] if len(parts) == 2 else None
    return BackendTarget(
        raw=raw,
        kind="provider",
        provider=provider,
        chip_name=chip_name,
    )


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------


def _check_provider_dep(provider: str) -> None:
    """Raise :class:`MissingDependencyError` if the provider's SDK is missing."""
    provider = provider.lower()
    install_hint = PROVIDER_INSTALL_HINTS.get(provider)

    if provider == "originq":
        if not check_pyqpanda3():
            raise MissingDependencyError("pyqpanda3", install_hint=install_hint)
        return
    if provider == "ibm":
        if not check_qiskit():
            raise MissingDependencyError(
                "qiskit + qiskit_ibm_runtime",
                install_hint=install_hint,
            )
        return
    if provider == "quafu":
        if not check_quafu():
            raise MissingDependencyError("quafu", install_hint=install_hint)
        return
    if provider == "quark":
        if not check_quark():
            raise MissingDependencyError("quark", install_hint=install_hint)
        return
    # Unknown provider — refuse rather than silently doing nothing.
    raise BackendPreflightError(
        f"Unknown provider '{provider}'. Known providers: "
        f"{sorted(PROVIDER_INSTALL_HINTS.keys())}. Pass an explicit "
        "backend identifier from one of those, or use 'local' for a "
        "pure local simulator."
    )


def _require_local_simulator() -> None:
    """Local simulator paths still need the C++ extension."""
    if not check_uniqc_cpp():
        raise MissingDependencyError(
            "uniqc_cpp",
            install_hint=(
                "The local simulator (uniqc_cpp C++ extension) is not "
                "available. Reinstall unified-quantum from a wheel that "
                "includes the binary extension, or build from source."
            ),
        )


# ---------------------------------------------------------------------------
# Chip cache TTL handling
# ---------------------------------------------------------------------------


def _chip_age_hours(path: Path) -> float | None:
    if not path.exists():
        return None
    return (time.time() - path.stat().st_mtime) / 3600.0


def _refresh_chip(provider: str, chip_name: str) -> Any:
    """Call the provider SDK to refresh a chip's characterization cache.

    Raises :class:`BackendPreflightError` (with a chained cause) on
    any failure — provider unreachable, auth missing, chip not found,
    SDK error, etc.
    """
    if provider == "originq":
        try:
            from uniqc.backend_adapter.task.adapters.originq_adapter import (
                OriginQAdapter,
            )
            from uniqc.cli.chip_cache import save_chip
        except Exception as exc:
            raise BackendPreflightError(
                f"originq SDK import failed while refreshing chip characterization for {chip_name!r}: {exc}"
            ) from exc
        try:
            adapter = OriginQAdapter()
            chip = adapter.get_chip_characterization(chip_name)
        except Exception as exc:
            raise BackendPreflightError(
                f"OriginQ refresh failed for {chip_name!r}: {exc}. "
                "Check UNIQC_ORIGINQ_TOKEN, network connectivity, and "
                "that the chip name is valid."
            ) from exc
        if chip is None:
            raise BackendPreflightError(
                f"OriginQ returned no characterization for {chip_name!r}. "
                "Verify the chip name (e.g. 'WK_C180') is currently online."
            )
        save_chip(chip)
        return chip

    if provider == "ibm":
        try:
            from uniqc.backend_adapter.task.adapters.ibm_adapter import IBMAdapter
            from uniqc.cli.chip_cache import save_chip
        except Exception as exc:
            raise BackendPreflightError(
                f"IBM SDK import failed while refreshing chip characterization for {chip_name!r}: {exc}"
            ) from exc
        try:
            adapter = IBMAdapter()
            chip = adapter.get_chip_characterization(chip_name)
        except Exception as exc:
            raise BackendPreflightError(
                f"IBM refresh failed for {chip_name!r}: {exc}. "
                "Check IBM Quantum credentials, network connectivity, and "
                "that the backend name is valid (e.g. 'ibm_fez')."
            ) from exc
        if chip is None:
            raise BackendPreflightError(
                f"IBM returned no characterization for {chip_name!r}. "
                "Verify the backend name is reachable from your IBM account."
            )
        save_chip(chip)
        return chip

    if provider == "quafu":
        try:
            from uniqc.backend_adapter.task.adapters.quafu_adapter import QuafuAdapter
            from uniqc.cli.chip_cache import save_chip
        except Exception as exc:
            raise BackendPreflightError(
                f"Quafu SDK import failed while refreshing chip characterization for {chip_name!r}: {exc}"
            ) from exc
        try:
            adapter = QuafuAdapter()
            chip = adapter.get_chip_characterization(chip_name)
        except Exception as exc:
            raise BackendPreflightError(
                f"Quafu refresh failed for {chip_name!r}: {exc}. "
                "Check UNIQC_QUAFU_TOKEN, network connectivity, and "
                "that the chip name is valid."
            ) from exc
        if chip is None:
            raise BackendPreflightError(
                f"Quafu returned no characterization for {chip_name!r}. "
                "Verify the chip name (e.g. 'ScQ-P18') is currently online."
            )
        save_chip(chip)
        return chip

    if provider == "quark":
        try:
            from uniqc.backend_adapter.task.adapters.quark_adapter import QuarkAdapter
            from uniqc.cli.chip_cache import save_chip
        except Exception as exc:
            raise BackendPreflightError(
                f"Quark SDK import failed while refreshing chip characterization for {chip_name!r}: {exc}"
            ) from exc
        try:
            adapter = QuarkAdapter()
            chip = adapter.get_chip_characterization(chip_name)
        except Exception as exc:
            raise BackendPreflightError(
                f"Quark refresh failed for {chip_name!r}: {exc}. "
                "Check QuarkStudio configuration and that the chip name is valid."
            ) from exc
        if chip is None:
            raise BackendPreflightError(
                f"Quark returned no characterization for {chip_name!r}. Verify the chip name is currently online."
            )
        save_chip(chip)
        return chip

    raise BackendPreflightError(
        f"Cache refresh not implemented for provider {provider!r}. "
        "Run the provider's CLI 'uniqc backend chip-display "
        f"{provider}/<chip> --update' from a host with the SDK installed, "
        "or supply 'chip_characterization' explicitly."
    )


def _load_chip_cache(provider: str, chip_name: str) -> tuple[Any | None, Path]:
    """Resolve the cache file path and read whatever's there (or None)."""
    from uniqc.backend_adapter.dummy_backend import _find_cached_chip
    from uniqc.cli.chip_cache import _chip_path

    try:
        plat = Platform(provider)
    except ValueError as exc:
        raise BackendPreflightError(f"Unknown provider '{provider}'. Known: {[p.value for p in Platform]}.") from exc

    chip = _find_cached_chip(plat, chip_name)
    path = _chip_path(None, plat, chip.chip_name if chip else chip_name)
    return chip, path


# ---------------------------------------------------------------------------
# Public preflight entry point
# ---------------------------------------------------------------------------


def ensure_backend_ready(
    backend: str,
    *,
    max_age_hours: float | None = None,
    refresh: bool | None = None,
) -> Any | None:
    """Perform every pre-execution check for ``backend`` and return chip data.

    Args:
        backend: Backend identifier (see module docstring grammar).
        max_age_hours: If set and the chip cache is older than this,
            attempt a refresh. ``None`` (default) disables age-based
            refresh — only missing-cache triggers a refresh attempt.
        refresh: ``True`` to force-refresh, ``False`` to forbid
            refresh, ``None`` (default) to follow the policy above.

    Returns:
        The loaded :class:`ChipCharacterization` for any backend that
        carries a ``<provider>:<chip>`` tag, otherwise ``None`` for
        pure local backends.

    Raises:
        MissingDependencyError: Required SDK / extension missing.
        BackendPreflightError: Cache refresh failed, or any other
            pre-execution check tripped.
        ValueError: Malformed backend identifier.
    """
    target = parse_backend_target(backend)

    # Pure local simulator path.
    if target.kind in ("local", "local_topology", "local_mps"):
        _require_local_simulator()
        return None

    if target.provider is None:
        raise BackendPreflightError(
            f"Backend {target.raw!r} parses as kind={target.kind!r} "
            "but lacks a provider. This is a bug — please report it."
        )

    # Provider-backed dummy (``dummy:<provider>:<chip>``) runs entirely
    # locally using the cached chip topology and the local C++ simulator.
    # It only needs the cloud SDK if we have to refresh the chip cache
    # (handled below). Skip the SDK preflight here so that environments
    # without the cloud SDK installed — for example, Python 3.14 where
    # the ``[originq]`` / ``[quark]`` extras are gated out — can still
    # exercise chip-backed dummy paths.
    if target.kind == "dummy_provider":
        _require_local_simulator()
    else:
        _check_provider_dep(target.provider)

    if target.chip_name is None:
        # Bare provider with no chip name — nothing to cache.
        return None

    chip, path = _load_chip_cache(target.provider, target.chip_name)
    age_h = _chip_age_hours(path) if path.exists() else None
    needs_refresh = (
        refresh is True
        or chip is None
        or (refresh is not False and max_age_hours is not None and age_h is not None and age_h > max_age_hours)
    )
    if not needs_refresh:
        return chip

    if refresh is False:
        raise BackendPreflightError(
            f"Chip cache for {target.provider}:{target.chip_name} is "
            f"{'missing' if chip is None else f'stale ({age_h:.1f}h old)'} "
            "and refresh is disabled."
        )
    # A refresh from the live provider requires the cloud SDK. For
    # provider-backed dummy we skipped the SDK check above, so re-check
    # here before we try to refresh.
    if target.kind == "dummy_provider":
        _check_provider_dep(target.provider)
    return _refresh_chip(target.provider, target.chip_name)
