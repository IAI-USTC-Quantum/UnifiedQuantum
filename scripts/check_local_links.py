#!/usr/bin/env python3
"""Fail when active local Markdown or Sphinx references point nowhere.

The checker is deliberately offline: it validates repository-local files,
Sphinx documents, labels, toctrees, includes, and Markdown links without
requesting external URLs.  Sphinx remains responsible for semantic API and
intersphinx references during the ``-W`` documentation build.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections.abc import Iterable

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"
DOCS_SOURCE = DOCS_ROOT / "source"
MARKDOWN_SUFFIXES = {".md", ".rst"}
EXCLUDED_PARTS = {".git", ".venv", "_build", "_generated", "example-exec-logs", "node_modules"}
EXTERNAL_PREFIXES = ("#", "http://", "https://", "mailto:", "tel:", "data:")
BUILTIN_REFS = {"genindex", "modindex", "search"}

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*]\((?P<target>[^)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+]:\s*(?P<target>\S+)", re.MULTILINE)
MYST_DOC = re.compile(r"\{doc\}`(?P<target>[^`]+)`")
RST_DOC = re.compile(r":doc:`(?P<target>[^`]+)`")
MYST_REF = re.compile(r"\{ref\}`(?P<target>[^`]+)`")
RST_REF = re.compile(r":ref:`(?P<target>[^`]+)`")
MYST_INCLUDE = re.compile(r"^\s*```\{(?P<kind>include|literalinclude)\}\s*(?P<target>\S+)", re.MULTILINE)
RST_INCLUDE = re.compile(r"^\s*\.\.\s+(?P<kind>include|literalinclude)::\s*(?P<target>\S+)", re.MULTILINE)
RST_LABEL = re.compile(r"^\s*\.\.\s+_(?P<label>[^:]+):\s*$", re.MULTILINE)
MYST_LABEL = re.compile(r"^\s*\((?P<label>[^)]+)\)=\s*$", re.MULTILINE)


def _active_files(roots: Iterable[pathlib.Path]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for root in roots:
        if root.is_file() and root.suffix in MARKDOWN_SUFFIXES:
            files.append(root)
        elif root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.suffix in MARKDOWN_SUFFIXES and not any(part in EXCLUDED_PARTS for part in path.parts)
            )
    return sorted(set(files))


def _strip_title(target: str) -> str:
    return target.strip().split(maxsplit=1)[0].strip("<>").split("#", maxsplit=1)[0]


def _is_external(target: str) -> bool:
    return not target or target.startswith(EXTERNAL_PREFIXES) or "://" in target


def _resolve_path(source: pathlib.Path, target: str, sphinx_doc: bool = False) -> pathlib.Path | None:
    target = _strip_title(target)
    if _is_external(target):
        return None
    candidates = [source.parent / target]
    if sphinx_doc and pathlib.Path(target).suffix not in MARKDOWN_SUFFIXES:
        candidates.extend((source.parent / f"{target}.md", source.parent / f"{target}.rst"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _collect_labels(files: Iterable[pathlib.Path]) -> set[str]:
    labels = set(BUILTIN_REFS)
    for path in files:
        text = path.read_text(encoding="utf-8")
        labels.update(match.group("label") for match in RST_LABEL.finditer(text))
        labels.update(match.group("label") for match in MYST_LABEL.finditer(text))
    return labels


def _toctree_targets(path: pathlib.Path, text: str) -> Iterable[str]:
    in_tree = False
    for line in text.splitlines():
        if line.lstrip().startswith(".. toctree::") or line.lstrip().startswith("```{toctree}"):
            in_tree = True
            continue
        if not in_tree:
            continue
        if line.startswith("```") or (line and not line[0].isspace()):
            in_tree = False
            continue
        target = line.strip()
        if target and not target.startswith(":"):
            yield target


def check(roots: Iterable[pathlib.Path]) -> list[str]:
    files = _active_files(roots)
    labels = _collect_labels(files)
    errors: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        references: list[tuple[str, str, bool]] = []
        references.extend(("Markdown link", m.group("target"), False) for m in MARKDOWN_LINK.finditer(text))
        references.extend(("Markdown reference", m.group("target"), False) for m in REFERENCE_LINK.finditer(text))
        references.extend(("Sphinx document", m.group("target"), True) for m in MYST_DOC.finditer(text))
        references.extend(("Sphinx document", m.group("target"), True) for m in RST_DOC.finditer(text))
        references.extend(("Sphinx include", m.group("target"), False) for m in MYST_INCLUDE.finditer(text))
        references.extend(("Sphinx include", m.group("target"), False) for m in RST_INCLUDE.finditer(text))
        references.extend(("Sphinx toctree", target, True) for target in _toctree_targets(path, text))

        for kind, target, sphinx_doc in references:
            if _is_external(target):
                continue
            if kind.startswith("Markdown") and _strip_title(target) in labels:
                continue
            resolved = _resolve_path(path, target, sphinx_doc=sphinx_doc)
            if resolved is not None and not resolved.exists():
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: {kind} target does not exist: {target}")

        for match in (*MYST_REF.finditer(text), *RST_REF.finditer(text)):
            target = _strip_title(match.group("target"))
            if target and target not in labels:
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: Sphinx reference label does not exist: {target}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=pathlib.Path,
        default=[PROJECT_ROOT / "README.md", PROJECT_ROOT / "CHANGELOG.md", PROJECT_ROOT / "CONTRIBUTING.md", DOCS_ROOT, PROJECT_ROOT / "examples", PROJECT_ROOT / "uniqc" / "test"],
        help="Files or directories to scan (defaults to active repository docs).",
    )
    args = parser.parse_args()
    errors = check(args.paths)
    if errors:
        print("check_local_links: broken local links found:", file=sys.stderr)
        print(*[f"  - {error}" for error in errors], sep="\n", file=sys.stderr)
        return 1
    print(f"check_local_links: checked {len(_active_files(args.paths))} Markdown/reST files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
