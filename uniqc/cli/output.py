"""Output formatting utilities for CLI."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import rich.box
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .refs import AI_HINTS, CMD_REFS, DOCS_URL, GITHUB_URL

console = Console()
err_console = Console(stderr=True)

# ----------------------------------------------------------------------
# Shared --ai-hints option (hidden; injected into every command)
# ----------------------------------------------------------------------
AI_HINTS_OPTION = typer.Option(
    False,
    "--ai-hints",
    "--ai-hint",
    help="Show AI workflow hints for this command (also enabled via UNIQC_AI_HINTS=1)",
    is_eager=True,
    hidden=True,
)


def _truthy(value: str | None) -> bool:
    """Return True for common opt-in environment/config strings."""
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def config_ai_hints_enabled() -> bool:
    """Return True when ~/.uniqc/config.yaml enables AI hints globally."""
    try:
        from uniqc.config import get_always_ai_hints

        return get_always_ai_hints()
    except Exception:
        return False


def ai_hints_enabled(ai_hints: bool = False) -> bool:
    """Return True if AI hints should be shown."""
    if ai_hints:
        return True
    if _truthy(os.environ.get("UNIQC_AI_HINTS")):
        return True
    return config_ai_hints_enabled()


def build_ref_str(command: str) -> str:
    """Return a single-line reference string for embedding in HELP constants."""
    refs = CMD_REFS.get(command)
    if not refs:
        return ""
    parts = []
    for label, url in refs:
        parts.append(f"[link={url}][cyan]{label}[/cyan][/link]")
    return "  |  ".join(parts)


def print_ai_hints(command: str) -> None:
    """Print AI workflow hints for the given command as a styled Rich panel."""
    hints = AI_HINTS.get(command)
    if not hints:
        return

    lines: list[str] = []
    for label, text in hints:
        lines.append(f"[bold white]{label}[/bold white]")
        lines.append(f"  {text}")
        lines.append("")

    console.print(
        Panel(
            "\n".join(lines).rstrip(),
            title="[bold cyan]AI Workflow Hints[/bold cyan]  (pass --ai-hints/--ai-hint, set UNIQC_AI_HINTS=1, or run uniqc config always-ai-hint on)",
            border_style="cyan",
            box=rich.box.ROUNDED,
            padding=(1, 2),
        )
    )


def _key_to_int(key: Any) -> int | None:
    """Best-effort conversion of a result key to an integer basis state.

    Returns ``None`` when the key is not a recognizable integer / hex /
    binary string.
    """
    if isinstance(key, bool):
        return None
    if isinstance(key, int):
        return key
    if not isinstance(key, str):
        return None
    if key.startswith("0x") or key.startswith("0X"):
        try:
            return int(key, 16)
        except ValueError:
            return None
    if key and all(ch in "01" for ch in key):
        try:
            return int(key, 2)
        except ValueError:
            return None
    return None


def _normalize_state_key(key: Any, *, n_qubits: int | None = None) -> str:
    """Return a binary bitstring for ``key``.

    Accepts plain binary strings, hex strings (``"0x..."``) or integers.
    Hex / int keys are zero-padded to ``n_qubits`` when known; binary strings
    are passed through unchanged so already-canonical inputs stay stable.
    """
    if isinstance(key, int):
        width = max(n_qubits or key.bit_length(), 1)
        return format(key, f"0{width}b")
    key_str = str(key)
    if key_str.startswith("0x") or key_str.startswith("0X"):
        try:
            int_val = int(key_str, 16)
        except ValueError:
            return key_str
        width = max(n_qubits or int_val.bit_length(), 1)
        return format(int_val, f"0{width}b")
    return key_str


def _looks_like_counts(mapping: dict[str, Any]) -> bool:
    """Return True if ``mapping`` looks like integer measurement counts."""
    if not mapping:
        return False
    for value in mapping.values():
        if isinstance(value, bool):
            return False
        if isinstance(value, int):
            continue
        if isinstance(value, float) and value.is_integer() and value > 1:
            # Some backends store counts as whole-number floats (e.g. 512.0).
            continue
        return False
    return True


def extract_counts_and_probs(
    result: Any,
    *,
    shots: int | None = None,
) -> tuple[dict[str, int], dict[str, float]]:
    """Normalize a backend result payload into ``(counts, probabilities)``.

    Task results arrive in several different shapes depending on the adapter:

    - ``{"counts": {...}, "probabilities": {...}}`` (dummy / quafu)
    - ``{"counts": {...}}`` or ``{"probabilities": {...}}`` alone
    - ``[{"key": "0x..", "value": prob}, ...]`` (originq single task)
    - ``[{"0x..": int, ...}, ...]`` (IBM: list of per-circuit count dicts)
    - flat ``{"state": int}`` / ``{"state": prob}`` (legacy / simple)

    This helper returns a uniform ``(counts, probabilities)`` pair so CLI
    displays don't have to sprinkle shape checks everywhere. ``counts`` may
    be empty when the backend only exposed probabilities and ``shots`` was
    not provided.
    """
    if not result:
        return {}, {}

    # ---- Nested "counts" / "probabilities" envelope -----------------------
    if isinstance(result, dict) and (
        "counts" in result or "probabilities" in result
    ):
        raw_counts = result.get("counts") or {}
        raw_probs = result.get("probabilities") or {}

        counts: dict[str, int] = {
            _normalize_state_key(k): int(v) for k, v in raw_counts.items()
        }
        probs: dict[str, float] = {
            _normalize_state_key(k): float(v) for k, v in raw_probs.items()
        }

        if counts and not probs:
            total = sum(counts.values()) or 1
            probs = {k: v / total for k, v in counts.items()}
        elif probs and not counts and shots:
            counts = {k: int(round(p * shots)) for k, p in probs.items()}

        return counts, probs

    # ---- originq list of {"key": ..., "value": ...} ------------------------
    if (
        isinstance(result, list)
        and result
        and isinstance(result[0], dict)
        and "key" in result[0]
        and "value" in result[0]
    ):
        raw_pairs: list[tuple[int | str, float]] = []
        for entry in result:
            key = entry.get("key")
            if key is None:
                continue
            int_key = _key_to_int(key)
            raw_pairs.append((int_key if int_key is not None else str(key), float(entry.get("value", 0.0))))

        width = max(
            (k.bit_length() for k, _ in raw_pairs if isinstance(k, int)),
            default=1,
        )
        probs_list: dict[str, float] = {}
        for key, val in raw_pairs:
            bin_key = format(key, f"0{max(width, 1)}b") if isinstance(key, int) else key
            probs_list[bin_key] = probs_list.get(bin_key, 0.0) + val

        counts_list: dict[str, int] = {}
        if shots:
            counts_list = {k: int(round(p * shots)) for k, p in probs_list.items()}
        return counts_list, probs_list

    # ---- IBM-style list of count dicts ------------------------------------
    if isinstance(result, list) and result and isinstance(result[0], dict):
        # Collect every (possibly hex) key as an int (or fall back to the
        # original string) so we can zero-pad to a consistent width.
        collected: list[tuple[int | str, int]] = []
        for entry in result:
            for k, v in entry.items():
                try:
                    count = int(v)
                except (TypeError, ValueError):
                    continue
                int_key = _key_to_int(k)
                collected.append(
                    (int_key if int_key is not None else str(k), count)
                )

        width = max(
            (k.bit_length() for k, _ in collected if isinstance(k, int)),
            default=1,
        )
        merged: dict[str, int] = {}
        for key, count in collected:
            bin_key = format(key, f"0{max(width, 1)}b") if isinstance(key, int) else key
            merged[bin_key] = merged.get(bin_key, 0) + count

        total = sum(merged.values()) or 1
        probs_merged = {k: v / total for k, v in merged.items()}
        return merged, probs_merged

    # ---- Flat dict: either counts or probabilities ------------------------
    if isinstance(result, dict):
        if _looks_like_counts(result):
            counts = {_normalize_state_key(k): int(v) for k, v in result.items()}
            total = sum(counts.values()) or 1
            probs = {k: v / total for k, v in counts.items()}
            return counts, probs

        # Treat as probabilities.
        probs = {_normalize_state_key(k): float(v) for k, v in result.items()}
        counts = (
            {k: int(round(p * shots)) for k, p in probs.items()} if shots else {}
        )
        return counts, probs

    return {}, {}


def print_table(
    title: str,
    columns: list[str],
    rows: list[list[Any]],
) -> None:
    """Print a rich table to console."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)


def print_json(data: dict[str, Any] | list[Any]) -> None:
    """Print data as JSON to stdout."""
    console.print(json.dumps(data, indent=2, ensure_ascii=False))


def print_error(message: str) -> None:
    """Print error message to stderr."""
    err_console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def format_prob(value: float) -> str:
    """Format probability as percentage string."""
    return f"{value * 100:.1f}%"


def write_output(content: str, output: str | None = None) -> None:
    """Write content to file or stdout."""
    if output:
        with open(output, "w") as f:
            f.write(content)
        print_success(f"Output written to {output}")
    else:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
