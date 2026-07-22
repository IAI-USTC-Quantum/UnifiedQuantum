"""Emit GitHub Actions annotations for failures in a JUnit XML report."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    root = ET.parse(args.report).getroot()
    failures = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        detail = failure if failure is not None else error
        if detail is None:
            continue
        failures.append((case, detail))

    for case, detail in failures:
        name = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
        message = detail.get("message") or (detail.text or "pytest failure")
        metadata = [f"title={_escape(name)}"]
        if case.get("file"):
            metadata.append(f"file={_escape(case.get('file', ''))}")
        if case.get("line"):
            metadata.append(f"line={case.get('line')}")
        print(f"::error {','.join(metadata)}::{_escape(message[-4000:])}")

    if not failures:
        print("No pytest failures found in the JUnit report.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
