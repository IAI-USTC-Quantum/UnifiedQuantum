"""Configuration management subcommand."""

from __future__ import annotations

import os

import typer

from .output import (
    AI_HINTS_OPTION,
    build_ref_str,
    console,
    print_ai_hints,
    print_error,
    print_json,
    print_success,
    print_table,
)

app = typer.Typer(
    help=(
        "Manage API key and configuration\n"
        f"  {build_ref_str('config')}"
    ),
)


@app.command()
def init(
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Initialize configuration file with default values.

    Workflow:
      - Next: uniqc config set originq.token <YOUR_TOKEN>
      - Then: uniqc config validate
      - Then: uniqc backend update
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("config")

    from uniqc.backend_adapter.config import create_default_config

    create_default_config()
    print_success("Configuration file created at ~/.uniqc/config.yaml")


@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key (e.g., originq.token)"),
    value: str = typer.Argument(..., help="Configuration value"),
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Set a configuration value.

    Workflow:
      - After setting a token, validate it: uniqc config validate
      - Then fetch backends: uniqc backend update
      - Use --profile to set values for a named profile instead of 'default'.
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("config")

    parts = key.split(".")
    if len(parts) != 2:
        print_error("Key must be in format 'platform.field' (e.g., originq.token)")
        raise typer.Exit(1)

    platform_name, field = parts
    platform_name = platform_name.lower()

    if platform_name not in ("originq", "quafu", "ibm"):
        print_error(f"Unknown platform: {platform_name}. Use originq/quafu/ibm.")
        raise typer.Exit(1)

    from uniqc.backend_adapter.config import update_platform_config

    update_platform_config(platform_name, {field: value}, profile=profile)
    print_success(f"Set {key} = {value[:8]}...")


@app.command()
def get(
    platform: str = typer.Argument(..., help="Platform name: originq/quafu/ibm"),
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Get configuration for a platform."""
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("config")

    from uniqc.backend_adapter.config import get_platform_config

    platform = platform.lower()
    config = get_platform_config(platform, profile=profile)

    if not config:
        print_error(f"No configuration found for {platform} (profile: {profile})")
        raise typer.Exit(1)

    rows = []
    for key, value in config.items():
        if key == "token" and value:
            display = f"{value[:8]}..." if len(value) > 8 else value
        elif isinstance(value, list):
            display = ", ".join(map(str, value)) if value else "(empty)"
        elif isinstance(value, dict):
            display = str(value) if value else "(empty)"
        else:
            display = str(value) if value else "(not set)"
        rows.append([key, display])

    print_table(f"{platform.upper()} Configuration", ["Field", "Value"], rows)


@app.command("list")
def list_config(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table/json"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """List all platform configurations."""
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("config")

    from uniqc.backend_adapter.config import PLATFORM_REQUIRED_FIELDS, load_config

    config = load_config()

    if profile not in config:
        print_error(f"Profile '{profile}' not found")
        raise typer.Exit(1)

    profile_config = config[profile]
    results = []

    for platform in ("originq", "quafu", "ibm"):
        platform_config = profile_config.get(platform, {})
        token = platform_config.get("token", "")
        required = PLATFORM_REQUIRED_FIELDS.get(platform, [])

        status = "[green]Configured[/green]" if token else "[red]Missing token[/red]"

        missing = [f for f in required if not platform_config.get(f)]
        if missing and token:
            status = f"[yellow]Missing: {', '.join(missing)}[/yellow]"

        results.append(
            {
                "platform": platform,
                "status": status,
                "has_token": bool(token),
            }
        )

    if format == "json":
        print_json(results)
    else:
        rows = [[r["platform"], r["status"]] for r in results]
        print_table("Platform Configuration Status", ["Platform", "Status"], rows)


@app.command()
def validate(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Validate current configuration."""
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("config")

    from uniqc.backend_adapter.config import validate_config

    errors = validate_config()

    if not errors:
        print_success("Configuration is valid")
    else:
        print_error("Configuration has errors:")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(1)


@app.command()
def profile(
    action: str = typer.Argument(..., help="Action: list/use/create"),
    name: str | None = typer.Argument(None, help="Profile name"),
    ai_hints: bool = AI_HINTS_OPTION,
):
    """Manage configuration profiles.

    Workflow:
      - List profiles: uniqc config profile list
      - Switch to a profile: uniqc config profile use <NAME>
      - Create a new profile: uniqc config profile create <NAME>
    """
    if ai_hints or os.environ.get("UNIQC_AI_HINTS"):
        print_ai_hints("config")

    from uniqc.backend_adapter.config import get_active_profile, load_config, set_active_profile

    if action == "list":
        from uniqc.backend_adapter.config import META_KEYS

        config = load_config()
        active = get_active_profile()
        rows = []
        for profile_name in config:
            if profile_name in META_KEYS:
                continue
            marker = "[green]*[/green]" if profile_name == active else " "
            rows.append([marker, profile_name])
        print_table("Profiles", ["Active", "Name"], rows)

    elif action == "use":
        if not name:
            print_error("Profile name required")
            raise typer.Exit(1)
        set_active_profile(name)
        print_success(f"Switched to profile '{name}'")

    elif action == "create":
        if not name:
            print_error("Profile name required")
            raise typer.Exit(1)
        from uniqc.backend_adapter.config import load_config, save_config

        config = load_config()
        if name in config:
            print_error(f"Profile '{name}' already exists")
            raise typer.Exit(1)
        config[name] = {
            "originq": {"token": ""},
            "quafu": {"token": ""},
            "ibm": {"token": "", "proxy": {"http": "", "https": ""}},
        }
        save_config(config)
        print_success(f"Created profile '{name}'")

    else:
        print_error(f"Unknown action: {action}. Use list/use/create.")
        raise typer.Exit(1)
