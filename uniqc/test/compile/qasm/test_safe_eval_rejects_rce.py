"""Tests for ``uniqc.compile.qasm._safe_eval.safe_eval_param``.

Verifies that the safe evaluator rejects RCE payloads that the previous
``eval()``-based implementation accepted, while still evaluating the
benign numeric expressions used by real QASM circuits.
"""

from __future__ import annotations

import math

import pytest

from uniqc.compile.qasm._safe_eval import safe_eval_param


def test_rejects_dunder_import_rce() -> None:
    with pytest.raises(ValueError):
        safe_eval_param("__import__('os').system('id')")


def test_rejects_subclass_walk_rce() -> None:
    with pytest.raises(ValueError):
        safe_eval_param("().__class__.__bases__[0].__subclasses__()")


def test_rejects_open_call() -> None:
    with pytest.raises(ValueError):
        safe_eval_param("open('/etc/passwd').read()")


def test_pi_constant() -> None:
    assert safe_eval_param("pi/2") == pytest.approx(math.pi / 2)


def test_math_function_composition() -> None:
    expected = math.sin(0.5) + math.cos(0.5) ** 2
    assert safe_eval_param("sin(0.5) + cos(0.5)**2") == pytest.approx(expected)
