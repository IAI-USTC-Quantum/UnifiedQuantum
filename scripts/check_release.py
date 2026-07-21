#!/usr/bin/env python3
"""Validate release tags and wheel versions before publishing."""

from __future__ import annotations

import argparse
import glob
import re
import subprocess
import sys
from pathlib import Path

TAG_RE = re.compile(r"^v(?P<version>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")
WHEEL_RE = re.compile(
    r"^[A-Za-z0-9_.]+-(?P<version>\d+\.\d+\.\d+(?:[A-Za-z0-9_.!+-]*))-[^-]+-[^-]+-[^-]+\.whl$"
)


def version_from_tag(tag: str) -> str:
    match = TAG_RE.fullmatch(tag)
    if match is None:
        raise ValueError(f"Release tag must use vMAJOR.MINOR.PATCH, got {tag!r}")
    return tag[1:]


def changelog_contains_version(changelog: Path, version: str) -> bool:
    heading = re.compile(rf"^## \[{re.escape(version)}\](?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?\s*$", re.MULTILINE)
    return heading.search(changelog.read_text(encoding="utf-8")) is not None


def tag_is_reachable_from(tag: str, main_ref: str, *, cwd: Path) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", tag, main_ref],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        detail = result.stderr.strip() or result.stdout.strip() or f"git exited with {result.returncode}"
        raise RuntimeError(f"Could not validate whether {tag} is reachable from {main_ref}: {detail}")
    return result.returncode == 0


def expand_wheels(patterns: list[str]) -> list[Path]:
    wheels: list[Path] = []
    for pattern in patterns:
        matches = [Path(match) for match in glob.glob(pattern)]
        if not matches and Path(pattern).exists():
            matches = [Path(pattern)]
        wheels.extend(matches)
    return sorted(set(wheels))


def wheel_version(wheel: Path) -> str:
    match = WHEEL_RE.fullmatch(wheel.name)
    if match is None:
        raise ValueError(f"Invalid wheel filename: {wheel.name}")
    return match.group("version")


def validate_wheels(wheels: list[Path], expected_version: str) -> list[str]:
    errors: list[str] = []
    if not wheels:
        return ["No wheel files matched the provided paths"]
    for wheel in wheels:
        try:
            actual_version = wheel_version(wheel)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if actual_version != expected_version:
            errors.append(f"{wheel.name}: version {actual_version} does not match release {expected_version}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Release tag, for example v0.0.16")
    parser.add_argument("--main-ref", help="Git ref that must contain the release tag")
    parser.add_argument("--changelog", type=Path, help="CHANGELOG file that must contain the release version")
    parser.add_argument("--wheel", action="append", default=[], help="Wheel path or glob; may be repeated")
    args = parser.parse_args()

    try:
        version = version_from_tag(args.tag)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    repo_root = Path.cwd()

    if args.main_ref:
        try:
            if not tag_is_reachable_from(args.tag, args.main_ref, cwd=repo_root):
                errors.append(f"{args.tag} is not reachable from {args.main_ref}")
        except RuntimeError as exc:
            errors.append(str(exc))

    if args.changelog and not changelog_contains_version(args.changelog, version):
        errors.append(f"{args.changelog}: missing release heading for [{version}]")

    if args.wheel:
        errors.extend(validate_wheels(expand_wheels(args.wheel), version))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    checks = [f"tag={args.tag}", f"version={version}"]
    if args.main_ref:
        checks.append(f"main_ref={args.main_ref}")
    if args.changelog:
        checks.append(f"changelog={args.changelog}")
    if args.wheel:
        checks.append(f"wheels={len(expand_wheels(args.wheel))}")
    print("OK: " + ", ".join(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
