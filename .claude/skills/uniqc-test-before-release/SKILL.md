---
name: uniqc-test-before-release
description: "Use before every UnifiedQuantum release to create and execute a complete release-candidate test plan, including CLI, Gateway frontend, cloud/dummy/real-device workflows, best-practices notebooks, and programmatic documentation-to-software alignment. Produces a full test report and a release/no-release recommendation."
---

# UnifiedQuantum Pre-Release Test Skill

Use this skill when a maintainer asks for release-candidate validation. This is not a smoke test. The output must be a complete execution plan first, then a complete report with a clear release recommendation.

## Required Output

Produce two artifacts:

1. **Test execution plan**: exact commands, credentials/quotas needed, expected artifacts, and pass/fail criteria.
2. **Final release report**: what was tested, evidence, failures, doc/software mismatches, coverage gaps, and one of `RELEASE`, `RELEASE WITH KNOWN GAPS`, or `DO NOT RELEASE`.

Use [references/report-template.md](references/report-template.md) for the report shape. Use [references/coverage-matrix.md](references/coverage-matrix.md) to avoid missing functional areas.

## First Steps

1. Confirm the release candidate:
   - Current branch, commit, tag candidate, and version from `uniqc/_version.py` or package metadata.
   - `README.md`, `README_en.md`, `CHANGELOG.md`, `pyproject.toml`, and `docs/source/releases/`.
2. Check the worktree:
   - `git status -sb`
   - Do not mix unrelated local changes into the release report. Report them as environment risk if they affect execution.
3. Build the test environment:
   - `uv sync --extra all --group dev --group docs --upgrade`
   - `cd frontend && npm ci`
   - Install Quafu only when the release scope explicitly includes deprecated Quafu behavior: `uv sync --extra quafu --group dev`. Do not use `--all-extras` as the default release path because deprecated Quafu/`pyquafu` may fail dependency resolution on current Python versions.
4. Identify real-platform readiness:
   - Config file: `~/.uniqc/config.yaml`
   - Required token sections: `originq`, `ibm`, `quark`, and deprecated `quafu` only if in scope.
   - Confirm quota/cost permission before any command that submits a real quantum task.

## Mandatory Test Phases

### 1. Automated Python Package Tests

Run and record:

```bash
uv run pytest uniqc/test -v
uv run pytest uniqc/test -v --real-cloud-test
```

Rules:

- Ordinary cloud discovery/status/token tests must run in the default test command.
- Only tests that submit real quantum circuits belong behind `--real-cloud-test`.
- Dependency failures for maintained extras such as Qiskit, Qutip, Torch, docs, or visualization are release blockers unless the maintainer explicitly scopes them out.
- Quafu is deprecated; failures there are not blockers unless Quafu is in the release scope.

### 2. Best-Practices Documentation Execution

The best-practices section is a release gate.

Run:

```bash
uv run python scripts/generate_best_practice_notebooks.py
cd docs
uv run make html
```

Then inspect:

- `docs/source/guide/best_practices.md`
- `docs/source/best_practices/index.md`
- every notebook under `docs/source/best_practices/*.ipynb`
- generated HTML pages for broken rendering, stale outputs, or inconsistent command names.

Best-practices failures are blockers unless the affected feature is explicitly removed from the release.

### 3. CLI Help and CLI Behavior

Use CLI help as a progressive-disclosure source of truth. Capture help for the root command and every public subcommand:

```bash
uv run uniqc --help
uv run python -m uniqc.cli --help
uv run uniqc circuit --help
uv run uniqc simulate --help
uv run uniqc submit --help
uv run uniqc result --help
uv run uniqc config --help
uv run uniqc task --help
uv run uniqc backend --help
uv run uniqc backend list --help
uv run uniqc backend show --help
uv run uniqc backend update --help
uv run uniqc backend chip-display --help
uv run uniqc calibrate --help
uv run uniqc gateway --help
```

Then execute representative CLI workflows:

- Build or write a Bell/GHZ OriginIR file. Prefer OriginIR in release-plan examples because it is the recommended normalized path:

```originir
QINIT 2
CREG 2
H q[0]
CNOT q[0], q[1]
MEASURE q[0], c[0]
MEASURE q[1], c[1]
```

- `uv run uniqc circuit <file> --info`
- `uv run uniqc simulate <file>`
- `uv run uniqc submit <file> --platform dummy --wait`
- `uv run uniqc submit <file> --platform dummy --backend virtual-line-3 --wait`
- `uv run uniqc submit <file> --platform dummy --backend originq:WK_C180 --dry-run`
- `uv run uniqc backend update --platform originq`
- `uv run uniqc backend list --platform originq`
- `uv run uniqc backend show originq:WK_C180`
- `uv run uniqc backend chip-display originq/WK_C180 --update`

Confirm the docs match the help output and actual behavior. Do not recommend `python -m uniqc`; the supported module fallback is `python -m uniqc.cli`. There is no `uniqc workflow` CLI subcommand; `docs/source/cli/workflow.md` is a workflow guide page, and interactive next-step guidance is exposed by `--ai-hints` / `--ai-hint`.

Also verify the AI-hint paths:

- `uv run uniqc config list --ai-hint` or an equivalent command-local hint check.
- `uv run uniqc config always-ai-hint on`
- A subsequent command without `--ai-hint` prints AI workflow hints.
- `uv run uniqc config always-ai-hint off`
- Error-path documentation recommends adding `--ai-hint` or enabling `always-ai-hint` when an agent is uncertain about the next command.

### 4. Gateway Frontend and API

Run frontend checks:

```bash
cd frontend
npm run build
```

Run gateway checks:

```bash
uv run uniqc gateway status
uv run uniqc gateway start --host 127.0.0.1 --port 18765
```

Then verify:

- `/api/health`
- `/api/version`
- `/api/backends`
- `/api/tasks`
- the React app renders built assets from `frontend/dist`.
- Backend cards do not list `dummy:<platform>:<backend>` as an enumerable backend.
- Task pages can show dummy tasks, dry-run metadata where applicable, and compiled/transpiled metadata for chip-backed dummy paths.

Use Playwright or an available browser automation tool if present. If no browser tool is available, use HTTP responses and built asset inspection, and mark visual coverage as a gap.

### 5. Real-Platform Validation

Separate real-platform tests into three buckets:

- **Discovery**: backend list, status, token validation, and cache update. This should run by default in a core-dev environment.
- **Dry-run**: compatibility checks without creating quantum tasks.
- **Execution**: small-shot real quantum tasks. Requires explicit maintainer permission, quota notes, task IDs, and result retrieval.

Minimum release-candidate evidence:

- At least one OriginQ discovery/cache/dry-run path.
- At least one IBM/Qiskit discovery or documented reason it is unavailable.
- At least one real quantum task if the maintainer has authorized quota use.
- For every unavailable platform, record the exact missing token, SDK, region, or network reason.

### 6. Programmatic Documentation Alignment

Compare docs to software, not just by reading prose.

Check at least:

- `pyproject.toml` `project.scripts` contains `uniqc = "uniqc.cli.main:app"` and docs use `uniqc` / `python -m uniqc.cli`.
- CLI docs under `docs/source/cli/` describe commands that exist in `uv run uniqc --help`.
- Best-practices code imports current top-level APIs from `uniqc` where expected.
- New docs do not encourage old entries for new code: `uniqc.transpiler`, `uniqc.task`, `uniqc.qasm`, `uniqc.originir`, `uniqc.pytorch`, `uniqc.analyzer`.
- Dummy backend semantics are consistent:
  - `dummy`: unconstrained, noiseless local VM.
  - `dummy:virtual-line-N` / `dummy:virtual-grid-RxC`: virtual topology, noiseless.
  - `dummy:<platform>:<backend>`: rule-based chip-backed local noisy execution, not listed as an enumerable backend.
- Config path is `~/.uniqc/config.yaml`.
- AI workflow hints use `--ai-hints` / `--ai-hint`, environment variable `UNIQC_AI_HINTS=1`, or `uniqc config always-ai-hint on`.
- IBM proxy can be configured with nested config keys such as `uniqc config set ibm.proxy.https http://127.0.0.1:7890`.
- Quafu is documented as deprecated and not part of `[all]`.

When possible, write small one-off scripts for this comparison and include their output in the report. If a comparison is manual, label it manual.

## Release Recommendation Rules

Use `DO NOT RELEASE` when any of these are true:

- Best-practices notebooks or docs build fail for maintained paths.
- CLI public help and docs disagree on a command required by the recommended workflow.
- Gateway frontend cannot build or the Gateway API cannot start in the release environment.
- Default tests fail for maintained dependencies.
- Real-platform discovery or dry-run fails without a documented external cause.
- Documentation claims a workflow works, but execution proves it does not.

Use `RELEASE WITH KNOWN GAPS` only when the gaps are external, explicitly documented, and not on the recommended path.

Use `RELEASE` only when the mandatory phases pass and any untested area is non-release-critical with maintainer approval.
