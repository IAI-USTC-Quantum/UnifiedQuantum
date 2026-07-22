#!/usr/bin/env python3
"""Pre-doc-execution: run all runnable examples and splice outputs into the docs.

This is **step 1** of the two-step documentation build:

* **Step 1 (this script)** — discover ``examples/<chapter>/*.py``, parse each
  example's docstring for runtime gating directives, run the runnable subset,
  capture stdout / stderr / matplotlib figures, write the per-example logs to
  ``example-exec-logs/<chapter>/<name>/`` *and* a Sphinx-includable Markdown
  page to ``docs/source/_generated/examples/<chapter>/<name>.md``. Fail the
  build (non-zero exit) if any executed example produced an unfiltered
  warning, error, or traceback.
* **Step 2 (sphinx)** — ``make html`` consumes the generated Markdown pages.

The chapter prose pages under ``docs/source/<chapter>/`` use
``{include} <relative path to generated md>`` to splice the example
walkthroughs into place.

Docstring directives (parsed from the example's *module* docstring):

* ``[doc-require: key1, key2, ...]`` — only run when all listed keys are
  satisfied. See ``REQUIREMENT_REGISTRY`` below for the supported keys.
  Missing keys cause the example to be **skipped**, not failed.
* ``[doc-warning-ignore: <python-regex>]`` — pattern to subtract from the
  warning/error scan. Repeat the directive for additional patterns.
* ``[doc-output-include: stdout, stderr, figures, source]`` — which sections
  to splice into the rendered Markdown page. Defaults to all four.
* ``[doc-title: ...]`` — override the section title (defaults to the first
  non-blank line of the docstring with leading ``#`` stripped).
* ``[doc-skip-execute]`` — list the example in the docs without running it
  (e.g., snippets that only make sense on a real chip).

CLI:

    uv run python scripts/build_docs.py            # default; --real-cloud off
    uv run python scripts/build_docs.py --real-cloud
    uv run python scripts/build_docs.py --only 3_best_practices
    uv run python scripts/build_docs.py --no-fail-on-warnings   # dev only

The companion ``scripts/check_doc_logs.py`` is what CI runs: it never
executes an example, it just re-reads ``example-exec-logs/index.json`` and
fails if any verdict is ``fail``.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import runpy
import sys
import time
import traceback
import warnings
from dataclasses import dataclass, field
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = PROJECT_ROOT / "examples"
LOGS_ROOT = PROJECT_ROOT / "example-exec-logs"
DOCS_GENERATED_ROOT = PROJECT_ROOT / "docs" / "source" / "_generated" / "examples"
LOG_INDEX_FORMAT_VERSION = 2
GENERATOR_VERSION = "2"

# Patterns considered a build-failure when found in stdout/stderr/warnings.
# Per-example regexes (from [doc-warning-ignore:]) are subtracted before this
# check runs.
WARNING_ERROR_PATTERNS = (
    re.compile(r"\bWarning\b", re.IGNORECASE),
    re.compile(r"\bWARNING\b"),
    re.compile(r"\bERROR\b"),
    re.compile(r"\bTraceback \(most recent call last\)"),
)


# ---------------------------------------------------------------------------
# Requirement registry
# ---------------------------------------------------------------------------


def _have_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _have_credentials(provider: str) -> bool:
    try:
        from uniqc.backend_adapter.preflight import has_provider_credentials
    except Exception:
        return False
    try:
        return bool(has_provider_credentials(provider))
    except Exception:
        return False


def _real_cloud_enabled() -> bool:
    # Patched at runtime by main() based on the --real-cloud CLI flag.
    return bool(_RUNTIME_OPTIONS.get("real_cloud", False))


_RUNTIME_OPTIONS: dict[str, Any] = {"real_cloud": False}


# Each entry is (label_for_human, callable returning bool).
REQUIREMENT_REGISTRY: dict[str, tuple[str, Any]] = {
    # SDK-only (no credentials):
    "originq-sdk": ("pyqpanda3 installed", lambda: _have_module("pyqpanda3")),
    "quafu-sdk": ("pyquafu installed", lambda: _have_module("quafu")),
    "ibm-sdk": ("qiskit_ibm_runtime installed", lambda: _have_module("qiskit_ibm_runtime")),
    "quark-sdk": (
        "quarkstudio installed",
        lambda: _have_module("quarkstudio") and _have_module("quarkcircuit"),
    ),
    "qiskit": ("qiskit installed", lambda: _have_module("qiskit")),
    "pytorch": ("torch installed", lambda: _have_module("torch")),
    "torchquantum": (
        "torch + torchquantum installed",
        lambda: _have_module("torch") and _have_module("torchquantum"),
    ),
    "qutip": ("qutip installed", lambda: _have_module("qutip")),
    "matplotlib": ("matplotlib installed", lambda: _have_module("matplotlib")),
    "pandas": ("pandas installed", lambda: _have_module("pandas")),
    "sklearn": ("scikit-learn installed", lambda: _have_module("sklearn")),
    "cpp": ("uniqc_cpp C++ extension installed", lambda: _have_module("uniqc_cpp")),
    # SDK + credentials (provider end-to-end):
    "originq": (
        "pyqpanda3 + originq token configured",
        lambda: _have_module("pyqpanda3") and _have_credentials("originq"),
    ),
    "quafu": (
        "pyquafu + quafu token configured",
        lambda: _have_module("quafu") and _have_credentials("quafu"),
    ),
    "ibm": (
        "qiskit_ibm_runtime + ibm token configured",
        lambda: _have_module("qiskit_ibm_runtime") and _have_credentials("ibm"),
    ),
    "quark": (
        "quarkstudio + quark token configured",
        lambda: _have_module("quarkstudio") and _have_credentials("quark"),
    ),
    # Gated by --real-cloud CLI flag (in addition to the provider req):
    "real-cloud": ("--real-cloud flag passed", _real_cloud_enabled),
}


# ---------------------------------------------------------------------------
# Directive parsing
# ---------------------------------------------------------------------------


@dataclass
class ExampleSpec:
    path: pathlib.Path
    chapter: str
    name: str
    docstring: str
    title: str
    require: list[str] = field(default_factory=list)
    warning_ignore: list[re.Pattern[str]] = field(default_factory=list)
    output_include: set[str] = field(default_factory=lambda: {"stdout", "stderr", "figures", "source"})
    skip_execute: bool = False


_DIRECTIVE_RE = re.compile(r"\[doc-([a-z-]+):?\s*(.*?)\]", re.IGNORECASE)


def _parse_module_docstring(path: pathlib.Path) -> str:
    """Return the literal module docstring (no compile required)."""
    src = path.read_text(encoding="utf-8")
    # Strip an optional leading shebang and encoding line.
    lines = src.splitlines()
    i = 0
    while i < len(lines) and lines[i].startswith("#"):
        i += 1
    rest = "\n".join(lines[i:]).lstrip()
    for opener, closer in (('"""', '"""'), ("'''", "'''"), ('r"""', '"""'), ("r'''", "'''")):
        if rest.startswith(opener):
            after = rest[len(opener):]
            end = after.find(closer)
            if end >= 0:
                return after[:end]
            break
    return ""


def _make_spec(path: pathlib.Path) -> ExampleSpec:
    # ``chapter`` is always the top-level numbered chapter dir under
    # ``examples/`` (e.g. ``2_advanced``).
    rel = path.relative_to(EXAMPLES_ROOT)
    chapter = rel.parts[0]
    # ``name`` is the rest of the relative path with the .py extension
    # stripped and ``/`` flattened into ``__`` so it is filesystem-safe
    # for use as a directory name under ``example-exec-logs/<chapter>/``
    # and ``docs/source/_generated/examples/<chapter>/``.
    sub_parts = list(rel.parts[1:])
    sub_parts[-1] = path.stem
    name = "__".join(sub_parts)
    docstring = _parse_module_docstring(path)

    require: list[str] = []
    warning_ignore: list[re.Pattern[str]] = []
    output_include: set[str] = {"stdout", "stderr", "figures", "source"}
    title_override: str | None = None
    skip_execute = False

    for match in _DIRECTIVE_RE.finditer(docstring):
        key = match.group(1).lower()
        value = match.group(2).strip()
        if key == "require":
            require.extend([p.strip() for p in value.split(",") if p.strip()])
        elif key == "warning-ignore":
            try:
                warning_ignore.append(re.compile(value))
            except re.error as exc:
                raise SystemExit(
                    f"{path}: invalid [doc-warning-ignore: {value!r}] regex: {exc}"
                ) from None
        elif key == "output-include":
            output_include = {p.strip() for p in value.split(",") if p.strip()}
        elif key == "title":
            title_override = value
        elif key == "skip-execute":
            skip_execute = True

    if title_override:
        title = title_override
    else:
        title = name
        for line in docstring.splitlines():
            line = line.strip()
            if line:
                title = re.sub(r"^[#*\s]+", "", line)
                # Strip the bare summary marker like "01_xxx —"
                title = re.sub(r"^\d{2}_\S+\s*[—-]\s*", "", title)
                break

    return ExampleSpec(
        path=path,
        chapter=chapter,
        name=name,
        docstring=docstring,
        title=title,
        require=require,
        warning_ignore=warning_ignore,
        output_include=output_include,
        skip_execute=skip_execute,
    )


def _missing_requirements(spec: ExampleSpec) -> list[str]:
    missing: list[str] = []
    for key in spec.require:
        if key not in REQUIREMENT_REGISTRY:
            raise SystemExit(
                f"{spec.path}: unknown [doc-require: {key}]; "
                f"add it to REQUIREMENT_REGISTRY in scripts/build_docs.py"
            )
        label, predicate = REQUIREMENT_REGISTRY[key]
        if not predicate():
            missing.append(f"{key} ({label})")
    return missing


# ---------------------------------------------------------------------------
# Example execution
# ---------------------------------------------------------------------------


def _run_example(spec: ExampleSpec, log_dir: pathlib.Path) -> dict[str, Any]:
    """Run a single example in-process; capture stdout, stderr, warnings, figures."""
    log_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = log_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    # Wipe any leftover figures from a previous run.
    for old in figures_dir.glob("*.svg"):
        old.unlink()
    docs_figures_dir = DOCS_GENERATED_ROOT / spec.chapter / "figures" / spec.name
    if docs_figures_dir.exists():
        for old in docs_figures_dir.glob("*.svg"):
            old.unlink()
    docs_figures_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(LOGS_ROOT / ".matplotlib"))

    captured_warnings: list[str] = []

    def _record_warning(message, category, filename, lineno, file=None, line=None):  # noqa: ANN001,ARG001
        captured_warnings.append(
            f"{category.__name__}: {message} ({pathlib.Path(filename).name}:{lineno})"
        )

    stdout = io.StringIO()
    stderr = io.StringIO()

    saved_argv = sys.argv[:]
    saved_cwd = os.getcwd()
    saved_path = sys.path[:]

    sys.argv = [str(spec.path)]
    os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    started_at = time.time()
    exc: BaseException | None = None
    figure_files: list[str] = []

    try:
        with warnings.catch_warnings():
            warnings.resetwarnings()
            warnings.simplefilter("always")
            warnings.showwarning = _record_warning  # type: ignore[assignment]
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    runpy.run_path(str(spec.path), run_name="__main__")
                except SystemExit as e:
                    if e.code not in (None, 0):
                        exc = e
                except BaseException as e:  # noqa: BLE001
                    exc = e

        # Collect any matplotlib figures the example created.
        try:
            import matplotlib.pyplot as plt
            for idx, fig_num in enumerate(plt.get_fignums(), start=1):
                fig = plt.figure(fig_num)
                fname = f"figure-{idx:02d}.svg"
                fig.savefig(figures_dir / fname, format="svg", bbox_inches="tight")
                fig.savefig(docs_figures_dir / fname, format="svg", bbox_inches="tight")
                figure_files.append(fname)
            plt.close("all")
        except Exception:
            pass
    finally:
        sys.argv = saved_argv
        os.chdir(saved_cwd)
        sys.path[:] = saved_path

    duration = time.time() - started_at

    return {
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "warnings": captured_warnings,
        "figure_files": figure_files,
        "exception": (
            None
            if exc is None
            else {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "traceback": "".join(traceback.format_exception(exc)),
            }
        ),
        "duration_seconds": round(duration, 3),
    }


def _classify_warnings_errors(
    text: str, ignore_patterns: list[re.Pattern[str]]
) -> tuple[list[str], list[str]]:
    """Return (offending_lines, ignored_lines) where 'offending' is what fails the build."""
    offending: list[str] = []
    ignored: list[str] = []
    for line in text.splitlines():
        if not any(p.search(line) for p in WARNING_ERROR_PATTERNS):
            continue
        if any(p.search(line) for p in ignore_patterns):
            ignored.append(line)
        else:
            offending.append(line)
    return offending, ignored


# ---------------------------------------------------------------------------
# Markdown rendering for sphinx
# ---------------------------------------------------------------------------


def _path_for_chapter_include(path: pathlib.Path) -> str:
    """Path string suitable for ``literalinclude`` from a chapter index page.

    The generated pages are designed to be ``{include}``'d from
    ``docs/source/<chapter>/index.md``. MyST resolves nested directive paths
    relative to the *including* file, not the included file, so we always use
    paths relative to ``docs/source/<chapter>/``.

    Examples are at ``examples/<chapter>/[<sub>/...]<name>.py`` where the
    sub-path may be one or more directories deep.
    """
    rel_to_examples = path.relative_to(EXAMPLES_ROOT)
    rel = pathlib.Path("..", "..", "..", "examples", *rel_to_examples.parts)
    return rel.as_posix()


def _figure_path_for_chapter_include(chapter: str, name: str, fname: str) -> str:
    """Return path to a copied figure, relative to ``docs/source/<chapter>/``.

    Figures are copied into ``docs/source/_generated/examples/<chapter>/figures/<name>/``
    so they live inside the sphinx source tree. From a chapter index page that
    resolves to ``../_generated/examples/<chapter>/figures/<name>/<fname>``.
    """
    rel = pathlib.Path("..", "_generated", "examples", chapter, "figures", name, fname)
    return rel.as_posix()


def _strip_title_from_prose(docstring: str, title: str) -> str:
    """Drop the first prose line if it matches the title (avoids duplicate H1)."""
    lines = docstring.splitlines()
    out: list[str] = []
    skipped_title = False
    for line in lines:
        if _DIRECTIVE_RE.search(line):
            continue
        stripped = re.sub(r"^[#*\s]+", "", line.strip())
        stripped = re.sub(r"^\d{2}_\S+\s*[—-]\s*", "", stripped)
        if not skipped_title and stripped:
            skipped_title = True
            if stripped == title:
                continue
        out.append(line)
    return "\n".join(out).strip()


def _render_markdown(spec: ExampleSpec, run: dict[str, Any], verdict: str, skip_reason: str | None) -> str:
    out: list[str] = []
    out.append(f"### {spec.title}")
    out.append("")
    out.append(f"*Source*: ``{spec.path.relative_to(PROJECT_ROOT).as_posix()}``  ")
    out.append(f"*Status*: **{verdict}**" + (f" — {skip_reason}" if skip_reason else ""))
    out.append("")

    if spec.docstring.strip():
        prose = _strip_title_from_prose(spec.docstring, spec.title)
        if prose:
            out.append(prose)
            out.append("")

    if "source" in spec.output_include:
        rel = _path_for_chapter_include(spec.path)
        out.append("**Source code**")
        out.append("")
        out.append("```{literalinclude} " + rel)
        out.append(":language: python")
        out.append("```")
        out.append("")

    if verdict == "skip":
        out.append(":::{note}")
        out.append(f"Example skipped during pre-doc-execution: {skip_reason}")
        out.append(":::")
        out.append("")
        return "\n".join(out) + "\n"

    if verdict == "not-executed":
        out.append(":::{note}")
        out.append("Listed for reference; not executed during the docs build "
                   "(``[doc-skip-execute]``).")
        out.append(":::")
        out.append("")
        return "\n".join(out) + "\n"

    if "stdout" in spec.output_include and run.get("stdout"):
        out.append("**Stdout**")
        out.append("")
        out.append("```text")
        out.append(run["stdout"].rstrip())
        out.append("```")
        out.append("")

    if "stderr" in spec.output_include and run.get("stderr"):
        out.append("**Stderr**")
        out.append("")
        out.append("```text")
        out.append(run["stderr"].rstrip())
        out.append("```")
        out.append("")

    if "figures" in spec.output_include and run.get("figure_files"):
        out.append("**Figures**")
        out.append("")
        for fname in run["figure_files"]:
            rel = _figure_path_for_chapter_include(spec.chapter, spec.name, fname)
            out.append(f"![{spec.title} — {fname}]({rel})")
            out.append("")

    if run.get("exception"):
        out.append("**Exception**")
        out.append("")
        out.append("```text")
        out.append(run["exception"]["traceback"].rstrip())
        out.append("```")
        out.append("")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def discover_examples(only_chapter: str | None) -> list[ExampleSpec]:
    if not EXAMPLES_ROOT.exists():
        return []
    specs: list[ExampleSpec] = []
    for chapter_dir in sorted(EXAMPLES_ROOT.iterdir()):
        if not chapter_dir.is_dir():
            continue
        if not re.match(r"^\d", chapter_dir.name):
            continue
        if only_chapter and chapter_dir.name != only_chapter:
            continue
        # Walk recursively so topical sub-dirs (e.g. ``2_advanced/algorithms/``,
        # ``2_advanced/circuits/``) are picked up. Skip files / dirs whose name
        # starts with ``_`` (private helpers).
        for path in sorted(chapter_dir.rglob("*.py")):
            if any(part.startswith("_") for part in path.relative_to(chapter_dir).parts):
                continue
            specs.append(_make_spec(path))
    return specs


def process(specs: list[ExampleSpec], fail_on_warnings: bool) -> int:
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    DOCS_GENERATED_ROOT.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    failures: list[str] = []

    for spec in specs:
        log_dir = LOGS_ROOT / spec.chapter / spec.name
        gen_dir = DOCS_GENERATED_ROOT / spec.chapter
        gen_dir.mkdir(parents=True, exist_ok=True)
        gen_md_path = gen_dir / f"{spec.name}.md"
        log_dir.mkdir(parents=True, exist_ok=True)

        verdict = "pass"
        skip_reason: str | None = None
        run: dict[str, Any] = {}

        missing = _missing_requirements(spec)
        if missing:
            verdict = "skip"
            skip_reason = "missing requirements: " + ", ".join(missing)
        elif spec.skip_execute:
            verdict = "not-executed"
        else:
            print(f"[run] {spec.path.relative_to(PROJECT_ROOT)}")
            run = _run_example(spec, log_dir)

            offending: list[str] = []
            ignored_total: list[str] = []
            for source_text in (run["stdout"], run["stderr"], "\n".join(run["warnings"])):
                bad, ignored = _classify_warnings_errors(source_text, spec.warning_ignore)
                offending.extend(bad)
                ignored_total.extend(ignored)
            run["offending_lines"] = offending
            run["ignored_lines"] = ignored_total

            if run["exception"] is not None:
                verdict = "fail"
                failures.append(f"{spec.path.relative_to(PROJECT_ROOT)}: raised {run['exception']['type']}")
            elif offending and fail_on_warnings:
                verdict = "fail"
                failures.append(
                    f"{spec.path.relative_to(PROJECT_ROOT)}: "
                    f"{len(offending)} unfiltered warning/error line(s); "
                    f"first: {offending[0]!r}"
                )

        record = {
            "example": spec.path.relative_to(PROJECT_ROOT).as_posix(),
            "source_sha256": hashlib.sha256(spec.path.read_bytes()).hexdigest(),
            "chapter": spec.chapter,
            "name": spec.name,
            "title": spec.title,
            "verdict": verdict,
            "skip_reason": skip_reason,
            "require": spec.require,
            "ignored_warning_patterns": [p.pattern for p in spec.warning_ignore],
            "stdout": run.get("stdout"),
            "stderr": run.get("stderr"),
            "warnings": run.get("warnings"),
            "figure_files": run.get("figure_files"),
            "offending_lines": run.get("offending_lines"),
            "ignored_lines": run.get("ignored_lines"),
            "exception": run.get("exception"),
            "duration_seconds": run.get("duration_seconds"),
        }
        (log_dir / "run.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        gen_md_path.write_text(_render_markdown(spec, run, verdict, skip_reason), encoding="utf-8")

        summary.append(
            {
                "example": record["example"],
                "chapter": record["chapter"],
                "name": record["name"],
                "title": record["title"],
                "verdict": verdict,
                "skip_reason": skip_reason,
                "duration_seconds": record["duration_seconds"],
                "n_offending": len(record["offending_lines"] or []),
                "n_ignored": len(record["ignored_lines"] or []),
                "source_sha256": record["source_sha256"],
            }
        )

    # When using --only, preserve results from chapters that were not
    # re-processed in this run so the index remains complete.
    index_path = LOGS_ROOT / "index.json"
    chapters_processed = {s.chapter for s in specs}
    existing_by_chapter: dict[str, list[dict[str, Any]]] = {}
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
            for rec in existing.get("results", []):
                existing_by_chapter.setdefault(rec["chapter"], []).append(rec)
        except (json.JSONDecodeError, KeyError):
            pass

    merged: list[dict[str, Any]] = list(summary)
    for chapter, recs in existing_by_chapter.items():
        if chapter not in chapters_processed:
            merged.extend(recs)

    index_path.write_text(
        json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "format_version": LOG_INDEX_FORMAT_VERSION,
                "generator": {
                    "name": "scripts/build_docs.py",
                    "version": GENERATOR_VERSION,
                },
                "real_cloud": _RUNTIME_OPTIONS["real_cloud"],
                "results": merged,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    n_pass = sum(1 for s in summary if s["verdict"] == "pass")
    n_skip = sum(1 for s in summary if s["verdict"] == "skip")
    n_skip_listed = sum(1 for s in summary if s["verdict"] == "not-executed")
    n_fail = sum(1 for s in summary if s["verdict"] == "fail")
    print(f"build_docs: pass={n_pass} skip={n_skip} listed={n_skip_listed} fail={n_fail}")
    if failures:
        print("Failures:")
        for line in failures:
            print(f"  - {line}")
        return 1
    return 0


def refresh_index_metadata() -> int:
    """Upgrade source hashes for a legacy index without re-executing examples."""
    index_path = LOGS_ROOT / "index.json"
    if not index_path.exists():
        print("build_docs: cannot refresh metadata; example-exec-logs/index.json is missing.", file=sys.stderr)
        return 1
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    if not results:
        print("build_docs: cannot refresh metadata; index has no results.", file=sys.stderr)
        return 1
    for record in results:
        example = record.get("example")
        source = PROJECT_ROOT / example if isinstance(example, str) else None
        if source is None or not source.is_file():
            print(f"build_docs: cannot hash missing example {example!r}.", file=sys.stderr)
            return 1
        record["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    payload["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload["format_version"] = LOG_INDEX_FORMAT_VERSION
    payload["generator"] = {"name": "scripts/build_docs.py", "version": GENERATOR_VERSION}
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"build_docs: refreshed source metadata for {len(results)} existing example logs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-cloud",
        action="store_true",
        help="Allow examples gated on [doc-require: real-cloud] to run.",
    )
    parser.add_argument(
        "--only",
        metavar="CHAPTER",
        help="Restrict to a single chapter directory (e.g. 3_best_practices).",
    )
    parser.add_argument(
        "--no-fail-on-warnings",
        action="store_true",
        help="Don't fail the build on unfiltered warnings (still fails on exceptions).",
    )
    parser.add_argument(
        "--refresh-index-metadata",
        action="store_true",
        help="Upgrade source hashes in an existing legacy index without executing examples.",
    )
    args = parser.parse_args()

    _RUNTIME_OPTIONS["real_cloud"] = args.real_cloud
    if args.refresh_index_metadata:
        return refresh_index_metadata()

    specs = discover_examples(args.only)
    if not specs:
        print("No examples discovered under examples/<chapter>/. Nothing to do.")
        return 0

    return process(specs, fail_on_warnings=not args.no_fail_on_warnings)


if __name__ == "__main__":
    raise SystemExit(main())
