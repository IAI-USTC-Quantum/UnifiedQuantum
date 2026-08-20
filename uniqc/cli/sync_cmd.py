"""``uniqc sync upload`` — confsync backend for config sync.

This subcommand lives on the ``uniqc sync`` command group (registered in
``uniqc.cli.sync``) but is an independent backend: it talks to a self-hosted
confsync server through the optional ``confsync-client`` package, whereas the
other ``uniqc sync`` subcommands use Infisical.  No confsync settings live in
``~/.uniqc/config.yaml`` — credentials are shared from
``~/.confsync/credentials.json`` (one ``confsync login`` works for every app).
"""

from __future__ import annotations

import typer

from .output import (
    AI_HINTS_OPTION,
    ai_hints_enabled,
    print_ai_hints,
    print_error,
    print_success,
)


def _load_confsync():
    """Import confsync lazily; exit with an install hint when it is missing."""
    try:
        from confsync import ConfsyncError, load_client
    except ImportError as e:
        print_error(
            "confsync-client is not installed. "
            "Install it with `pip install confsync-client`, then run `confsync login --server <url>`."
        )
        raise typer.Exit(1) from e
    return ConfsyncError, load_client


def upload(
    name: str = typer.Option("config.yaml", "--name", "-n", help="Document name on the confsync server"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Upload the local configuration file to confsync.

    Pushes ~/.uniqc/config.yaml as the encrypted confsync document
    'uniqc/<name>'.
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("sync")

    from uniqc.config import CONFIG_FILE

    if not CONFIG_FILE.exists():
        print_error(f"Configuration file not found: {CONFIG_FILE}. Run `uniqc config init` first.")
        raise typer.Exit(1)

    ConfsyncError, load_client = _load_confsync()

    content = CONFIG_FILE.read_text(encoding="utf-8")
    try:
        with load_client() as client:
            version = client.push(app="uniqc", name=name, content=content)
    except ConfsyncError as e:
        print_error(f"Upload failed: {e}")
        raise typer.Exit(1) from e

    print_success(f"Configuration uploaded to confsync (uniqc/{name}, version {version})")
