import warnings
from typing import TYPE_CHECKING

try:
    # uniqc_cpp extension is implemented by C++
    from uniqc_cpp import *  # noqa: F403

    if TYPE_CHECKING:
        from .uniqc_cpp import *  # noqa: F403
except ImportError:
    # Note: Without compiling the UniqcCpp, you can also use uniqc.
    # Only the C++ simulator is disabled.
    warnings.warn("uniqc is not installed with UniqcCpp.", stacklevel=2)

from .get_backend import create_simulator as create_simulator
from .get_backend import get_backend as get_backend
from .get_backend import get_simulator as get_simulator
from .mps_simulator import MPSConfig as MPSConfig
from .mps_simulator import MPSSimulator as MPSSimulator
from .originir_simulator import OriginIR_NoisySimulator as OriginIR_NoisySimulator
from .originir_simulator import OriginIR_Simulator as OriginIR_Simulator
from .qasm_simulator import QASM_Simulator as QASM_Simulator

try:
    from .torchquantum_simulator import TORCHQUANTUM_AVAILABLE as TORCHQUANTUM_AVAILABLE
    from .torchquantum_simulator import TorchQuantumSimulator as TorchQuantumSimulator
except ImportError:
    TORCHQUANTUM_AVAILABLE = False
