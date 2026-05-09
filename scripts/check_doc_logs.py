#!/usr/bin/env python3
"""CI-side gate: re-validate ``example-exec-logs/`` without re-running anything.

Intended to be invoked from CI as the cheap counterpart to
``scripts/build_docs.py``. Local maintainers run the full pipeline (which
re-executes runnable examples and refreshes the cached logs); CI just
checks the cached verdicts and refuses the build if anything is
``verdict == "fail"`` or if the index file is missing/stale.

Exit code 0 → all clear. Exit code 1 → at least one failure or missing log.
"""

from __future__ import annotations

import json
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
LOGS_ROOT = PROJECT_ROOT / "example-exec-logs"
INDEX_PATH = LOGS_ROOT / "index.json"


def main() -> int:
    if not INDEX_PATH.exists():
        print(
            f"check_doc_logs: missing {INDEX_PATH.relative_to(PROJECT_ROOT)}.\n"
            "Run `uv run python scripts/build_docs.py` locally and commit "
            "the updated example-exec-logs/ tree.",
            file=sys.stderr,
        )
        return 1

    payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    if not results:
        print("check_doc_logs: no results in example-exec-logs/index.json", file=sys.stderr)
        return 1

    failures = [r for r in results if r.get("verdict") == "fail"]
    n_pass = sum(1 for r in results if r.get("verdict") == "pass")
    n_skip = sum(1 for r in results if r.get("verdict") == "skip")
    n_listed = sum(1 for r in results if r.get("verdict") == "not-executed")
    n_fail = len(failures)

    print(
        f"check_doc_logs: pass={n_pass} skip={n_skip} listed={n_listed} fail={n_fail} "
        f"(real_cloud={payload.get('real_cloud')}, generated_at={payload.get('generated_at')})"
    )
    if failures:
        print("\nFailures:", file=sys.stderr)
        for rec in failures:
            print(
                f"  - {rec['example']}: "
                f"{rec.get('skip_reason') or 'unfiltered warning/error or exception'}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
