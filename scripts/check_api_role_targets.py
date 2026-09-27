"""Check that MyST py-role links in the docs resolve to real API entries.

Sphinx does not warn about unresolvable ``{py:class}`...`` style references
outside nitpicky mode, so a role whose target is not a registered object
renders silently as plain code instead of a hyperlink. This script closes
that gap: after a docs build it compares every ``{py:*}`` role target in
``docs/source/**/*.md`` against the objects registered in
``docs/_build/html/objects.inv`` and reports dead targets together with a
canonical-name suggestion (a registered object sharing the trailing path
segments).

Usage (from the repo root, after ``make -C docs html-fast`` or any build):

    python scripts/check_api_role_targets.py

Exits non-zero when at least one role target is dead.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# `python -m sphinx.ext.intersphinx <path>` prints the inventory as
# "domain:type" headers followed by indented "name : url" entries.
inv_path = DOCS / "_build" / "html" / "objects.inv"
if not inv_path.exists():
    sys.exit(f"no inventory at {inv_path} — build the docs first (make -C docs html-fast)")
proc = subprocess.run(
    [sys.executable, "-m", "sphinx.ext.intersphinx", str(inv_path)],
    capture_output=True, text=True, check=True,
)
by_name: dict[str, set[str]] = {}
current_type = None
for line in proc.stdout.splitlines():
    if not line.strip():
        continue
    if not line[0].isspace():
        current_type = line.strip()  # e.g. "py:attribute"
    elif current_type:
        entry = line.split(":", 1)[0].strip()
        if entry:
            by_name.setdefault(entry, set()).add(current_type)
all_names = set(by_name)

ROLE_RE = re.compile(r"\{(?:py:)?(class|func|meth|mod|attr|exc|data|obj)\}`([^`<]+?)(?:\s*<([^`>]+)>)?`")
# role target with optional custom title: {py:class}`title <target>`

files = [
    p for p in (DOCS / "source").rglob("*.md")
    if "_generated" not in p.parts and "7_releases" not in p.parts
]

found: dict[str, list[str]] = {}  # "role:target" -> [files]
for p in sorted(files):
    text = p.read_text(encoding="utf-8")
    rel = str(p.relative_to(DOCS)).replace("\\", "/")
    for m in ROLE_RE.finditer(text):
        role, body, explicit = m.group(1), m.group(2).strip(), m.group(3)
        target = (explicit or body).strip()
        key = f"{role}:{target}"
        found.setdefault(key, []).append(rel)

print(f"inventory objects: {len(all_names)}; role occurrences: {sum(len(v) for v in found.values())} across {len(found)} unique targets\n")

dead, live = [], []
for key in sorted(found):
    role, target = key.split(":", 1)
    # Role/object-type mismatches still hyperlink (the py domain resolves by
    # name), so membership in the inventory is the pass/fail criterion.
    (live if target in all_names else dead).append(key)

print(f"=== RESOLVING ({len(live)}) ===")
for k in live:
    print("  OK", k)

print(f"\n=== NOT RESOLVING ({len(dead)}) — with canonical suggestions ===")
for key in dead:
    role, target = key.split(":", 1)
    parts = target.split(".")
    cands = []
    for take in range(len(parts), 0, -1):
        suffix = ".".join(parts[-take:])
        matches = sorted(n for n in all_names if n.endswith("." + suffix) or n == suffix)
        # exact-suffix matches with at least the same length
        matches = [m for m in matches if len(m.split(".")) >= len(parts)]
        if matches:
            cands = matches
            break
    print(f"  DEAD {key}")
    for f in sorted(set(found[key])):
        print(f"       in {f}")
    for c in cands[:4]:
        print(f"       -> {c}  [{','.join(sorted(by_name[c]))}]")
    if not cands:
        print("       -> NO CANDIDATE")

if dead:
    sys.exit(1)
print(f"\nall {len(live)} role targets resolve")

