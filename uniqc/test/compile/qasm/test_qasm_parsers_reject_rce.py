"""Tests that the OpenQASM 2.0 parsers reject parameter-expression RCE
payloads instead of executing them via ``eval()``.

These tests exercise the public ``OpenQASM2_BaseParser.parse`` entry point,
which is what every caller in the codebase (``uniqc.cli``,
``uniqc.compile.converter``, ``uniqc.circuit_builder.normalize``, …) uses
to parse QASM source.  A malicious parameter must surface a
``ValueError``-family error rather than silently invoking ``__import__``.
"""

from __future__ import annotations

import os

import pytest

from uniqc.compile.qasm import OpenQASM2_BaseParser

# Sentinel file path the canary payloads would create if eval() actually ran.
# We place it inside the pytest tmp_path so the test is self-cleaning even if
# something goes catastrophically wrong.


def _canary_path(tmp_path) -> str:
    return str(tmp_path / "PWNED_RCE_CANARY")


def _malicious_payload(canary: str) -> str:
    # Quote the path safely for embedding inside the QASM string literal.
    quoted = canary.replace("'", "\\'")
    return f"__import__('os').system('touch {quoted}')"


def test_line_parser_rejects_unsafe_param(tmp_path) -> None:
    """The line parser's parameter regex blocks nested parens, so a
    fully-fledged ``__import__('os').system(...)`` payload can't even reach
    ``handle_parameters``.  But a bare unsafe identifier *does* pass the
    regex — and the old ``eval(parameter_str, {"pi": math.pi})`` would
    happily resolve it because ``eval`` auto-injects ``__builtins__`` when
    the globals dict lacks the key.  ``safe_eval_param`` must reject it.
    """
    qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\nrx(__import__) q[0];\n'

    parser = OpenQASM2_BaseParser()
    with pytest.raises(Exception) as exc_info:
        parser.parse(qasm)

    # The cause must ultimately be our safe-evaluator rejection.
    chain = []
    err = exc_info.value
    while err is not None:
        chain.append(err)
        err = err.__cause__ or err.__context__
    assert any(isinstance(e, ValueError) and "Unsafe QASM expression" in str(e) for e in chain), (
        f"Expected an Unsafe-QASM-expression ValueError, got chain={chain!r}"
    )


def test_custom_gate_body_rejects_rce_payload(tmp_path) -> None:
    """The custom-gate-definition expansion path goes through
    ``qasm_base_parser._eval_param_expr``.  A malicious expression supplied
    as a bound argument to a custom gate must also be rejected (or at worst
    passed through as text) — *never* executed.
    """
    canary = _canary_path(tmp_path)
    payload = _malicious_payload(canary)

    qasm = (
        "OPENQASM 2.0;\n"
        'include "qelib1.inc";\n'
        "gate mygate(theta) q { rx(theta) q; }\n"
        "qreg q[1];\n"
        "creg c[1];\n"
        f"mygate({payload}) q[0];\n"
    )

    parser = OpenQASM2_BaseParser()
    # The parser is permitted either to raise (preferred) or to fall through
    # to the line-parser which will raise.  Either way: must not succeed
    # silently and must not run the payload.
    with pytest.raises(Exception):
        parser.parse(qasm)

    assert not os.path.exists(canary), f"RCE canary file {canary} was created — eval() executed the payload!"
