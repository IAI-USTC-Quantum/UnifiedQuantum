from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION_OPERATORS = ("===", "~=", "==", "!=", "<=", ">=", "<", ">", "@")


def _requirement_spec(requirement: str) -> str:
    """Return the package specifier part, excluding PEP 508 environment markers."""
    return requirement.split(";", 1)[0].strip()


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
        if any(operator in _requirement_spec(requirement) for operator in VERSION_OPERATORS)
    ]

    assert constrained == []


def test_quafu_extra_has_been_removed() -> None:
    """The legacy [quafu] extra is fully removed; pyquafu must not appear in any extra.

    The Quafu platform SDK (pyquafu) is deprecated and pulls numpy<2; users who still
    need it must install pyquafu manually. See docs/source/guide/installation.md.
    """
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = pyproject["project"]["optional-dependencies"]

    assert "quafu" not in optional, "[quafu] extra must be removed"
    for group, requirements in optional.items():
        assert all("pyquafu" not in requirement for requirement in requirements), (
            f"pyquafu unexpectedly listed under [{group}]"
        )


def test_qiskit_is_a_core_dependency() -> None:
    """qiskit, qiskit-aer, qiskit-ibm-runtime moved into project.dependencies.

    The legacy [qiskit] extra has been removed; qiskit is now part of the default install.
    """
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproject["project"]["dependencies"]
    optional = pyproject["project"]["optional-dependencies"]

    for pkg in ("qiskit", "qiskit-aer", "qiskit-ibm-runtime"):
        assert any(_requirement_spec(req).split("[", 1)[0] == pkg for req in deps), (
            f"{pkg} must be listed in project.dependencies"
        )
    assert "qiskit" not in optional, "[qiskit] extra must be removed"
