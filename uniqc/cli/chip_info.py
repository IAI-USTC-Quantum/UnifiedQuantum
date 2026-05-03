"""Chip characterization data schemas.

Unified per-qubit, per-pair, and global chip data for all quantum cloud
platforms. Each :class:`ChipCharacterization` is cached as a single JSON file
under ``~/.uniqc/backend-cache/``.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from uniqc.backend_adapter.backend_info import Platform, QubitTopology

__all__ = [
    "SingleQubitData",
    "TwoQubitGateData",
    "TwoQubitData",
    "ChipGlobalInfo",
    "ChipCharacterization",
]


@dataclasses.dataclass(frozen=True, slots=True)
class SingleQubitData:
    """Per-qubit calibration data for one physical qubit."""

    qubit_id: int
    t1: float | None = None  # microseconds
    t2: float | None = None  # microseconds
    single_gate_fidelity: float | None = None  # e.g. SX/X gate fidelity
    readout_fidelity_0: float | None = None  # P(0|0) probability
    readout_fidelity_1: float | None = None  # P(1|1) probability
    avg_readout_fidelity: float | None = None  # (P(0|0) + P(1|1)) / 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "qubit_id": self.qubit_id,
            "t1": self.t1,
            "t2": self.t2,
            "single_gate_fidelity": self.single_gate_fidelity,
            "readout_fidelity_0": self.readout_fidelity_0,
            "readout_fidelity_1": self.readout_fidelity_1,
            "avg_readout_fidelity": self.avg_readout_fidelity,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SingleQubitData:
        return cls(
            qubit_id=int(d["qubit_id"]),
            t1=d.get("t1"),
            t2=d.get("t2"),
            single_gate_fidelity=d.get("single_gate_fidelity"),
            readout_fidelity_0=d.get("readout_fidelity_0"),
            readout_fidelity_1=d.get("readout_fidelity_1"),
            avg_readout_fidelity=d.get("avg_readout_fidelity"),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class TwoQubitGateData:
    """Fidelity for one two-qubit gate type on a specific qubit pair."""

    gate: str  # "cz" | "ecr" | "cx" | "iswap" | ...
    fidelity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"gate": self.gate, "fidelity": self.fidelity}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TwoQubitGateData:
        return cls(gate=str(d["gate"]), fidelity=d.get("fidelity"))


@dataclasses.dataclass(frozen=True, slots=True)
class TwoQubitData:
    """Per-pair calibration data for one connected qubit pair."""

    qubit_u: int
    qubit_v: int
    gates: tuple[TwoQubitGateData, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "qubit_u": self.qubit_u,
            "qubit_v": self.qubit_v,
            "gates": [g.to_dict() for g in self.gates],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TwoQubitData:
        return cls(
            qubit_u=int(d["qubit_u"]),
            qubit_v=int(d["qubit_v"]),
            gates=tuple(TwoQubitGateData.from_dict(g) for g in d.get("gates", [])),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ChipGlobalInfo:
    """Global chip properties that apply to all qubits / pairs."""

    single_qubit_gates: tuple[str, ...] = ()
    two_qubit_gates: tuple[str, ...] = ()
    single_qubit_gate_time: float | None = None  # nanoseconds
    two_qubit_gate_time: float | None = None  # nanoseconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "single_qubit_gates": list(self.single_qubit_gates),
            "two_qubit_gates": list(self.two_qubit_gates),
            "single_qubit_gate_time": self.single_qubit_gate_time,
            "two_qubit_gate_time": self.two_qubit_gate_time,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChipGlobalInfo:
        return cls(
            single_qubit_gates=tuple(d.get("single_qubit_gates", [])),
            two_qubit_gates=tuple(d.get("two_qubit_gates", [])),
            single_qubit_gate_time=d.get("single_qubit_gate_time"),
            two_qubit_gate_time=d.get("two_qubit_gate_time"),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ChipCharacterization:
    """Complete characterization data for one quantum chip / backend.

    One object per physical device. Stored as a single JSON file under
    ``~/.uniqc/backend-cache/{platform}-{chip_name}.json``.
    """

    platform: Platform
    chip_name: str
    full_id: str
    available_qubits: tuple[int, ...] = ()
    connectivity: tuple[QubitTopology, ...] = ()
    single_qubit_data: tuple[SingleQubitData, ...] = ()
    two_qubit_data: tuple[TwoQubitData, ...] = ()
    global_info: ChipGlobalInfo = ChipGlobalInfo()
    calibrated_at: str | None = None  # ISO-8601 timestamp from platform API

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.value,
            "chip_name": self.chip_name,
            "full_id": self.full_id,
            "available_qubits": list(self.available_qubits),
            "connectivity": [e.to_dict() for e in self.connectivity],
            "single_qubit_data": [s.to_dict() for s in self.single_qubit_data],
            "two_qubit_data": [t.to_dict() for t in self.two_qubit_data],
            "global_info": self.global_info.to_dict(),
            "calibrated_at": self.calibrated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChipCharacterization:
        platform = Platform(d["platform"])
        return cls(
            platform=platform,
            chip_name=str(d["chip_name"]),
            full_id=str(d["full_id"]),
            available_qubits=tuple(d.get("available_qubits", [])),
            connectivity=tuple(QubitTopology.from_dict(e) for e in d.get("connectivity", [])),
            single_qubit_data=tuple(SingleQubitData.from_dict(s) for s in d.get("single_qubit_data", [])),
            two_qubit_data=tuple(TwoQubitData.from_dict(t) for t in d.get("two_qubit_data", [])),
            global_info=ChipGlobalInfo.from_dict(d.get("global_info", {})),
            calibrated_at=d.get("calibrated_at"),
        )
