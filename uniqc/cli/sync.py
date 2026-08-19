"""``uniqc sync`` — sync platform credentials with Infisical.

Core flatten/encode/Infisical-adapter logic and the typer commands live in
this module; the package root intentionally stays limited to boundary
modules (see ``uniqc/test/test_package_structure.py``).

Secret layout
=============
Each flattened config value becomes one Infisical secret named::

    UNIQC_<PROFILE>_<PLATFORM>_<FIELD-PATH>

with every segment upper-cased and ``.`` replaced by ``_``.  For example
``default.originq.token`` -> ``UNIQC_DEFAULT_ORIGINQ_TOKEN`` and
``default.ibm.proxy.http`` -> ``UNIQC_DEFAULT_IBM_PROXY_HTTP``.

Value encoding
==============
Secret values are strings, but the YAML config also holds ints, bools,
lists and dicts.  Plain strings are stored verbatim (so tokens stay
directly consumable via ``infisical run``); anything else — and strings
that would be ambiguous (``json:`` prefix) or misread by the CLI (leading
``@`` means "load from file") — is stored as ``json:`` plus its JSON
serialization.  Only ``UNIQC_`` secrets that parse back into a known
platform are managed; everything else in the project is untouched.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

import typer

from uniqc.config import META_KEYS, PLATFORM_KNOWN_FIELDS, SUPPORTED_PLATFORMS

from . import sync_cmd
from .output import (
    AI_HINTS_OPTION,
    ai_hints_enabled,
    build_ref_str,
    console,
    print_ai_hints,
    print_error,
    print_json,
    print_success,
    print_table,
    print_warning,
)

#: Prefix for every secret managed by this module.
SECRET_PREFIX = "UNIQC_"

#: Marker for values that must be JSON-decoded on pull.
_JSON_TAG = "json:"

#: Field names whose canonical casing must survive the upper-casing of
#: secret names (``QUARK_API_KEY`` is upper-case in the YAML schema).
_CASE_SENSITIVE_FIELDS = frozenset({"QUARK_API_KEY"})


class SyncError(Exception):
    """Raised when a sync operation cannot be completed."""


# ---------------------------------------------------------------------------
# Value encoding / decoding
# ---------------------------------------------------------------------------


def encode_value(value: Any) -> str:
    """Encode a config value into its secret-string form.

    Plain strings are stored verbatim so other tools can consume tokens
    directly.  Strings that would be ambiguous (``json:`` prefix) or that
    the infisical CLI would misinterpret on the command line (leading
    ``@`` means "read value from file") are JSON-encoded like non-strings.
    """
    if isinstance(value, str):
        if value.startswith(_JSON_TAG) or value.startswith("@") or "\n" in value:
            return _JSON_TAG + json.dumps(value)
        return value
    return _JSON_TAG + json.dumps(value, sort_keys=True, ensure_ascii=False)


def decode_value(raw: str) -> Any:
    """Decode a secret string back into its config value."""
    if not raw.startswith(_JSON_TAG):
        return raw
    try:
        return json.loads(raw[len(_JSON_TAG):])
    except json.JSONDecodeError as e:
        raise SyncError(
            f"Secret value starts with '{_JSON_TAG}' but is not valid JSON: {e}"
        ) from e


# ---------------------------------------------------------------------------
# Flatten / unflatten
# ---------------------------------------------------------------------------


def _flatten_mapping(prefix: str, value: dict[str, Any], out: dict[str, str]) -> None:
    for key, nested in value.items():
        segment = str(key).upper()
        if isinstance(nested, dict):
            _flatten_mapping(f"{prefix}_{segment}", nested, out)
        elif nested in ("", None, [], {}):
            continue  # unset values are not synced
        else:
            out[f"{prefix}_{segment}"] = encode_value(nested)


def flatten_config(config: dict[str, Any]) -> dict[str, str]:
    """Flatten a full config dict into ``{secret_name: encoded_value}``.

    Meta keys (``active_profile``, ``always_ai_hints``, ``sync``) are
    machine-local and never synced.  Only known platforms are considered.
    """
    out: dict[str, str] = {}
    for profile_name, profile_config in config.items():
        if profile_name in META_KEYS or not isinstance(profile_config, dict):
            continue
        for platform in SUPPORTED_PLATFORMS:
            platform_config = profile_config.get(platform)
            if isinstance(platform_config, dict):
                _flatten_mapping(
                    f"{SECRET_PREFIX}{profile_name.upper()}_{platform.upper()}",
                    platform_config,
                    out,
                )
    return out


def _canonical_field(segment: str) -> str:
    """Recover a field's canonical casing from its upper-cased segment."""
    if segment in _CASE_SENSITIVE_FIELDS:
        return segment
    return segment.lower()


#: Known field names per platform: upper-case name -> canonical name.
_KNOWN_FIELD_CANONICAL: dict[str, dict[str, str]] = {
    platform: {f.upper(): f for f in fields}
    for platform, fields in PLATFORM_KNOWN_FIELDS.items()
}


def parse_secret_name(name: str) -> tuple[str, str, list[str]] | None:
    """Split ``UNIQC_<profile>_<platform>_<fields...>`` into its parts.

    Returns ``(profile, platform, field_path)`` or ``None`` when the name
    does not follow the uniqc layout.

    Ambiguity: both profiles and multi-word field names may contain
    underscores, and a profile may even embed a platform name.  Every
    token position that could be the platform yields a candidate split;
    candidates whose field path matches the platform's known field
    vocabulary win — a full-path match (``QUARK_API_KEY``,
    ``TASK_GROUP_SIZE``) yields a single multi-word field, a first-token
    match (``PROXY_HTTP``) yields a nested path.  This keeps ``QUARK`` in
    ``UNIQC_DEFAULT_QUARK_QUARK_API_KEY`` from being mistaken for the
    platform.  Without a vocabulary match (custom fields), the rightmost
    platform candidate is used and the path is treated as nested.
    """
    if not name.startswith(SECRET_PREFIX):
        return None
    tokens = name[len(SECRET_PREFIX):].split("_")
    if len(tokens) < 3:
        return None

    candidates: list[tuple[str, str, list[str]]] = []
    for idx in range(1, len(tokens) - 1):
        platform = tokens[idx].lower()
        if platform not in SUPPORTED_PLATFORMS:
            continue
        profile = "_".join(tokens[:idx]).lower()
        fields = tokens[idx + 1:]
        if not profile or not fields:
            continue
        candidates.append((profile, platform, fields))

    if not candidates:
        return None

    for profile, platform, fields in candidates:
        known = _KNOWN_FIELD_CANONICAL.get(platform, {})
        full = "_".join(fields).upper()
        if full in known:
            return profile, platform, [known[full]]
        if fields[0].upper() in known:
            return profile, platform, [_canonical_field(t) for t in fields]

    profile, platform, fields = candidates[-1]
    return profile, platform, [_canonical_field(t) for t in fields]


def unflatten_secrets(secrets: dict[str, str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Rebuild ``{profile: {platform: {...}}}`` from synced secrets.

    Returns the config tree plus a list of ``UNIQC_``-prefixed names that
    could not be parsed (left untouched by sync; reported as warnings).
    """
    profiles: dict[str, dict[str, Any]] = {}
    skipped: list[str] = []
    for name in sorted(secrets):
        parsed = parse_secret_name(name)
        if parsed is None:
            if name.startswith(SECRET_PREFIX):
                skipped.append(name)
            continue
        profile, platform, fields = parsed
        target = profiles.setdefault(profile, {}).setdefault(platform, {})
        for field in fields[:-1]:
            target = target.setdefault(field, {})
        target[fields[-1]] = decode_value(secrets[name])
    return profiles, skipped


def secret_name_to_display(name: str) -> str:
    """Render a secret name as a friendly dotted config key for tables."""
    parsed = parse_secret_name(name)
    if parsed is None:
        return name
    profile, platform, fields = parsed
    return ".".join([profile, platform, *fields])


# ---------------------------------------------------------------------------
# Infisical CLI adapter
# ---------------------------------------------------------------------------


def run_infisical(args: list[str], *, token: str | None = None, confirm: str | None = None) -> str:
    """Run an ``infisical`` CLI invocation and return its stdout.

    Raises :class:`SyncError` when the binary is missing or the command
    fails, embedding the tail of stderr to surface the actual cause
    (expired login, wrong project id, network errors, ...).
    """
    binary = shutil.which("infisical")
    if binary is None:
        raise SyncError(
            "The 'infisical' CLI was not found on PATH. "
            "Install it (https://infisical.com/docs/cli/overview) and run 'infisical login', "
            "or use UNIQC_INFISICAL_TOKEN with a machine identity token."
        )

    cmd = [binary, *args, "--silent"]
    if token:
        cmd += ["--token", token]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            input=confirm,
        )
    except subprocess.TimeoutExpired as e:
        raise SyncError("infisical CLI timed out after 90s") from e
    except OSError as e:
        raise SyncError(f"Failed to launch infisical CLI: {e}") from e

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        tail = " | ".join(line.strip() for line in detail[-3:]) or "no output"
        raise SyncError(f"infisical CLI failed (exit {result.returncode}): {tail}")

    return result.stdout


def _common_flags(project_id: str, env: str) -> list[str]:
    return ["--projectId", project_id, "--env", env]


def fetch_remote_secrets(project_id: str, env: str, token: str | None = None) -> dict[str, str]:
    """Fetch all uniqc-managed secrets from the given project/environment."""
    out = run_infisical(["secrets", "-o", "json", *_common_flags(project_id, env)], token=token)
    try:
        payload = json.loads(out or "null")
    except json.JSONDecodeError as e:
        raise SyncError(f"Could not parse infisical output as JSON: {e}") from e
    if not payload:
        return {}
    return {s["secretKey"]: s["secretValue"] for s in payload if s.get("secretKey")}


def push_secrets(
    secrets: dict[str, str],
    project_id: str,
    env: str,
    token: str | None = None,
) -> None:
    """Upsert the given ``{name: encoded_value}`` secrets (one CLI batch)."""
    if not secrets:
        return
    assignments = [f"{name}={value}" for name, value in secrets.items()]
    run_infisical(
        ["secrets", "set", *assignments, "--type", "shared", *_common_flags(project_id, env)],
        token=token,
    )


def delete_remote_secret(name: str, project_id: str, env: str, token: str | None = None) -> bool:
    """Delete one secret, answering the CLI's confirmation prompt.

    Returns ``False`` when the secret no longer exists (the CLI aborts a
    delete on missing names), so prune loops tolerate races.
    """
    try:
        run_infisical(
            ["secrets", "delete", name, "--type", "shared", *_common_flags(project_id, env)],
            token=token,
            confirm="y\n",
        )
    except SyncError:
        return False
    return True


# ---------------------------------------------------------------------------
# Settings resolution
# ---------------------------------------------------------------------------


def resolve_sync_settings(
    project_id: str | None,
    env: str | None,
    config: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Resolve ``(project_id, env)`` from flags, env vars, and stored config.

    Precedence: CLI flag > environment variable > ``sync`` section of the
    config file.  ``env`` defaults to ``dev`` (the Infisical CLI default).
    """
    from uniqc.config import load_config

    stored: dict[str, Any] = (config if config is not None else load_config()).get("sync", {}) or {}

    resolved_id = (
        project_id
        or os.environ.get("UNIQC_INFISICAL_PROJECT_ID")
        or stored.get("project_id")
    )
    resolved_env = (
        env
        or os.environ.get("UNIQC_INFISICAL_ENV")
        or stored.get("env")
        or "dev"
    )
    if not resolved_id:
        raise SyncError(
            "No Infisical project configured. Run 'uniqc sync setup --project-id <ID>', "
            "set UNIQC_INFISICAL_PROJECT_ID, or pass --project-id."
        )
    return str(resolved_id), str(resolved_env)


def get_infisical_token() -> str | None:
    """Optional machine-identity / service token for CI usage."""
    return os.environ.get("UNIQC_INFISICAL_TOKEN")


# ---------------------------------------------------------------------------
# Change computation
# ---------------------------------------------------------------------------


def compute_changes(
    local: dict[str, str],
    remote: dict[str, str],
) -> dict[str, list[str]]:
    """Compare local and remote secret maps.

    Returns ``{"push_add", "push_change", "prune", "pull_add", "pull_change"}``
    where each list contains secret names.  ``prune`` names remote secrets
    absent locally (stale), and ``pull_*`` mirror ``push_*`` in the other
    direction.
    """
    push_add = sorted(n for n in local if n not in remote)
    push_change = sorted(n for n in local if n in remote and remote[n] != local[n])
    prune = sorted(n for n in remote if n not in local)
    pull_add = sorted(n for n in remote if n not in local)
    pull_change = sorted(n for n in remote if n in local and remote[n] != local[n])
    return {
        "push_add": push_add,
        "push_change": push_change,
        "prune": prune,
        "pull_add": pull_add,
        "pull_change": pull_change,
    }


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------


def backup_config_file(config_path) -> str | None:
    """Copy the config file aside; return the backup path or None."""
    from datetime import datetime

    if not config_path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = config_path.with_name(f"{config_path.name}.bak-{stamp}")
    shutil.copy2(config_path, backup_path)
    return str(backup_path)


app = typer.Typer(
    help=(
        "Sync ~/.uniqc/config.yaml with an Infisical secrets project\n"
        "  ('upload' is an independent confsync-based alternative)\n"
        f"  {build_ref_str('sync')}"
    ),
    no_args_is_help=True,
)

# ``uniqc sync upload`` — confsync backend (see sync_cmd.py).  Independent
# of the Infisical subcommands; confsync-client stays an optional, lazily
# imported dependency.
app.command()(sync_cmd.upload)

PROJECT_ID_OPTION = typer.Option(
    None,
    "--project-id",
    help="Infisical project ID (overrides sync settings and UNIQC_INFISICAL_PROJECT_ID)",
)
ENV_OPTION = typer.Option(
    None,
    "--env",
    "-e",
    help="Infisical environment (default: dev, or the stored sync setting)",
)
FORMAT_OPTION = typer.Option("table", "--format", "-f", help="Output format: table/json")


def _sync_error_exit(e: Exception) -> None:
    print_error(str(e))
    raise typer.Exit(1)


def _load_local_and_remote(project_id: str | None, env: str | None):
    from uniqc.config import load_config

    try:
        config = load_config()
        resolved_id, resolved_env = resolve_sync_settings(project_id, env, config)
        local = flatten_config(config)
        fetched = fetch_remote_secrets(resolved_id, resolved_env, get_infisical_token())
        # Only secrets following the uniqc layout are managed; anything
        # else in the project is invisible to push/pull/prune.
        remote = {n: v for n, v in fetched.items() if parse_secret_name(n) is not None}
        changes = compute_changes(local, remote)
        _, skipped = unflatten_secrets(fetched)
    except Exception as e:  # SyncError, ConfigError, ...
        _sync_error_exit(e)
        raise  # unreachable
    return config, resolved_id, resolved_env, local, remote, changes, skipped


def _print_changes(
    title: str,
    changes: dict[str, list[str]],
    keys: list[tuple[str, str]],
    resolved_env: str,
) -> None:
    rows = []
    for change_key, label in keys:
        for name in changes.get(change_key, []):
            rows.append([secret_name_to_display(name), label])
    if rows:
        print_table(title, ["Config key", "Change"], rows)
    else:
        print_success(f"{title}: no differences (env: {resolved_env})")


def _warn_skipped(skipped: list[str]) -> None:
    for name in skipped:
        print_warning(
            f"Ignored unparsable secret '{name}' (not managed by uniqc sync layout)"
        )


@app.command()
def setup(
    project_id: str = typer.Option(..., "--project-id", help="Infisical project ID"),
    env: str = typer.Option("dev", "--env", "-e", help="Default Infisical environment"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Store Infisical sync settings in ~/.uniqc/config.yaml.

    Workflow:
      - First: infisical login
      - Next: uniqc sync setup --project-id <ID>
      - Then: uniqc sync status  (preview differences)
      - Then: uniqc sync push / uniqc sync pull
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("sync")

    from uniqc.config import load_config, save_config

    config = load_config()
    sync_settings = config.setdefault("sync", {})
    sync_settings["project_id"] = project_id
    sync_settings["env"] = env
    save_config(config)
    print_success(f"Sync settings saved (project: {project_id}, env: {env})")


@app.command()
def status(
    project_id: str | None = PROJECT_ID_OPTION,
    env: str | None = ENV_OPTION,
    format: str = FORMAT_OPTION,
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Compare local config with Infisical without changing anything."""
    if ai_hints_enabled(ai_hints):
        print_ai_hints("sync")

    _, resolved_id, resolved_env, local, remote, changes, skipped = _load_local_and_remote(
        project_id, env
    )
    _warn_skipped(skipped)

    if format == "json":
        print_json(
            {
                "project_id": resolved_id,
                "env": resolved_env,
                "push_add": [secret_name_to_display(n) for n in changes["push_add"]],
                "push_change": [secret_name_to_display(n) for n in changes["push_change"]],
                "prune": [secret_name_to_display(n) for n in changes["prune"]],
                "pull_add": [secret_name_to_display(n) for n in changes["pull_add"]],
                "pull_change": [secret_name_to_display(n) for n in changes["pull_change"]],
            }
        )
        return

    console.print(f"[bold]project:[/bold] {resolved_id}   [bold]env:[/bold] {resolved_env}")
    _print_changes(
        "Would push (local -> Infisical)",
        changes,
        [("push_add", "[green]add[/green]"), ("push_change", "[yellow]update[/yellow]")],
        resolved_env,
    )
    _print_changes(
        "Would pull (Infisical -> local)",
        changes,
        [("pull_add", "[green]add[/green]"), ("pull_change", "[yellow]update[/yellow]")],
        resolved_env,
    )
    if changes["prune"]:
        _print_changes(
            "Stale on remote (deleted by 'push --prune')",
            changes,
            [("prune", "[red]stale[/red]")],
            resolved_env,
        )


@app.command()
def push(
    project_id: str | None = PROJECT_ID_OPTION,
    env: str | None = ENV_OPTION,
    prune: bool = typer.Option(
        False, "--prune", help="Also delete remote uniqc secrets missing locally"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    format: str = FORMAT_OPTION,
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Upload local platform credentials to Infisical (local wins).

    Values already on the remote with different content are overwritten.
    Other tools' secrets in the project are never touched.
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("sync")

    _, resolved_id, resolved_env, local, remote, changes, skipped = _load_local_and_remote(
        project_id, env
    )
    _warn_skipped(skipped)

    if dry_run:
        if format == "json":
            print_json(
                {
                    "dry_run": True,
                    "add": [secret_name_to_display(n) for n in changes["push_add"]],
                    "change": [secret_name_to_display(n) for n in changes["push_change"]],
                    "prune": [secret_name_to_display(n) for n in changes["prune"]] if prune else [],
                }
            )
        else:
            _print_changes(
                "Would push (local -> Infisical)",
                changes,
                [("push_add", "[green]add[/green]"), ("push_change", "[yellow]update[/yellow]")],
                resolved_env,
            )
            if prune and changes["prune"]:
                _print_changes(
                    "Would delete on remote",
                    changes,
                    [("prune", "[red]delete[/red]")],
                    resolved_env,
                )
        return

    to_push = {n: local[n] for n in changes["push_add"] + changes["push_change"]}
    if not to_push and not (prune and changes["prune"]):
        print_success(f"Already in sync — nothing to push (env: {resolved_env})")
        return

    try:
        push_secrets(to_push, resolved_id, resolved_env, token=get_infisical_token())
        for name in changes["push_add"]:
            print_success(f"Created {secret_name_to_display(name)}")
        for name in changes["push_change"]:
            print_success(f"Updated {secret_name_to_display(name)}")
        if prune and changes["prune"]:
            for name in changes["prune"]:
                if delete_remote_secret(
                    name, resolved_id, resolved_env, get_infisical_token()
                ):
                    print_success(f"Deleted remote {secret_name_to_display(name)}")
                else:
                    print_warning(f"Could not delete remote {name} (already gone?)")
        print_success(f"Push complete (env: {resolved_env})")
    except Exception as e:
        _sync_error_exit(e)


@app.command()
def pull(
    project_id: str | None = PROJECT_ID_OPTION,
    env: str | None = ENV_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without writing"),
    no_backup: bool = typer.Option(
        False, "--no-backup", help="Skip the timestamped config backup before writing"
    ),
    format: str = FORMAT_OPTION,
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Download credentials from Infisical into ~/.uniqc/config.yaml (remote wins).

    Local profile sections are replaced by the remote state; machine-local
    keys (active_profile, always_ai_hints, sync, and platform-free sections
    such as gateway) are preserved.  A backup of the previous config is
    written next to it unless --no-backup.
    """
    if ai_hints_enabled(ai_hints):
        print_ai_hints("sync")

    config, resolved_id, resolved_env, local, remote, changes, skipped = _load_local_and_remote(
        project_id, env
    )
    _warn_skipped(skipped)

    if dry_run:
        if format == "json":
            print_json(
                {
                    "dry_run": True,
                    "add": [secret_name_to_display(n) for n in changes["pull_add"]],
                    "change": [secret_name_to_display(n) for n in changes["pull_change"]],
                    "local_only": [secret_name_to_display(n) for n in changes["push_add"]],
                }
            )
        else:
            _print_changes(
                "Would pull (Infisical -> local)",
                changes,
                [("pull_add", "[green]add[/green]"), ("pull_change", "[yellow]update[/yellow]")],
                resolved_env,
            )
            if changes["push_add"]:
                _print_changes(
                    "Local-only keys that would be dropped",
                    changes,
                    [("push_add", "[red]remove[/red]")],
                    resolved_env,
                )
        return

    from uniqc.config import CONFIG_FILE, save_config

    if not remote:
        print_error(
            f"No uniqc secrets found in project (env: {resolved_env}). "
            "Refusing to overwrite local config — check the project id/env."
        )
        raise typer.Exit(1)

    profiles, _ = unflatten_secrets(remote)

    def _is_profile_like(section: Any) -> bool:
        return isinstance(section, dict) and any(
            platform in section for platform in SUPPORTED_PLATFORMS
        )

    # Machine-local keys (meta, sync settings, and platform-free sections
    # such as `gateway`) survive; profile-like sections are replaced by the
    # remote state.
    new_config = {
        key: value
        for key, value in config.items()
        if key in META_KEYS or not _is_profile_like(value)
    }
    new_config.update(profiles)

    active = new_config.get("active_profile", "default")
    if active not in new_config:
        new_config["active_profile"] = (
            "default" if "default" in new_config else next(iter(profiles), "default")
        )
        print_warning(
            f"Active profile '{active}' not present remotely; "
            f"switched to '{new_config['active_profile']}'"
        )

    if not no_backup:
        backup = backup_config_file(CONFIG_FILE)
        if backup:
            console.print(f"[dim]Backup written to {backup}[/dim]")

    try:
        save_config(new_config)
        for name in changes["pull_add"]:
            print_success(f"Added {secret_name_to_display(name)}")
        for name in changes["pull_change"]:
            print_success(f"Updated {secret_name_to_display(name)}")
        for name in changes["push_add"]:
            console.print(f"[red]Removed[/red] {secret_name_to_display(name)}")
        print_success(f"Pull complete (env: {resolved_env})")
    except Exception as e:
        _sync_error_exit(e)
