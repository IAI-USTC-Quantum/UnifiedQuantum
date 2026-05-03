"""Variational quantum algorithm training modules.

Provides reusable algorithm implementations using TorchQuantum backend
for native PyTorch autograd-based optimization.

Requires optional dependencies: install unified-quantum[pytorch], then install
the TorchQuantum fork manually.
"""

from __future__ import annotations

__all__ = [
    "VQESolver",
    "build_h2_hamiltonian",
    "build_hea_circuit",
    "QAOASolver",
    "build_maxcut_hamiltonian",
    "build_qaoa_circuit",
    "QNNClassifier",
    "QCNNClassifier",
    "HybridQCLModel",
]

try:
    from .hybrid_model import HybridQCLModel
    from .qaoa_torch import QAOASolver, build_maxcut_hamiltonian, build_qaoa_circuit
    from .qcnn import QCNNClassifier
    from .qnn import QNNClassifier
    from .vqe_torch import VQESolver, build_h2_hamiltonian, build_hea_circuit
except ImportError:
    pass
