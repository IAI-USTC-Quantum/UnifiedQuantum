#!/usr/bin/env python3
"""Validate that bundled uniqc_cpp extensions match wheel Python tags."""

from __future__ import annotations

import argparse
import glob
import re
import sys
import zipfile
from pathlib import Path

EXTENSION_TAG_RE = re.compile(
    r"^uniqc_cpp\.(?:cpython-|cp)(?P<version>\d{2,3})[A-Za-z0-9_./-]*\.(?:so|pyd)$"
)
WHEEL_TAG_RE = re.compile(r"^cp(?P<version>\d{2,3})(?:m|t|d|u)?$")


def expand_wheel_paths(patterns: list[str]) -> list[Path]:
    wheel_paths: list[Path] = []
    seen: set[Path] = set()

    for pattern in patterns:
        matches = [Path(match) for match in glob.glob(pattern)]
        if not matches:
            path = Path(pattern)
            if path.exists():
                matches = [path]

        for match in matches:
            resolved = match.resolve()
            if resolved.suffix == ".whl" and resolved not in seen:
                seen.add(resolved)
                wheel_paths.append(resolved)

    return sorted(wheel_paths)


def expected_python_versions(wheel_path: Path) -> set[str]:
    stem = wheel_path.name[:-4] if wheel_path.name.endswith(".whl") else wheel_path.name
    try:
        _, python_tag, _, _ = stem.rsplit("-", 3)
    except ValueError as exc:
        raise ValueError(f"Wheel filename does not match expected format: {wheel_path.name}") from exc

    versions: set[str] = set()
    for tag in python_tag.split("."):
        match = WHEEL_TAG_RE.fullmatch(tag)
        if match:
            versions.add(match.group("version"))

    if not versions:
        raise ValueError(f"Could not determine CPython tag from wheel filename: {wheel_path.name}")

    return versions


def bundled_extension_versions(wheel_path: Path) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    with zipfile.ZipFile(wheel_path) as wheel_zip:
        for member in wheel_zip.namelist():
            basename = Path(member).name
            match = EXTENSION_TAG_RE.fullmatch(basename)
            if match:
                matches.append((member, match.group("version")))

    return matches


def validate_wheel(wheel_path: Path) -> list[str]:
    expected_versions = expected_python_versions(wheel_path)
    bundled_versions = bundled_extension_versions(wheel_path)
    errors: list[str] = []

    if not bundled_versions:
        errors.append(f"{wheel_path.name}: no bundled uniqc_cpp extension found")
        return errors

    for member, bundled_version in bundled_versions:
        if bundled_version not in expected_versions:
            expected = ", ".join(f"cp{version}" for version in sorted(expected_versions))
            errors.append(
                f"{wheel_path.name}: bundled extension {member} targets cp{bundled_version}, expected {expected}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", nargs="+", help="Wheel files or glob patterns to validate")
    args = parser.parse_args()

    wheel_paths = expand_wheel_paths(args.wheels)
    if not wheel_paths:
        print("No wheel files matched the provided paths.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for wheel_path in wheel_paths:
        errors = validate_wheel(wheel_path)
        if errors:
            all_errors.extend(errors)
        else:
            print(f"OK: {wheel_path.name}")

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
