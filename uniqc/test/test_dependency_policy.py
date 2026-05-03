from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION_OPERATORS = ("===", "~=", "==", "!=", "<=", ">=", "<", ">", "@")


def _dependency_entries(pyproject: dict) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []

    for requirement in pyproject.get("build-system", {}).get("requires", []):
        entries.append(("build-system.requires", requirement))

    for requirement in pyproject.get("project", {}).get("dependencies", []):
        entries.append(("project.dependencies", requirement))

    optional = pyproject.get("project", {}).get("optional-dependencies", {})
    for group, requirements in optional.items():
        for requirement in requirements:
            entries.append((f"project.optional-dependencies.{group}", requirement))

    dependency_groups = pyproject.get("dependency-groups", {})
    for group, requirements in dependency_groups.items():
        for requirement in requirements:
            entries.append((f"dependency-groups.{group}", requirement))

    return entries


def test_third_party_dependencies_are_not_version_pinned() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    constrained = [
        f"{section}: {requirement}"
        for section, requirement in _dependency_entries(pyproject)
        if any(operator in requirement for operator in VERSION_OPERATORS)
    ]

    assert constrained == []
