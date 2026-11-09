"""Consumer side of the versioned noise-model exchange (``nlearn.noise-model.v1``).

This module imports the offline noise-model exchange files produced by the
noise-learning product (schema ``nlearn.noise-model.v1``, consumer binding
``uniqc.noisy_simulator.v1``) and wires them into UniQC's frozen noisy
simulation stack — :class:`uniqc.simulator.NoisySimulator` (density-operator
backend) and :class:`uniqc.backend_adapter.task.adapters.dummy_adapter.DummyAdapter`.

The exchange is **data-only**: UniQC never imports the private ``nlearn``
package; everything needed to rebuild the channels is inside the JSON file
(Pauli probabilities, readout pairs, topology, layout) and integrity is
guarded by the file's canonical ``model_sha256``.  Model files declare
``new_hardware_run: false`` — importing one performs no new hardware run.

Capabilities exposed on top of the imported model:

- :func:`load_noise_model` — validate + parse an exchange file.
- :meth:`ImportedNoiseModel.to_simulator` — a density-operator
  ``NoisySimulator`` with the learned per-gate-instance Pauli channels and
  per-qubit readout error.
- :meth:`ImportedNoiseModel.to_adapter` — a ``DummyAdapter`` wired the same
  way, so the unified ``submit_task``-style flows keep working.
- :meth:`ImportedNoiseModel.simulate_counts` — run a circuit and return noisy
  shot counts including the model's post-measurement edge-flip mixture.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any

__all__ = [
    "SCHEMA",
    "UNIQC_BINDING",
    "ExchangeModelError",
    "ImportedNoiseModel",
    "load_noise_model",
    "validate_exchange_payload",
]

SCHEMA = "nlearn.noise-model.v1"
UNIQC_BINDING = "uniqc.noisy_simulator.v1"


class ExchangeModelError(ValueError):
    """Raised when a noise-model exchange file fails validation."""


def _canonical_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_exchange_payload(payload: dict) -> None:
    """Structural + integrity validation (mirrors the producer's own checks)."""
    if not isinstance(payload, dict):
        raise ExchangeModelError("noise model payload must be a JSON object")
    if payload.get("schema") != SCHEMA:
        raise ExchangeModelError(f"unsupported schema: {payload.get('schema')!r} (expected {SCHEMA!r})")
    declared = payload.get("model_sha256")
    body = {key: value for key, value in payload.items() if key != "model_sha256"}
    if not declared or _canonical_hash(body) != declared:
        raise ExchangeModelError("model_sha256 mismatch — exchange file corrupted or tampered")
    if payload.get("new_hardware_run") is not False:
        raise ExchangeModelError("exchange model must declare new_hardware_run=false")
    try:
        chain = payload["layout"]["physical_chain"]
        channels = payload["channels"]
        binding = payload["consumer_bindings"][UNIQC_BINDING]
        if len(channels["single_qubit"]) != len(chain):
            raise ExchangeModelError("single_qubit channel count does not match chain")
        if len(channels["readout"]) != len(chain):
            raise ExchangeModelError("readout channel count does not match chain")
        n = len(chain)
        for entry in binding["gate_specific_errors"]:
            gate = entry["gate"]
            qubits = entry["qubits"]
            if gate == "CZ" and (len(qubits) != 2 or not (0 <= qubits[0] < qubits[1] < n)):
                raise ExchangeModelError(f"CZ channel qubits out of range: {qubits}")
            if gate != "CZ" and (len(qubits) != 1 or not 0 <= qubits[0] < n):
                raise ExchangeModelError(f"1q channel qubits out of range: {qubits}")
    except KeyError as exc:
        raise ExchangeModelError(f"missing required field: {exc}") from None


@dataclasses.dataclass(frozen=True)
class ImportedNoiseModel:
    """A validated ``nlearn.noise-model.v1`` file wired for UniQC execution.

    Local qubit ``i`` of the model maps to physical qubit
    ``physical_chain[i]``; error channels, topology, and readout rates are
    addressed in *local* indices so the simulator can run on a compact
    register.
    """

    payload: dict[str, Any]
    path: Path | None

    @property
    def physical_chain(self) -> list[int]:
        return [int(q) for q in self.payload["layout"]["physical_chain"]]

    @property
    def num_qubits(self) -> int:
        return len(self.physical_chain)

    @property
    def local_edges(self) -> list[tuple[int, int]]:
        return [tuple(int(x) for x in edge) for edge in self.payload["topology"]["local_edges"]]

    @property
    def model_sha256(self) -> str:
        return str(self.payload["model_sha256"])

    @property
    def data_class(self) -> str:
        return str(self.payload["data_class"])

    @property
    def generator(self) -> dict[str, Any]:
        return dict(self.payload["generator"])

    def error_loader(self) -> Any:
        """Build the per-gate-instance error loader from the uniqc binding."""
        from uniqc.simulator.error_model import (
            ErrorLoader_GateSpecificError,
            PauliError1Q,
            PauliError2Q,
        )

        gate_specific: dict[tuple[str, tuple[int, ...]], list[Any]] = {}
        for entry in self.payload["consumer_bindings"][UNIQC_BINDING]["gate_specific_errors"]:
            gate = entry["gate"]
            qubits = tuple(sorted(int(q) for q in entry["qubits"]))
            error = entry["error"]
            if error["type"] == "PauliError1Q":
                model: Any = PauliError1Q(*(float(p) for p in error["arguments"]))
            elif error["type"] == "PauliError2Q":
                model = PauliError2Q([float(p) for p in error["arguments"]])
            else:
                raise ExchangeModelError(f"unsupported channel type in binding: {error['type']!r}")
            gate_specific.setdefault((gate, qubits), []).append(model)
        return ErrorLoader_GateSpecificError(
            generic_error=[],
            gatetype_error={},
            gate_specific_error=gate_specific,
        )

    def readout_error(self) -> dict[int, list[float]]:
        """Per-local-qubit readout error ``{q: [p01, p10]}``."""
        binding = self.payload["consumer_bindings"][UNIQC_BINDING]
        return {int(q): [float(v[0]), float(v[1])] for q, v in binding["readout_error"].items()}

    def edge_flip_entries(self) -> list[dict[str, Any]]:
        """Post-measurement stochastic XOR-mixture entries (already local)."""
        flip = self.payload["channels"].get("post_measurement_edge_flip") or {}
        return [dict(entry) for entry in flip.get("entries", [])]

    def to_simulator(self) -> Any:
        """A density-operator ``NoisySimulator`` carrying the learned channels."""
        from uniqc.simulator import NoisySimulator

        return NoisySimulator(
            backend_type="density_operator",
            error_loader=self.error_loader(),
            readout_error=self.readout_error(),
        )

    def to_adapter(self, backend_id: str = "dummy:noise-model") -> Any:
        """A ``DummyAdapter`` wired with the learned channels (unified pipeline)."""
        from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

        n = self.num_qubits
        return DummyAdapter(
            backend_id=backend_id,
            error_loader=self.error_loader(),
            readout_error=self.readout_error(),
            available_qubits=list(range(n)),
            available_topology=[list(edge) for edge in self.local_edges],
        )

    def apply_edge_flips(self, outcome: int, rng: Any) -> int:
        """Apply the post-measurement XOR mixture to one outcome integer."""
        for entry in self.edge_flip_entries():
            if float(rng.random()) < float(entry["rate"]):
                outcome ^= int(entry["outcome_xor_mask"])
        return outcome

    def simulate_counts(
        self,
        circuit: Any,
        *,
        shots: int,
        seed: int,
        qram_data: dict[str, dict[int, int]] | None = None,
    ) -> dict[str, int]:
        """Execute *circuit* on the learned noisy VM and sample shot counts.

        Args:
            circuit: ``Circuit`` object or OriginIR string.  Gates must live on
                local qubits ``0..n-1``; use ``RPhi``/``CZ`` to exercise the
                learned channels (RZ is virtual and noiseless per the model).
            shots: Number of shots.
            seed: Seed for shot sampling and the edge-flip mixture.
            qram_data: Optional ``{qram_name: {address: value}}`` preloaded
                into the simulator's QRAM objects before execution.

        Returns:
            Counts keyed by bitstring with local qubit ``i`` = character
            ``n-1-i`` (``c[i]`` rightmost, the UniQC endianness convention).
        """
        import numpy as np

        if shots < 1:
            raise ValueError(f"shots must be >= 1, got {shots}")
        sim = self.to_simulator()
        probabilities = None
        if qram_data:
            # Two-phase: preprocess once to materialise QRAM objects, preload
            # the data, then preprocess again (data survives re-preprocessing).
            sim.simulate_preprocess(circuit)
            for name, mapping in qram_data.items():
                qram = sim.qram_objects[name]
                for address, value in mapping.items():
                    qram.write(address, value)
            probabilities = np.asarray(sim.simulate_pmeasure(circuit), dtype=float)
        else:
            probabilities = np.asarray(sim.simulate_pmeasure(circuit), dtype=float)

        rng = np.random.default_rng(seed)
        sampled = rng.multinomial(shots, probabilities / probabilities.sum())
        counts: dict[int, int] = {}
        for outcome, count in enumerate(sampled):
            if count:
                flipped = self.apply_edge_flips(int(outcome), rng)
                counts[flipped] = counts.get(flipped, 0) + int(count)
        n_measured = int(round(np.log2(len(probabilities))))
        return {bin(outcome)[2:].zfill(n_measured): count for outcome, count in sorted(counts.items())}


def load_noise_model(path: str | Path) -> ImportedNoiseModel:
    """Load and validate a ``nlearn.noise-model.v1`` exchange file."""
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExchangeModelError(f"cannot read noise model {path}: {exc}") from None
    validate_exchange_payload(payload)
    return ImportedNoiseModel(payload=payload, path=path)
