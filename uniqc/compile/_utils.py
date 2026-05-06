
"""Compilation exception re-exports.

Historical names ``CompilationFailedException`` and ``IRConversionFailedException``
have been renamed to :class:`~uniqc.exceptions.CompilationFailedError` and
:class:`~uniqc.exceptions.CircuitTranslationError` respectively.
"""

__all__ = ["CompilationFailedError", "CircuitTranslationError"]

from uniqc.exceptions import CircuitTranslationError, CompilationFailedError
