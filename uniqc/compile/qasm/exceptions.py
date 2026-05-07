"""QASM parser exceptions module.

Re-exported from :mod:`uniqc.exceptions` for backward compatibility.
"""

__all__ = ["NotSupportedGateError", "RegisterNotFoundError", "RegisterOutOfRangeError", "RegisterDefinitionError"]

from uniqc.exceptions import (  # noqa: F401
    NotSupportedGateError,
    RegisterDefinitionError,
    RegisterNotFoundError,
    RegisterOutOfRangeError,
)
