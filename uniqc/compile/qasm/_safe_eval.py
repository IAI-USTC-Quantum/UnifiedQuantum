"""Safe evaluator for OpenQASM numeric parameter expressions.

This module is a deliberate replacement for ``eval()`` in the QASM parsers
(``qasm_line_parser`` and ``qasm_base_parser``).  Calling ``eval()`` on
parameter strings extracted from QASM source allows arbitrary Python code
execution if an attacker can supply (or persuade a user to load) crafted
QASM input — the classic ``__import__('os').system('...')`` payload would
run inside the user's process with all of their permissions.

``safe_eval_param`` parses the expression with :mod:`ast` and walks an
explicit allow-list of node types.  Only numeric constants, the symbols
``pi`` / ``e``, basic arithmetic operators, and a small set of
:mod:`math` functions are permitted.  Anything else — attribute access,
subscripts, comprehensions, lambdas, calls to non-whitelisted names,
access to ``__builtins__`` / ``__class__`` / ``__import__``, etc. — raises
``ValueError``.  There is *no* fallback to ``eval()``.
"""

from __future__ import annotations

import ast
import math

__all__ = ["safe_eval_param"]


_ALLOWED_BINOPS: tuple[type[ast.operator], ...] = (
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
)

_ALLOWED_UNARYOPS: tuple[type[ast.unaryop], ...] = (
    ast.UAdd,
    ast.USub,
)

_ALLOWED_NAMES: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
}

_ALLOWED_FUNCS: dict[str, object] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sqrt": math.sqrt,
    "ceil": math.ceil,
    "floor": math.floor,
    "fabs": math.fabs,
    "pow": math.pow,
}


def _reject(node: ast.AST) -> ValueError:
    return ValueError(f"Unsafe QASM expression: disallowed syntax {type(node).__name__!s}")


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsafe QASM expression: non-numeric constant {node.value!r}")
        return float(node.value)

    if isinstance(node, ast.Name):
        if node.id not in _ALLOWED_NAMES:
            raise ValueError(f"Unsafe QASM expression: unknown name {node.id!r}")
        return float(_ALLOWED_NAMES[node.id])

    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise ValueError(f"Unsafe QASM expression: disallowed operator {type(node.op).__name__}")
        left = _eval(node.left)
        right = _eval(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise _reject(node.op)  # pragma: no cover — guarded above

    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARYOPS):
            raise ValueError(f"Unsafe QASM expression: disallowed unary operator {type(node.op).__name__}")
        operand = _eval(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        return -operand

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Unsafe QASM expression: only direct calls to whitelisted math functions are permitted")
        fname = node.func.id
        if fname not in _ALLOWED_FUNCS:
            raise ValueError(f"Unsafe QASM expression: function {fname!r} is not in the allow-list")
        if node.keywords:
            raise ValueError("Unsafe QASM expression: keyword arguments are not permitted")
        args = [_eval(a) for a in node.args]
        return float(_ALLOWED_FUNCS[fname](*args))  # type: ignore[operator]

    raise _reject(node)


def safe_eval_param(expr: str) -> float:
    """Safely evaluate a QASM numeric parameter expression.

    Parameters
    ----------
    expr:
        Parameter expression as it appears in QASM source, e.g.
        ``"pi/2"`` or ``"sin(0.5) + cos(0.5)**2"``.

    Returns
    -------
    float
        The evaluated value.

    Raises
    ------
    ValueError
        If ``expr`` cannot be parsed, or contains any syntax / identifier
        outside the safe allow-list.  This is raised *instead of* — never
        in addition to — falling back to ``eval()``.
    """
    if not isinstance(expr, str):
        raise ValueError(f"Unsafe QASM expression: expected str, got {type(expr).__name__}")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Unsafe QASM expression: parse error: {exc}") from exc

    # Pre-walk to reject any forbidden node anywhere in the tree.
    for node in ast.walk(tree):
        if isinstance(node, ast.Load):
            continue
        if isinstance(
            node,
            (
                ast.Expression,
                ast.Constant,
                ast.Name,
                ast.BinOp,
                ast.UnaryOp,
                ast.Call,
            ),
        ):
            continue
        if isinstance(node, _ALLOWED_BINOPS) or isinstance(node, _ALLOWED_UNARYOPS):
            continue
        raise ValueError(f"Unsafe QASM expression: disallowed syntax {type(node).__name__!s}")

    return float(_eval(tree))
