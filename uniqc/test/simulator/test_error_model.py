"""Tests for simulator error models."""

from __future__ import annotations

from uniqc.simulator.error_model import Depolarizing, ErrorLoader_GenericError


def test_error_loader_process_opcodes_resets_between_circuits():
    """Reusable error loaders should not retain prior circuit opcodes."""
    error_loader = ErrorLoader_GenericError([Depolarizing(0.01)])

    error_loader.process_opcodes([("X", 0, None, None, False, None)])
    error_loader.process_opcodes([("HADAMARD", 0, None, None, False, None)])

    assert error_loader.opcodes == [
        ("HADAMARD", 0, None, None, False, None),
        ("Depolarizing", 0, None, 0.01, None, None),
    ]
