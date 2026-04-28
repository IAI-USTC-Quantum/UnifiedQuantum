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
    IBM = "ibm"


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

    def full_id(self) -> str:
        """Return the globally-unique identifier: ``platform:name``."""
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
    if ":" in identifier:
        platform_str, name = identifier.split(":", 1)
        try:
            platform = Platform(platform_str.strip())
        except ValueError:
            raise ValueError(
                f"Unknown platform '{platform_str}'. "
                f"Valid platforms: {', '.join(p.value for p in Platform)}"
            ) from None
        return platform, name.strip()

    # Bare name — cannot be resolved without consulting the registry
    raise ValueError(
        f"Ambiguous backend identifier '{identifier}'. "
        f"Use the fully-qualified form 'platform:name', "
        f"e.g. 'originq:HanYuan_01'."
    )
