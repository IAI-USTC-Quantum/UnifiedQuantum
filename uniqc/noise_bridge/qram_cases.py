"""Noisy-VM functional cases: 3-layer QRAM, QPU addressing, and mitigation.

These cases exercise QRAM lookup, quantum addressing and mitigation using an
imported noise-model exchange file (:mod:`uniqc.noise_bridge.exchange`) — or
on the plain noiseless simulator as an ideal reference:

- **QRAM lookup (3 layers)** — a basis-state address register queries a
  ``QRAMDECL`` memory with 3 address bits (8 entries); the returned value is
  sampled through the noisy VM (gate channels + readout + edge flips).
- **QPU addressing** — the address register is prepared in a superposition
  (an entangling RPhi/CZ fanout makes the query exercise the learned 2-qubit
  channels); the data-register distribution reflects the quantum-addressed
  memory contents.
- **Readout mitigation** — the noisy counts are mitigated through the frozen
  :class:`uniqc.qem.ReadoutEM` unified interface, calibrated on the same
  noisy VM adapter.

All inputs are fixed (no randomness beyond seeded shot sampling), so a case
run is reproducible.  This is a *local simulation* capability — it is not a
real-hardware QRAM validation, and it never submits cloud tasks.
"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = [
    "QRAM_CASE_DATA",
    "build_qram_lookup_circuit",
    "build_qpu_addressing_circuit",
    "ideal_data_distribution",
    "run_qram_lookup_case",
    "run_qpu_addressing_case",
]

# 3-layer (8-entry) QRAM contents used by the packaged cases; data width 2.
QRAM_CASE_DATA: tuple[int, ...] = (3, 1, 2, 0, 3, 2, 1, 0)
ADDR_SIZE = 3
DATA_SIZE = 2
CASE_QRAM_NAME = "qram_case"
CASE_QUBITS = ADDR_SIZE + DATA_SIZE


def _bitstring(counts_key: str, width: int) -> int:
    return int(counts_key, 2) if counts_key else 0


def _data_only_circuit(address_gates: list[tuple[int, float, float]], *, entangle: bool):
    """Assemble the QRAM case circuit (local qubits: 0..2 address, 3..4 data)."""
    from uniqc.circuit_builder.qcircuit import Circuit

    circuit = Circuit()
    circuit.qram_declare(CASE_QRAM_NAME, ADDR_SIZE, DATA_SIZE)
    for qubit, theta, phi in address_gates:
        circuit.rphi(qubit, theta, phi)
    if entangle:
        # Entangling fanout across the address line: exercises the learned
        # CZ channels and makes the address state genuinely quantum.
        circuit.cz(0, 1)
        circuit.rphi(2, np.pi / 2, 0.0)
        circuit.cz(1, 2)
        circuit.rphi(0, np.pi / 2, 0.0)
        circuit.rphi(1, np.pi / 2, 0.0)
        circuit.cz(0, 1)
    circuit.qram_call(CASE_QRAM_NAME, *range(CASE_QUBITS))
    circuit.measure(ADDR_SIZE, ADDR_SIZE + 1)
    return circuit


def build_qram_lookup_circuit(address: int):
    """Basis-state QRAM lookup: prepare ``|address>`` via RPhi(pi,0) and query."""
    if not 0 <= address < len(QRAM_CASE_DATA):
        raise ValueError(f"address must be in [0, {len(QRAM_CASE_DATA) - 1}], got {address}")
    gates = [(qubit, float(np.pi), 0.0) for qubit in range(ADDR_SIZE) if (address >> qubit) & 1]
    return _data_only_circuit(gates, entangle=False)


def build_qpu_addressing_circuit():
    """QPU-addressed query: entangled superposition over the address register."""
    gates = [(qubit, np.pi / 2, 0.0) for qubit in range(ADDR_SIZE)]
    return _data_only_circuit(gates, entangle=True)


def _ideal_probabilities(circuit) -> np.ndarray:
    """Noiseless reference distribution over the data register."""
    from uniqc.simulator import Simulator

    sim = Simulator(backend_type="statevector")
    sim.simulate_preprocess(circuit)
    qram = sim.qram_objects[CASE_QRAM_NAME]
    for address, value in enumerate(QRAM_CASE_DATA):
        qram.write(address, value)
    return np.asarray(sim.simulate_pmeasure(circuit), dtype=float)


def ideal_data_distribution(circuit) -> dict[int, float]:
    """Ideal distribution over data-register values for a QRAM case circuit."""
    probs = _ideal_probabilities(circuit)
    return {value: float(probs[value]) for value in range(len(probs)) if probs[value] > 0}


def distribution_fidelity(counts: dict[str, int], ideal: dict[int, float]) -> float:
    """Classical fidelity <sqrt(p q)> between sampled counts and ideal probs."""
    shots = sum(counts.values())
    if shots == 0:
        return 0.0
    observed: dict[int, float] = {}
    for key, count in counts.items():
        observed[_bitstring(key, len(key))] = observed.get(_bitstring(key, len(key)), 0.0) + count / shots
    return float(sum(np.sqrt(observed.get(value, 0.0) * probability) for value, probability in ideal.items()))


def _run_noisy(model: Any, circuit, shots: int, seed: int) -> dict[str, int]:
    """Sample counts on the imported noisy VM (QRAM data preloaded)."""
    return model.simulate_counts(
        circuit,
        shots=shots,
        seed=seed,
        qram_data={CASE_QRAM_NAME: dict(enumerate(QRAM_CASE_DATA))},
    )


def _mitigate(model: Any, counts: dict[str, int], shots: int, workdir) -> dict[str, int]:
    """Readout-EM mitigation through the frozen unified interface.

    Calibrates the data-register qubits (local 3..4) on the imported noisy
    VM adapter, then mitigates the case counts.  Calibration circuits run
    through the same adapter, so the mitigation sees exactly the model's
    readout channels.
    """
    from uniqc.backend_adapter.task.result_types import UnifiedResult
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.qem import ReadoutEM

    adapter = model.to_adapter(backend_id="dummy:noise-model")
    calibrator = ReadoutCalibrator(adapter=adapter, shots=shots, cache_dir=str(workdir))
    calibrator.calibrate_qubits([ADDR_SIZE, ADDR_SIZE + 1])
    calibrator.calibrate_pairs([(ADDR_SIZE, ADDR_SIZE + 1)])
    mitigator = ReadoutEM(adapter=adapter, cache_dir=str(workdir), shots=shots)
    result = UnifiedResult.from_counts(counts=dict(counts), platform="dummy", task_id="qram-case")
    mitigated = mitigator.apply(result, measured_qubits=[ADDR_SIZE, ADDR_SIZE + 1])
    return dict(mitigated.counts)


def run_qram_lookup_case(
    model: Any,
    *,
    address: int,
    shots: int = 1000,
    seed: int = 0,
    workdir: Any = None,
) -> dict[str, Any]:
    """Run the 3-layer QRAM basis-lookup case on a noisy VM.

    Returns a JSON-able report: expected value, noisy top outcome, mitigated
    top outcome, raw/mitigated accuracy and fidelity, and evidence metadata.
    """
    import pathlib
    import tempfile

    circuit = build_qram_lookup_circuit(address)
    expected = QRAM_CASE_DATA[address]
    ideal = {expected: 1.0}
    counts = _run_noisy(model, circuit, shots, seed)
    workdir = pathlib.Path(workdir) if workdir is not None else pathlib.Path(tempfile.mkdtemp(prefix="uniqc-qram-"))
    mitigated = _mitigate(model, counts, shots, workdir)

    def _top(counts: dict[str, int]) -> int:
        return max(counts, key=counts.get) if counts else -1  # type: ignore[arg-type,return-value]

    top_raw = _top(counts)
    top_mit = _mitigated_top(mitigated)
    raw_hits = counts.get(format(expected, "02b"), 0)
    mit_hits = mitigated.get(format(expected, "02b"), 0)
    return {
        "case": "qram_lookup_3layer",
        "address": address,
        "expected_value": expected,
        "qram_data": list(QRAM_CASE_DATA),
        "shots": shots,
        "seed": seed,
        "noisy_counts": counts,
        "mitigated_counts": mitigated,
        "raw_accuracy": raw_hits / shots,
        "mitigated_accuracy": mit_hits / max(sum(mitigated.values()), 1),
        "raw_top_outcome": top_raw,
        "mitigated_top_outcome": top_mit,
        "ideal_distribution": {str(k): v for k, v in ideal.items()},
        "raw_fidelity": distribution_fidelity(counts, ideal),
        "mitigated_fidelity": distribution_fidelity(mitigated, ideal),
        "model_sha256": model.model_sha256,
    }


def _mitigated_top(mitigated: dict[str, int]) -> str:
    return max(mitigated, key=mitigated.get) if mitigated else ""


def run_qpu_addressing_case(
    model: Any,
    *,
    shots: int = 1000,
    seed: int = 0,
    workdir: Any = None,
) -> dict[str, Any]:
    """Run the QPU-superposition-addressing case on a noisy VM.

    The data-register distribution of the entangled-address query is compared
    against the ideal (noiseless) distribution, before and after readout EM.
    """
    import pathlib
    import tempfile

    circuit = build_qpu_addressing_circuit()
    ideal = ideal_data_distribution(circuit)
    counts = _run_noisy(model, circuit, shots, seed)
    workdir = pathlib.Path(workdir) if workdir is not None else pathlib.Path(tempfile.mkdtemp(prefix="uniqc-qram-"))
    mitigated = _mitigate(model, counts, shots, workdir)
    return {
        "case": "qpu_addressing_3layer_qram",
        "qram_data": list(QRAM_CASE_DATA),
        "shots": shots,
        "seed": seed,
        "ideal_distribution": {str(k): round(v, 6) for k, v in sorted(ideal.items())},
        "noisy_counts": counts,
        "mitigated_counts": mitigated,
        "raw_fidelity": distribution_fidelity(counts, ideal),
        "mitigated_fidelity": distribution_fidelity(mitigated, ideal),
        "model_sha256": model.model_sha256,
    }
