"""Noise-model bridge: versioned exchange import, noisy VM, QRAM/QPU cases.

Public surface:

- :func:`load_noise_model` — import a ``nlearn.noise-model.v1`` exchange file.
- :class:`ImportedNoiseModel` — simulator/adapter factories + noisy sampling.
- :mod:`uniqc.noise_bridge.qram_cases` — 3-layer QRAM / QPU-addressing /
  readout-mitigation cases on the noisy VM.
- :mod:`uniqc.noise_bridge.synthetic` — synthetic exchange models (clearly
  labeled, WK_C180-scale magnitudes) for local verification.

UniQC never imports the private noise-learning package; the exchange is
data-only and integrity-checked by the file's canonical ``model_sha256``.
"""

from uniqc.noise_bridge.exchange import (
    SCHEMA,
    UNIQC_BINDING,
    ExchangeModelError,
    ImportedNoiseModel,
    load_noise_model,
    validate_exchange_payload,
)
from uniqc.noise_bridge.qram_cases import (
    QRAM_CASE_DATA,
    build_qpu_addressing_circuit,
    build_qram_lookup_circuit,
    run_qpu_addressing_case,
    run_qram_lookup_case,
)
from uniqc.noise_bridge.synthetic import build_synthetic_model, write_synthetic_model

__all__ = [
    "SCHEMA",
    "UNIQC_BINDING",
    "ExchangeModelError",
    "ImportedNoiseModel",
    "load_noise_model",
    "validate_exchange_payload",
    "QRAM_CASE_DATA",
    "build_qpu_addressing_circuit",
    "build_qram_lookup_circuit",
    "run_qpu_addressing_case",
    "run_qram_lookup_case",
    "build_synthetic_model",
    "write_synthetic_model",
]
