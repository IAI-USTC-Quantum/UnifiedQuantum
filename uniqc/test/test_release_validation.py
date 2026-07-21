from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.check_release import (
    changelog_contains_version,
    tag_is_reachable_from,
    validate_wheels,
    version_from_tag,
    wheel_version,
)


def test_version_from_tag_requires_strict_semver() -> None:
    assert version_from_tag("v1.2.3") == "1.2.3"
    with pytest.raises(ValueError, match="vMAJOR.MINOR.PATCH"):
        version_from_tag("release-1.2.3")


def test_changelog_contains_release_heading(tmp_path: Path) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [1.2.3] - 2026-07-21\n", encoding="utf-8")
    assert changelog_contains_version(changelog, "1.2.3")
    assert not changelog_contains_version(changelog, "1.2.4")


def test_wheel_version_must_match_release() -> None:
    matching = Path("unified_quantum-1.2.3-cp312-cp312-manylinux.whl")
    stale = Path("unified_quantum-1.2.2-cp312-cp312-manylinux.whl")

    assert wheel_version(matching) == "1.2.3"
    assert validate_wheels([matching], "1.2.3") == []
    assert "does not match" in validate_wheels([stale], "1.2.3")[0]


def test_tag_must_be_reachable_from_main_ref(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("release\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "release"], cwd=tmp_path, check=True)
    subprocess.run(["git", "tag", "v1.2.3"], cwd=tmp_path, check=True)

    assert tag_is_reachable_from("v1.2.3", "main", cwd=tmp_path)

    subprocess.run(["git", "checkout", "-q", "--orphan", "unrelated"], cwd=tmp_path, check=True)
    tracked.write_text("unrelated\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "unrelated"], cwd=tmp_path, check=True)
    assert not tag_is_reachable_from("v1.2.3", "unrelated", cwd=tmp_path)
