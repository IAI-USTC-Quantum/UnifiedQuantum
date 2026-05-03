"""Unified backend information data structures.

This module defines the canonical BackendInfo dataclass that all quantum cloud
platforms are normalised into, plus helpers for parsing and formatting backend
identifiers.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any


class Platform(Enum):
    ORIGINQ = "originq"
    QUAFU = "quafu"
    QUARK = "quark"
    IBM = "ibm"
    DUMMY = "dummy"


# ---------------------------------------------------------------------------
# OriginQ simulator names — must match what OriginQ Cloud reports.
# Kept here so both the adapter and registry can share it without a circular
# import (backend_info has no external dependencies).
# ---------------------------------------------------------------------------
ORIGINQ_SIMULATOR_NAMES = frozenset(
    {
        "full_amplitude",
        "partial_amplitude",
        "single_amplitude",
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class QubitTopology:
    """Directed edge in a qubit connectivity graph."""

    u: int
    v: int

    def to_dict(self) -> dict[str, int]:
        return {"u": self.u, "v": self.v}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> QubitTopology:
        return cls(u=int(d["u"]), v=int(d["v"]))


@dataclasses.dataclass(frozen=True, slots=True)
class BackendInfo:
    """Canonical description of a single quantum backend / chip / simulator.

    One BackendInfo object corresponds to one real device or cloud simulator
    exposed by a platform.  The object is hashable (frozen) so it can be
    stored in sets.
    """

    platform: Platform
    name: str
    description: str = ""
    num_qubits: int = 0
    topology: tuple[QubitTopology, ...] = ()
    status: str = "unknown"  # human-readable, e.g. "Online", "Offline", "Obsolete"
    is_simulator: bool = False
    is_hardware: bool = False
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)
    # Fidelity and coherence — None means not available from the platform API
    avg_1q_fidelity: float | None = None
    avg_2q_fidelity: float | None = None
    avg_readout_fidelity: float | None = None
    coherence_t1: float | None = None  # microseconds
    coherence_t2: float | None = None  # microseconds

    def full_id(self) -> str:
        """Return the globally-unique identifier: ``platform:name``."""
        if self.platform == Platform.DUMMY and self.name == "dummy":
            return "dummy"
        return f"{self.platform.value}:{self.name}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.value,
            "name": self.name,
            "description": self.description,
            "num_qubits": self.num_qubits,
            "topology": [e.to_dict() for e in self.topology],
            "status": self.status,
            "is_simulator": self.is_simulator,
            "is_hardware": self.is_hardware,
            "extra": self.extra,
            "avg_1q_fidelity": self.avg_1q_fidelity,
            "avg_2q_fidelity": self.avg_2q_fidelity,
            "avg_readout_fidelity": self.avg_readout_fidelity,
            "coherence_t1": self.coherence_t1,
            "coherence_t2": self.coherence_t2,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BackendInfo:
        platform = Platform(d["platform"])
        topology = tuple(QubitTopology.from_dict(e) for e in d.get("topology", []))
        return cls(
            platform=platform,
            name=d["name"],
            description=d.get("description", ""),
            num_qubits=d.get("num_qubits", 0),
            topology=topology,
            status=d.get("status", "unknown"),
            is_simulator=d.get("is_simulator", False),
            is_hardware=d.get("is_hardware", False),
            extra=d.get("extra", {}),
            avg_1q_fidelity=d.get("avg_1q_fidelity"),
            avg_2q_fidelity=d.get("avg_2q_fidelity"),
            avg_readout_fidelity=d.get("avg_readout_fidelity"),
            coherence_t1=d.get("coherence_t1"),
            coherence_t2=d.get("coherence_t2"),
        )


def parse_backend_id(identifier: str) -> tuple[Platform, str]:
    """Parse a backend identifier into (Platform, name).

    Supports two forms:
        - ``platform:name``   (e.g. ``originq:HanYuan_01``)
        - bare ``name``       (ambiguous; tries to match across all platforms)

    Args:
        identifier: Full or partial backend identifier.

    Returns:
        (Platform, backend_name) tuple.

    Raises:
        ValueError: If the format is invalid or the platform is unknown.
    """
    identifier = identifier.strip()
    if identifier == Platform.DUMMY.value:
        return Platform.DUMMY, "dummy"
    if ":" in identifier:
        platform_str, name = identifier.split(":", 1)
        try:
            platform = Platform(platform_str.strip())
        except ValueError:
            raise ValueError(
                f"Unknown platform '{platform_str}'. Valid platforms: {', '.join(p.value for p in Platform)}"
            ) from None
        return platform, name.strip()

    # Bare name — cannot be resolved without consulting the registry
    raise ValueError(
        f"Ambiguous backend identifier '{identifier}'. "
        f"Use the fully-qualified form 'platform:name', "
        f"e.g. 'originq:HanYuan_01'."
    )
