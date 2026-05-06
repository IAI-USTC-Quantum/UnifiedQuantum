from .base_simulator import BaseSimulator
from .mps_simulator import MPSSimulator
from .originir_simulator import OriginIR_Simulator
from .qasm_simulator import QASM_Simulator
from .torchquantum_simulator import TorchQuantumSimulator

__all__ = ["create_simulator", "get_simulator"]


def create_simulator(
    backend: str = "statevector",
    program_type: str = "originir",
    **kwargs,
) -> BaseSimulator | TorchQuantumSimulator | MPSSimulator:
    """Create a simulator backend.

    Args:
        backend: Simulator backend name. Supported values include
            ``"statevector"``, ``"density_matrix"``, ``"densitymatrix"``,
            ``"density"``, ``"torchquantum"``, and ``"mps"`` (alias
            ``"matrix_product_state"``).
        program_type: Type of quantum program ("originir" or "qasm").
        **kwargs: Additional arguments passed to the simulator constructor.

    Returns:
        A simulator instance for the requested backend.

    Raises:
        ValueError: If the backend or program type is not supported.
        ImportError: If the TorchQuantum backend is requested but optional
            dependencies are not installed.
    """
    normalised_backend = backend.replace("-", "_").lower()
    if normalised_backend == "torchquantum":
        return TorchQuantumSimulator(**kwargs)
    if normalised_backend in ("mps", "matrix_product_state"):
        if program_type != "originir":
            raise ValueError(
                "MPSSimulator currently only supports program_type='originir'"
            )
        return MPSSimulator(**kwargs)

    backend_type_aliases = {
        "statevector": "statevector",
        "density": "densitymatrix",
        "density_matrix": "densitymatrix",
        "densitymatrix": "densitymatrix",
    }
    if normalised_backend not in backend_type_aliases:
        raise ValueError(f"Unsupported simulator backend: {backend}")

    backend_type = backend_type_aliases[normalised_backend]
    if program_type == "originir":
        return OriginIR_Simulator(backend_type=backend_type, **kwargs)

    if program_type == "qasm":
        return QASM_Simulator(backend_type=backend_type, **kwargs)

    raise ValueError(f"Unsupported program type: {program_type}")


def get_simulator(
    program_type: str = "originir",
    backend_type: str = "statevector",
    **kwargs,
) -> BaseSimulator | TorchQuantumSimulator | MPSSimulator:
    """Create a simulator instance (alias for :func:`create_simulator`).

    Args:
        program_type: Type of quantum program (``"originir"`` or ``"qasm"``).
        backend_type: Simulator backend (``"statevector"``, ``"density_matrix"``, etc.).
        **kwargs: Additional arguments passed to the simulator constructor.

    Returns:
        A simulator instance.
    """
    return create_simulator(backend=backend_type, program_type=program_type, **kwargs)


def get_backend(
    program_type: str = "originir",
    backend_type: str = "statevector",
    **kwargs,
) -> BaseSimulator | TorchQuantumSimulator | MPSSimulator:
    """Deprecated: use :func:`get_simulator` or :func:`create_simulator`."""
    import warnings

    warnings.warn(
        "uniqc.simulator.get_backend() is deprecated. "
        "Use get_simulator() or create_simulator() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_simulator(backend=backend_type, program_type=program_type, **kwargs)
