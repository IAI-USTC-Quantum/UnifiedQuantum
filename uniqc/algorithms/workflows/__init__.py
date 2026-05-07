"""Higher-level workflows that combine calibration, execution, and mitigation.

Currently includes:
- :mod:`readout_em_workflow` — calibrate + apply readout-error mitigation
- :mod:`xeb_workflow`         — 1q / 2q / parallel cross-entropy benchmarking
- :mod:`vqe_workflow`         — scipy-driven VQE on a Pauli-string Hamiltonian
- :mod:`qaoa_workflow`        — scipy-driven QAOA on a cost Hamiltonian
- :mod:`classical_shadow_workflow` — collect shadow snapshots + multi-observable estimates

VQE/QAOA workflows here are deliberately torch-free so they work in the base
install. For autodiff / parameter-shift / batched-gradient flavours, use
:mod:`uniqc.algorithms.core.training` (requires ``[pytorch] + torchquantum``).
"""

from . import (
    classical_shadow_workflow,
    qaoa_workflow,
    readout_em_workflow,
    vqe_workflow,
    xeb_workflow,
)

__all__ = [
    "classical_shadow_workflow",
    "qaoa_workflow",
    "readout_em_workflow",
    "vqe_workflow",
    "xeb_workflow",
]
