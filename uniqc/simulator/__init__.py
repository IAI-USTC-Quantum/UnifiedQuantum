import warnings
from typing import TYPE_CHECKING
try:
    # uniqc_cpp extension is implemented by C++
    from uniqc_cpp import *
    if TYPE_CHECKING:
        from .uniqc_cpp import *
except ImportError as e:
    # Note: Without compiling the UniqcCpp, you can also use uniqc.
    # Only the C++ simulator is disabled.
    warnings.warn('uniqc is not install with UniqcCpp.')

from .originir_simulator import OriginIR_Simulator, OriginIR_NoisySimulator