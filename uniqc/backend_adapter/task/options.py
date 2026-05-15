"""Typed backend options for UnifiedQuantum task submission.

This module provides a typed, platform-agnostic interface for specifying
backend-specific options when calling :func:`submit_task` and
:func:`submit_batch`. The existing ``**kwargs`` interface remains fully
supported; :class:`BackendOptions` is an additive enhancement.

Example
-------
Using the typed interface::

    from uniqc.backend_adapter.task.options import OriginQOptions
    from uniqc import submit_task

    opts = OriginQOptions(backend_name="originq:WK_C180", circuit_optimize=True)
    task_id = submit_task(circuit, "originq", shots=1000, options=opts)

Equivalent using the legacy interface::

    task_id = submit_task(circuit, "originq", shots=1000,
                          backend_name="originq:WK_C180", circuit_optimize=True)
"""

from __future__ import annotations

__all__ = [
    "BackendOptions",
    "OriginQOptions",
    "QuafuOptions",
    "QuarkOptions",
    "IBMOptions",
    "DummyOptions",
    "UnifiedOptions",
    "BackendOptionsFactory",
    "BackendOptionsError",
]

import dataclasses
import warnings
from typing import Any

from uniqc.backend_adapter.backend_info import Platform
from uniqc.exceptions import BackendOptionsError  # noqa: F401 — re-export


@dataclasses.dataclass
class BackendOptions:
    """Base class for platform-specific backend options.

    Subclasses define the options that are relevant for a particular platform.
    The ``platform`` field identifies which backend these options target.

    Parameters
    ----------
    platform :
        The target platform.
    shots :
        Number of measurement shots (default: 1000).
    """

    platform: Platform
    shots: int = 1000

    def to_kwargs(self) -> dict[str, Any]:
        """Render the options as a ``**kwargs`` dict for :func:`submit_task`.

        Subclasses must implement this method to produce the kwargs shape
        expected by the underlying adapter.
        """
        raise NotImplementedError

    @classmethod
    def from_kwargs(
        cls, platform: str, kwargs: dict[str, Any] | None = None, **extra: Any
    ) -> BackendOptions:
        """Construct the appropriate :class:`BackendOptions` from a ``**kwargs`` dict.

        This is a convenience alias for :meth:`BackendOptionsFactory.from_kwargs`.
        """
        return BackendOptionsFactory.from_kwargs(platform, kwargs, **extra)


@dataclasses.dataclass
class OriginQOptions(BackendOptions):
    """Options for OriginQ Cloud backends.

    Parameters
    ----------
    backend_name : str
        Full OriginQ backend name, e.g. ``"originq:WK_C180"``.
        Default: ``"originq:WK_C180"``.
    circuit_optimize : bool
        Enable circuit optimisation on the backend. Default: ``True``.
    measurement_amend : bool
        Enable measurement error mitigation. Default: ``False``.
    auto_mapping : bool
        Enable automatic qubit mapping. Default: ``False``.
    """

    platform: dataclasses.InitVar[Platform] = dataclasses.field(default=Platform.ORIGINQ, repr=False)
    backend_name: str = "originq:WK_C180"
    circuit_optimize: bool = True
    measurement_amend: bool = False
    auto_mapping: bool = False

    def to_kwargs(self) -> dict[str, Any]:
        return {
            "backend_name": self.backend_name,
            "circuit_optimize": self.circuit_optimize,
            "measurement_amend": self.measurement_amend,
            "auto_mapping": self.auto_mapping,
        }


@dataclasses.dataclass
class QuafuOptions(BackendOptions):
    """Options for Quafu (ScQ) backends.

    Parameters
    ----------
    chip_id : str
        Quafu chip identifier, e.g. ``"ScQ-P18"``. Default: ``"ScQ-P18"``.
    auto_mapping : bool
        Enable automatic qubit mapping. Default: ``True``.
    task_name : str | None
        Optional task name for the server-side task list.
    group_name : str | None
        Optional group name for batch tracking.
    wait : bool
        Block until server acknowledges receipt. Default: ``False``.
    """

    platform: dataclasses.InitVar[Platform] = dataclasses.field(default=Platform.QUAFU, repr=False)
    chip_id: str = "ScQ-P18"
    auto_mapping: bool = True
    task_name: str | None = None
    group_name: str | None = None
    wait: bool = False

    def to_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "chip_id": self.chip_id,
            "auto_mapping": self.auto_mapping,
        }
        if self.task_name is not None:
            kwargs["task_name"] = self.task_name
        if self.group_name is not None:
            kwargs["group_name"] = self.group_name
        if self.wait:
            kwargs["wait"] = self.wait
        return kwargs


@dataclasses.dataclass
class QuarkOptions(BackendOptions):
    """Options for QuarkStudio / Quafu-SQC backends.

    Parameters
    ----------
    chip_id : str
        QuarkStudio chip name, e.g. ``"Baihua"`` or ``"Dongling"``.
    task_name : str | None
        Optional server-side task name.
    compile : bool
        Whether QuarkStudio should compile the OpenQASM2 circuit. Default: True.
    compiler : str | None
        Optional compiler backend: ``"quarkcircuit"``, ``"qsteed"``, ``"qiskit"``, or None.
    correct : bool | None
        Optional readout correction flag.
    open_dd : str | None
        Optional dynamical decoupling mode such as ``"XY4"`` or ``"CPMG"``.
    target_qubits : list[int] | None
        Optional target qubits passed in the QuarkStudio task options.
    """

    platform: dataclasses.InitVar[Platform] = dataclasses.field(default=Platform.QUARK, repr=False)
    chip_id: str = "Baihua"
    task_name: str | None = None
    compile: bool = True
    compiler: str | None = None
    correct: bool | None = None
    open_dd: str | None = None
    target_qubits: list[int] | None = None

    def to_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "chip_id": self.chip_id,
            "compile": self.compile,
        }
        if self.task_name is not None:
            kwargs["task_name"] = self.task_name
        if self.compiler is not None:
            kwargs["compiler"] = self.compiler
        if self.correct is not None:
            kwargs["correct"] = self.correct
        if self.open_dd is not None:
            kwargs["open_dd"] = self.open_dd
        if self.target_qubits is not None:
            kwargs["target_qubits"] = self.target_qubits
        return kwargs


@dataclasses.dataclass
class IBMOptions(BackendOptions):
    """Options for IBM Quantum backends.

    Parameters
    ----------
    chip_id : str | None
        IBM backend name (e.g. ``"ibm_kyoto"``). Optional; if ``None`` the
        IBM adapter's default backend is used.
    auto_mapping : bool
        Enable automatic qubit mapping. Default: ``True``.
    circuit_optimize : bool
        Enable circuit optimisation. Default: ``True``.
    task_name : str | None
        Optional task name for server-side tracking.
    """

    platform: dataclasses.InitVar[Platform] = dataclasses.field(default=Platform.IBM, repr=False)
    chip_id: str | None = None
    auto_mapping: bool = True
    circuit_optimize: bool = True
    task_name: str | None = None

    def to_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "auto_mapping": self.auto_mapping,
            "circuit_optimize": self.circuit_optimize,
        }
        if self.chip_id is not None:
            kwargs["chip_id"] = self.chip_id
        if self.task_name is not None:
            kwargs["task_name"] = self.task_name
        return kwargs


@dataclasses.dataclass
class DummyOptions(BackendOptions):
    """Options for the local dummy simulator.

    Parameters
    ----------
    noise_model : Any | None
        Optional noise model for noisy simulation.
        Supported keys: ``depol_1q``, ``depol_2q``, ``depol`` (fallback for both).
    chip_characterization : ChipCharacterization | None
        Chip characterization data. When provided, the simulator derives
        realistic noise parameters from per-qubit and per-pair calibration
        data (T1/T2, gate fidelities, readout errors).
        Cannot be used together with ``noise_model`` (noise_model takes precedence).
    available_qubits : int
        Number of qubits available in the dummy simulator. Default: 16.
    available_topology : list[list[int]] | None
        Connectivity graph as list of ``[u, v]`` edge pairs.
        If ``None``, all-to-all connectivity is assumed.
    """

    platform: dataclasses.InitVar[Platform] = dataclasses.field(default=Platform.DUMMY, repr=False)
    noise_model: Any = None
    chip_characterization: Any = None
    available_qubits: int = 16
    available_topology: list[list[int]] | None = None

    def to_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "available_qubits": self.available_qubits,
        }
        if self.noise_model is not None:
            kwargs["noise_model"] = self.noise_model
        if self.chip_characterization is not None:
            kwargs["chip_characterization"] = self.chip_characterization
        if self.available_topology is not None:
            kwargs["available_topology"] = self.available_topology
        return kwargs


@dataclasses.dataclass
class UnifiedOptions:
    """Cross-platform task-submission options.

    ``UnifiedOptions`` lets you write backend-agnostic submission code: pass
    the same instance to :func:`uniqc.submit_task` against any platform and
    uniqc translates the high-level intent (optimise, mitigate readout,
    auto-map qubits) into each platform's specific
    :class:`BackendOptions` payload.

    Translation table — ``warn`` / ``raise`` indicates the option is not
    supported on that platform; the behaviour is governed by ``strict``
    (default ``False`` → :func:`warnings.warn`; ``True`` → raise
    :class:`BackendOptionsError`):

    ===========================  ===================================  ========================  =========================  ====================================
    Unified option               OriginQ                              Quafu                     Quark                      IBM
    ===========================  ===================================  ========================  =========================  ====================================
    ``optimize_level=0``         ``circuit_optimize=False``           ignored (no knob)         ``compile=False``          ``circuit_optimize=False``
    ``optimize_level>=1``        ``circuit_optimize=True``            ``auto_mapping=True``     ``compile=True``           ``circuit_optimize=True``
    ``error_mitigation=True``    ``measurement_amend=True``           warn / raise              ``correct=True``           warn / raise
    ``auto_mapping=True``        ``auto_mapping=True``                ``auto_mapping=True``     warn / raise               ``auto_mapping=True``
    ``backend_name``             ``backend_name=...``                 ``chip_id=...``           ``chip_id=...``            ``chip_id=...``
    ``shots``                    forwarded                            forwarded                 forwarded                  forwarded
    ===========================  ===================================  ========================  =========================  ====================================

    Per-platform :class:`BackendOptions` instances remain a fully-supported
    "escape hatch" for platform-specific knobs that have no unified
    counterpart (Quark's ``open_dd``, Quafu's ``group_name``, IBM's
    ``task_name`` etc.).

    Parameters
    ----------
    optimize_level :
        Cross-platform optimisation strength.  ``0`` disables compilation /
        optimisation on every platform that exposes such a knob.  Any value
        ``>= 1`` enables it.  Higher integers are reserved for future use
        by platforms that distinguish multiple optimisation tiers; for now
        ``>= 1`` is treated identically across platforms.
    error_mitigation :
        Enable readout-error mitigation when the platform supports it.
    auto_mapping :
        Enable automatic logical-to-physical qubit mapping.
    shots :
        Number of measurement shots.  Forwarded verbatim.
    backend_name :
        Optional chip identifier.  Translated to the platform's native
        chip-selection key (``backend_name`` on OriginQ, ``chip_id``
        elsewhere).  When ``None`` the platform's default chip is used.
    strict :
        When ``True``, unsupported options raise
        :class:`BackendOptionsError`.  When ``False`` (default), they are
        emitted as :class:`UserWarning` and silently dropped.
    """

    optimize_level: int = 1
    error_mitigation: bool = False
    auto_mapping: bool = True
    shots: int = 1000
    backend_name: str | None = None
    strict: bool = False

    def _unsupported(self, option: str, platform: str) -> None:
        msg = (
            f"UnifiedOptions: option {option!r} is not supported on platform "
            f"{platform!r}; "
            f"{'raising as strict=True is set' if self.strict else 'silently ignored'}."
        )
        if self.strict:
            raise BackendOptionsError(msg)
        warnings.warn(msg, UserWarning, stacklevel=3)

    def to_platform_options(self, platform: str) -> "BackendOptions":
        """Translate to the platform-specific :class:`BackendOptions` subclass.

        Unknown platforms raise :class:`BackendOptionsError`.  Unsupported
        options trigger :func:`warnings.warn` (or
        :class:`BackendOptionsError` when ``strict=True``).
        """
        platform_lower = platform.lower()
        optimize = bool(self.optimize_level >= 1)

        if platform_lower == "originq":
            return OriginQOptions(
                shots=self.shots,
                backend_name=self.backend_name or "originq:WK_C180",
                circuit_optimize=optimize,
                measurement_amend=bool(self.error_mitigation),
                auto_mapping=bool(self.auto_mapping),
            )
        if platform_lower == "quafu":
            if self.error_mitigation:
                self._unsupported("error_mitigation", "quafu")
            return QuafuOptions(
                shots=self.shots,
                chip_id=self.backend_name or "ScQ-P18",
                auto_mapping=bool(self.auto_mapping or optimize),
            )
        if platform_lower == "quark":
            if self.auto_mapping:
                self._unsupported("auto_mapping", "quark")
            return QuarkOptions(
                shots=self.shots,
                chip_id=self.backend_name or "Baihua",
                compile=optimize,
                correct=bool(self.error_mitigation) or None,
            )
        if platform_lower == "ibm":
            if self.error_mitigation:
                self._unsupported("error_mitigation", "ibm")
            return IBMOptions(
                shots=self.shots,
                chip_id=self.backend_name,
                auto_mapping=bool(self.auto_mapping),
                circuit_optimize=optimize,
            )
        if platform_lower == "dummy":
            return DummyOptions(shots=self.shots)
        raise BackendOptionsError(
            f"UnifiedOptions: unknown platform {platform_lower!r}. "
            f"Available: ['originq', 'quafu', 'quark', 'ibm', 'dummy']"
        )

    def to_kwargs(self, platform: str) -> dict[str, Any]:
        """Render as a ``**kwargs`` dict for the given platform.

        Convenience shortcut for ``self.to_platform_options(platform).to_kwargs()``.
        """
        return self.to_platform_options(platform).to_kwargs()


class BackendOptionsFactory:
    """Factory for constructing :class:`BackendOptions` from various input forms.

    Supports three input forms:

    1. **BackendOptions instance** — returned unchanged.
    2. ``**kwargs`` dict — converted to the appropriate platform subclass.
    3. ``None`` — returns a default options object for the platform.

    Example
    -------
    >>> opts = BackendOptionsFactory.from_kwargs("originq", {"circuit_optimize": False})
    >>> type(opts).__name__
    'OriginQOptions'
    >>> opts.to_kwargs()["circuit_optimize"]
    False
    """

    _PLATFORM_MAP: dict[str, type[BackendOptions]] = {
        "originq": OriginQOptions,
        "quafu": QuafuOptions,
        "quark": QuarkOptions,
        "ibm": IBMOptions,
        "dummy": DummyOptions,
    }

    @classmethod
    def from_kwargs(
        cls,
        platform: str,
        kwargs: dict[str, Any] | None = None,
        **extra: Any,
    ) -> BackendOptions:
        """Construct the appropriate :class:`BackendOptions` from a ``**kwargs`` dict.

        Accepts both forms for backwards compatibility:

        * ``BackendOptionsFactory.from_kwargs("originq", {"shots": 100})``
        * ``BackendOptionsFactory.from_kwargs("originq", shots=100)``

        Parameters
        ----------
        platform :
            Platform name — one of ``"originq"``, ``"quafu"``, ``"ibm"``, ``"dummy"``.
        kwargs :
            Optional keyword arguments dict. Merged with any additional
            keyword arguments passed via ``**extra``.

        Returns
        -------
        BackendOptions
            The appropriate platform-specific subclass.

        Raises
        ------
        BackendOptionsError
            If the platform is unknown.
        """
        platform_lower = platform.lower()

        if platform_lower not in cls._PLATFORM_MAP:
            raise BackendOptionsError(
                f"Unknown platform {platform_lower!r}. Available: {list(cls._PLATFORM_MAP.keys())}"
            )

        if kwargs is None:
            kwargs = {}
        else:
            kwargs = dict(kwargs)  # Don't mutate caller's dict
        if extra:
            kwargs.update(extra)

        shots = kwargs.pop("shots", 1000)

        if platform_lower == "originq":
            return OriginQOptions(
                shots=shots,
                backend_name=kwargs.pop("backend_name", "originq:WK_C180"),
                circuit_optimize=kwargs.pop("circuit_optimize", True),
                measurement_amend=kwargs.pop("measurement_amend", False),
                auto_mapping=kwargs.pop("auto_mapping", False),
            )
        elif platform_lower == "quafu":
            return QuafuOptions(
                shots=shots,
                chip_id=kwargs.pop("chip_id", "ScQ-P18"),
                auto_mapping=kwargs.pop("auto_mapping", True),
                task_name=kwargs.pop("task_name", None),
                group_name=kwargs.pop("group_name", None),
                wait=kwargs.pop("wait", False),
            )
        elif platform_lower == "quark":
            return QuarkOptions(
                shots=shots,
                chip_id=kwargs.pop("chip_id", kwargs.pop("backend_name", kwargs.pop("chip", "Baihua"))),
                task_name=kwargs.pop("task_name", kwargs.pop("name", None)),
                compile=kwargs.pop("compile", True),
                compiler=kwargs.pop("compiler", None),
                correct=kwargs.pop("correct", None),
                open_dd=kwargs.pop("open_dd", None),
                target_qubits=kwargs.pop("target_qubits", None),
            )
        elif platform_lower == "ibm":
            return IBMOptions(
                shots=shots,
                chip_id=kwargs.pop("chip_id", None),
                auto_mapping=kwargs.pop("auto_mapping", True),
                circuit_optimize=kwargs.pop("circuit_optimize", True),
                task_name=kwargs.pop("task_name", None),
            )
        elif platform_lower == "dummy":
            return DummyOptions(
                shots=shots,
                noise_model=kwargs.pop("noise_model", None),
                chip_characterization=kwargs.pop("chip_characterization", None),
                available_qubits=kwargs.pop("available_qubits", 16),
                available_topology=kwargs.pop("available_topology", None),
            )
        # Should not reach here
        raise BackendOptionsError(f"Unknown platform: {platform_lower}")

    @classmethod
    def create_default(cls, platform: str) -> BackendOptions:
        """Return a default :class:`BackendOptions` for the given platform."""
        platform_lower = platform.lower()
        if platform_lower not in cls._PLATFORM_MAP:
            raise BackendOptionsError(f"Unknown platform: {platform_lower}")
        return cls.from_kwargs(platform_lower, {})

    @classmethod
    def normalize_options(
        cls,
        options: "BackendOptions | UnifiedOptions | dict[str, Any] | None",
        platform: str,
    ) -> BackendOptions:
        """Normalise mixed input to a validated :class:`BackendOptions` instance.

        This is the main integration point for :func:`submit_task`.

        Parameters
        ----------
        options :
            Either a :class:`BackendOptions` instance, a
            :class:`UnifiedOptions` instance (translated to the platform's
            specific options), a plain dict (treated as ``**kwargs``), or
            ``None`` (returns platform defaults).
        platform :
            Platform name.

        Returns
        -------
        BackendOptions
            Validated options object.

        Raises
        ------
        BackendOptionsError
            If ``options`` is not a :class:`BackendOptions`,
            :class:`UnifiedOptions`, dict, or ``None``.
        """
        if options is None:
            return cls.create_default(platform)
        if isinstance(options, BackendOptions):
            return options
        if isinstance(options, UnifiedOptions):
            return options.to_platform_options(platform)
        if isinstance(options, dict):
            return cls.from_kwargs(platform, options)
        raise BackendOptionsError(
            f"options must be BackendOptions, UnifiedOptions, dict, or None; "
            f"got {type(options).__name__}"
        )
