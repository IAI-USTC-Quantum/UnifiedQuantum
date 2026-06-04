"""OriginIR and OpenQASM2 format conversion utilities.

This module provides bidirectional conversion between OriginIR-ext,
official OriginIR, and OpenQASM2 quantum circuit representations.
"""

__all__ = [
    "convert_oir_to_qasm",
    "convert_qasm_to_oir",
    "convert_originir_ext_to_originir",
]
from uniqc._error_hints import format_enriched_message
from uniqc.exceptions import CircuitTranslationError

from .originir import OriginIR_BaseParser
from .qasm import OpenQASM2_BaseParser


def convert_oir_to_qasm(originir_str: str) -> str:
    """
    Convert OriginIR to OpenQASM2.
    """
    try:
        originir_parser = OriginIR_BaseParser()
        originir_parser.parse(originir_str)
        if originir_parser.qram_declarations:
            raise CircuitTranslationError(
                "Circuit contains QRAM declarations which cannot be converted to "
                "OpenQASM 2.0. QRAM is an OriginIR-ext-only feature.",
                source_format="originir-ext",
                target_format="qasm2",
            )
        return originir_parser.to_qasm()
    except CircuitTranslationError:
        raise
    except Exception as e:
        raise CircuitTranslationError(
            format_enriched_message(f"Failed to convert OriginIR to OpenQASM2: {e}", "compilation")
        ) from e


def convert_qasm_to_oir(qasm_str: str) -> str:
    """
    Convert OpenQASM2 to OriginIR.
    """
    try:
        qasm_parser = OpenQASM2_BaseParser()
        qasm_parser.parse(qasm_str)
        return qasm_parser.to_originir()
    except Exception as e:
        raise CircuitTranslationError(
            format_enriched_message(f"Failed to convert OpenQASM2 to OriginIR: {e}", "compilation")
        ) from e


def convert_originir_ext_to_originir(originir_ext_str: str) -> str:
    """Convert OriginIR-ext (superset) to strict official OriginIR.

    Pipeline:
    1. Parse the OriginIR-ext string into a :class:`~uniqc.Circuit`.
    2. Decompose extended gates to the official gate set.
    3. Serialize using block-level ``DAGGER``/``CONTROL`` syntax.

    The output is valid under the official OriginIR specification accepted
    by OriginQ cloud.
    """
    try:
        parser = OriginIR_BaseParser()
        parser.parse(originir_ext_str)
        if parser.qram_declarations:
            raise CircuitTranslationError(
                "Circuit contains QRAM declarations which cannot be converted to "
                "official OriginIR. QRAM is an OriginIR-ext-only feature.",
                source_format="originir-ext",
                target_format="originir",
            )
        circuit = parser.to_circuit()
        return circuit.to_originir_official()
    except CircuitTranslationError:
        raise
    except Exception as e:
        raise CircuitTranslationError(
            format_enriched_message(
                f"Failed to convert OriginIR-ext to official OriginIR: {e}", "compilation"
            )
        ) from e
