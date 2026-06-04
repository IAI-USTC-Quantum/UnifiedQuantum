from .base_simulator import BaseSimulator
from .mps_simulator import MPSSimulator
from .simulator import Simulator
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
        program_type: Ignored — :class:`Simulator` auto-detects the input
            format.  Kept for backward compatibility.
        **kwargs: Additional arguments passed to the simulator constructor.

    Returns:
        A simulator instance for the requested backend.

    Raises:
        ValueError: If the backend is not supported.
        ImportError: If the TorchQuantum backend is requested but optional
            dependencies are not installed.
    """
    normalised_backend = backend.replace("-", "_").lower()
    if normalised_backend == "torchquantum":
        return TorchQuantumSimulator(**kwargs)
    if normalised_backend in ("mps", "matrix_product_state"):
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
    return Simulator(backend_type=backend_type, **kwargs)


def get_simulator(
    backend_type: str = "statevector",
    program_type: str = "originir",
    **kwargs,
) -> BaseSimulator | TorchQuantumSimulator | MPSSimulator:
    """Create a simulator instance (alias for :func:`create_simulator`).

    The argument order matches :func:`create_simulator` — ``backend_type``
    first, then ``program_type``. Both arguments default to the most common
    case (``"statevector"`` + ``"originir"``).

    Args:
        backend_type: Simulator backend, e.g. ``"statevector"``,
            ``"density_matrix"``, ``"mps"``, ``"torchquantum"``.
        program_type: Ignored — :class:`Simulator` auto-detects the input
            format.
        **kwargs: Additional arguments passed to the simulator constructor.

    Returns:
        A simulator instance.
    """
    return create_simulator(backend=backend_type, program_type=program_type, **kwargs)


def get_backend(
    backend_type: str = "statevector",
    program_type: str = "originir",
    **kwargs,
) -> BaseSimulator | TorchQuantumSimulator | MPSSimulator:
    """Deprecated: use :func:`get_simulator` or :func:`create_simulator`.

    .. deprecated::
        This function will be removed in uniqc 0.1.0. See
        :doc:`/source/7_releases/deprecation_policy` for the project-wide
        0.0.x → 0.1.0 compatibility cliff.
    """
    from uniqc._deprecation import warn_removed_in_0_1_0

    warn_removed_in_0_1_0(
        "uniqc.simulator.get_backend()",
        replacement="get_simulator() or create_simulator()",
        stacklevel=2,
    )
    return create_simulator(backend=backend_type, program_type=program_type, **kwargs)
