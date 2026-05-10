---
name: uniqc-build-docs
description: "Run the full UnifiedQuantum documentation build: execute all examples (pre-doc-execution), regenerate API reference via sphinx-apidoc, and build Sphinx HTML. Reports any warnings, errors, or diffs in example-exec-logs/."
---

# UnifiedQuantum Documentation Build Skill

Use this skill when a developer wants to build the documentation locally. The build has two stages:

1. **Pre-doc-execution** (`scripts/build_docs.py`): runs every `examples/<chapter>/*.py`, captures stdout/stderr and matplotlib figures, generates `docs/source/_generated/examples/` Markdown pages, and refreshes `example-exec-logs/`.
2. **Sphinx HTML** (`sphinx-build`): builds the final site, `{include}`-ing the generated example pages.

`make html` runs both. `make html-fast` skips step 1 and trusts committed logs.

## Steps

### Step 1: Ensure the environment is up to date

```bash
cd /home/agony/projects/uniqc-skill-dev/UnifiedQuantum
uv sync --all-extras --group dev --group docs
```

If `uv sync` fails because of a missing optional extra (e.g. deprecated `pyquafu`), retry without `--all-extras`:

```bash
uv sync --group dev --group docs
```

### Step 2: Run the full doc build

From the project root:

```bash
cd docs && uv run make html 2>&1
```

This runs (in order):
1. `examples` target — executes `scripts/build_docs.py` and refreshes `example-exec-logs/`
2. `apidoc` target — runs `sphinx-apidoc` to regenerate API rst stubs under `source/6_api/`
3. `html` target — runs `sphinx-build -M html`

Capture the full output and look for:
- **`WARNING`** or **`ERROR`** lines from Sphinx
- **Traceback** or **Exception** lines from example execution
- **Non-zero exit code** from `make html`

### Step 3: Check for example-exec-logs diffs

After a successful build, check whether the committed example outputs changed:

```bash
cd /home/agony/projects/uniqc-skill-dev/UnifiedQuantum
git diff --stat -- example-exec-logs/
```

- **No diff**: examples produced identical output to what is committed. No action needed.
- **Diff present**: an example's behaviour changed. Review the diff to confirm it is intentional (due to your code changes), then stage and commit the updated logs:
  ```bash
  git add example-exec-logs/
  ```

### Step 4: Check for generated-page diffs

```bash
git diff --stat -- docs/source/_generated/
```

Commit any intentional diffs:

```bash
git add docs/source/_generated/
```

### Step 5: Report results

Report to the user:
1. Whether the build succeeded (exit code 0) or failed.
2. Number and category of warnings (if any).
3. Whether `example-exec-logs/` has uncommitted diffs (and whether they were committed).
4. Path to the built HTML: `docs/_build/html/index.html`.

## Fast rebuild (skip example re-execution)

If examples have not changed and only prose or API docs were edited, use the fast path:

```bash
cd docs && uv run make html-fast 2>&1
```

This skips `scripts/build_docs.py` and uses the already-committed `example-exec-logs/`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` during example execution | Missing optional dependency | `uv sync --all-extras --group docs` or install the specific package |
| `WARNING: unknown directive` in Sphinx output | Missing or renamed rst/md include path | Check `docs/source/<chapter>/index.md` for stale `{include}` paths |
| `example-exec-logs/` diff on CI but not locally | Stale committed logs | Run `make html` locally, commit updated `example-exec-logs/` |
| `sphinx-apidoc` produces unexpected entries | New module not excluded | Update `APIDOC_EXCLUDE` in `docs/Makefile` |
