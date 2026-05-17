"""Shared type definitions for the ansatz module."""

from __future__ import annotations

from enum import Enum

__all__ = [
    "EntanglingGate",
    "EntanglementTopology",
    "RotationGate",
]


class RotationGate(str, Enum):
    """Single-qubit rotation gates usable in ansatz rotation blocks."""

    RX = "rx"
    RY = "ry"
    RZ = "rz"


class EntanglingGate(str, Enum):
    """Two-qubit entangling gates usable in ansatz entangling layers.

    Non-parametric (0 extra params per edge): CNOT, CZ, ISWAP.
    Parametric (1 param per edge): CRX, CRY, CRZ, XX, YY, ZZ.
    """

    CNOT = "cnot"
    CZ = "cz"
    ISWAP = "iswap"
    CRX = "crx"
    CRY = "cry"
    CRZ = "crz"
    XX = "xx"
    YY = "yy"
    ZZ = "zz"

    @property
    def is_parametric(self) -> bool:
        return self in _PARAMETRIC_ENTANGLING_GATES


_PARAMETRIC_ENTANGLING_GATES = frozenset(
    {
        EntanglingGate.CRX,
        EntanglingGate.CRY,
        EntanglingGate.CRZ,
        EntanglingGate.XX,
        EntanglingGate.YY,
        EntanglingGate.ZZ,
    }
)


class EntanglementTopology(str, Enum):
    """Named entanglement topologies for HEA-like circuits."""

    LINEAR = "linear"
    RING = "ring"
    FULL = "full"
    STAR = "star"
    BRICKWORK = "brickwork"
    CUSTOM = "custom"
