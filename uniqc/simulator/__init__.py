"""Public simulator API.

Two ways to obtain a simulator:

- :func:`create_simulator` (recommended) — factory keyed by ``backend`` then
  ``program_type``. Accepts both names and aliases.
- :func:`get_simulator` — alias of :func:`create_simulator` with the same
  ``(backend_type, program_type)`` argument order.

Concrete simulator classes (``OriginIR_Simulator``, ``QASM_Simulator``,
``MPSSimulator``, ``TorchQuantumSimulator``, ``OpcodeSimulator``) and
common error-model classes (``Depolarizing``, ``AmplitudeDamping`` …) are
re-exported here so users do not need to know the submodule layout.
"""

from __future__ import annotations

import warnings as _warnings

try:
    # uniqc_cpp extension is implemented by C++; importing it side-effect
    # registers the native simulators used by ``OpcodeSimulator``.
    from uniqc_cpp import *  # noqa: F401,F403
except ImportError:
    _warnings.warn("uniqc is not installed with UniqcCpp.", stacklevel=2)

from . import error_model as error_model
from .error_model import (
    AmplitudeDamping as AmplitudeDamping,
    BitFlip as BitFlip,
    Depolarizing as Depolarizing,
    ErrorLoader as ErrorLoader,
    ErrorLoader_GateSpecificError as ErrorLoader_GateSpecificError,
    ErrorLoader_GateTypeError as ErrorLoader_GateTypeError,
    ErrorLoader_GenericError as ErrorLoader_GenericError,
    ErrorModel as ErrorModel,
    Kraus1Q as Kraus1Q,
    PauliError1Q as PauliError1Q,
    PauliError2Q as PauliError2Q,
    PhaseFlip as PhaseFlip,
    TwoQubitDepolarizing as TwoQubitDepolarizing,
)
from .get_backend import create_simulator as create_simulator
from .get_backend import get_backend as get_backend
from .get_backend import get_simulator as get_simulator
from .mps_simulator import MPSConfig as MPSConfig
from .mps_simulator import MPSSimulator as MPSSimulator
from .opcode_simulator import OpcodeSimulator as OpcodeSimulator
from .opcode_simulator import backend_alias as backend_alias
from .originir_simulator import OriginIR_NoisySimulator as OriginIR_NoisySimulator
from .originir_simulator import OriginIR_Simulator as OriginIR_Simulator
from .qasm_simulator import QASM_Simulator as QASM_Simulator

try:
    from .torchquantum_simulator import TORCHQUANTUM_AVAILABLE as TORCHQUANTUM_AVAILABLE
    from .torchquantum_simulator import TorchQuantumSimulator as TorchQuantumSimulator
except ImportError:
    TORCHQUANTUM_AVAILABLE = False

__all__ = [
    # factories
    "create_simulator",
    "get_simulator",
    "get_backend",
    # concrete simulators
    "OpcodeSimulator",
    "OriginIR_Simulator",
    "OriginIR_NoisySimulator",
    "QASM_Simulator",
    "MPSSimulator",
    "MPSConfig",
    "TorchQuantumSimulator",
    "TORCHQUANTUM_AVAILABLE",
    "backend_alias",
    # noise / error model (also available as ``uniqc.simulator.error_model``)
    "error_model",
    "ErrorModel",
    "BitFlip",
    "PhaseFlip",
    "Depolarizing",
    "TwoQubitDepolarizing",
    "AmplitudeDamping",
    "PauliError1Q",
    "PauliError2Q",
    "Kraus1Q",
    "ErrorLoader",
    "ErrorLoader_GenericError",
    "ErrorLoader_GateTypeError",
    "ErrorLoader_GateSpecificError",
]

del _warnings
