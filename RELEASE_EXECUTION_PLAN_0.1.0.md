# Release Execution Plan — v0.1.0

> Generated 2026-08-23. Scope: release-candidate validation for the commit
> range `v0.0.17.post1..HEAD` (36 commits). This plan follows
> `.agents/skills/uniqc-test-before-release/`.

## Release Candidate

- Repository: `IAI-USTC-Quantum/UnifiedQuantum` (local: `/home/agony/projects/uniqc-dev/UnifiedQuantum`)
- Branch: `main` (10 commits ahead of `origin/main`)
- Commit: `a49d106` (`docs: refresh example-exec-logs and generated pages`)
- Version metadata: `0.0.17.post2.dev26` (`uniqc/_version.py`) → released as **`v0.1.0`** (renamed from the planned post2 tag)
- Environment: Linux x86_64, Python 3.12.3, Node 24.18.0 / npm 11.16.0, uv 0.12.1
- Worktree: clean at plan time; **no stale `RELEASE_REPORT_*` / `RELEASE_EXECUTION_PLAN_*` artifacts** in repo root
- Credentials (`~/.uniqc/config.yaml`, profile `default`, `config_version=1`): tokens present for **originq, ibm, quark, tianyan, logicalqubit**; quafu absent (out of scope)

## Credentials / Quotas Needed

| Bucket | Requirement | Status |
|---|---|---|
| Discovery (list/status/cache update) | tokens above | available |
| Dry-run | tokens + chip caches | available; caches refreshed during the run |
| Real execution | tokens + **explicit maintainer quota authorization** | **NOT authorized in this run** — real quantum tasks are only submitted after the maintainer approves quota use; otherwise recorded as BLOCKED |

## Phases, Commands, Artifacts, Pass/Fail Criteria

### Phase 1 — Automated Python package tests

```bash
uv run pytest uniqc/test -v        # default suite
uv run pytest uniqc/test -v --real-cloud-test   # includes real-submission tests
```

- Artifact: pytest output logs (`/tmp/prt_pytest_*.log`).
- PASS: zero failures in the default suite; `--real-cloud-test` run has no failures
  attributable to our code (tests gated on real submissions may skip without the flag's
  quota authorization — skips are recorded, not failures).
- FAIL (blocker): any failure in maintained-extra areas (qiskit, qutip, torch, docs, visualization).

### Phase 2 — C++ simulator dependency

```bash
uv run python -c "import uniqc_cpp; print(uniqc_cpp.StatevectorSimulator, uniqc_cpp.DensityOperatorSimulator)"
```

- PASS: imports and both classes print. FAIL = blocker.

### Phase 3 — Best-practices documentation execution (release gate)

```bash
uv run python scripts/build_docs.py --only 3_best_practices
cd docs && uv run sphinx-build -M html . _build   # `make html` equivalent (make unavailable on this host)
```

- Artifacts: `example-exec-logs/3_best_practices/`, `docs/source/_generated/examples/3_best_practices/*.md`, built HTML.
- PASS: all 3_best_practices examples pass; Sphinx build exits 0 with no new warnings;
  generated pages inspected for broken rendering / stale outputs / inconsistent command names.
- FAIL = blocker (unless the feature is explicitly scoped out of the release).

### Phase 4 — CLI help and CLI behavior

Help capture for root + all public subcommands (circuit, simulate, submit, result, config,
task, backend list/show/update/chip-display, calibrate, gateway, sync, doctor), plus
`python -m uniqc.cli --help`. Behavioral workflows with a 2-qubit Bell OriginIR file:

```bash
uv run uniqc circuit <bell.originir> --info
uv run uniqc simulate <bell.originir>
uv run uniqc submit <bell.originir> --backend dummy:local:simulator --wait
uv run uniqc submit <bell.originir> --backend dummy:local:virtual-line-3 --wait
uv run uniqc submit <bell.originir> --backend dummy:originq:WK_C180 --dry-run
uv run uniqc backend update --platform originq
uv run uniqc backend list --platform originq
uv run uniqc backend show originq:WK_C180
uv run uniqc backend chip-display originq/WK_C180 --update
```

AI-hint paths: `uv run uniqc config list --ai-hint`, `uniqc config always-ai-hint on`
(subsequent command prints hints), then `uniqc config always-ai-hint off`.

- PASS: every documented command exists and behaves as documented; AI hints appear as specified.
- FAIL = blocker when a docs-required command disagrees with help/behavior.

### Phase 5 — Gateway frontend and API

```bash
cd frontend && npm ci && npm run build
uv run uniqc gateway status
uv run uniqc gateway start --host 127.0.0.1 --port 18765   # background
curl /api/health /api/version /api/backends /api/tasks
```

- PASS: frontend builds; server starts; endpoints return 200 with expected schema;
  built React app served; `/api/backends` does not enumerate `dummy:<platform>:<backend>`
  chip-backed pseudo-backends. Browser automation (Playwright) if available; otherwise
  HTTP + built-asset inspection and visual coverage marked as a gap.
- FAIL = blocker (frontend build or gateway start failure).

### Phase 6 — Real-platform validation

- Discovery: `uniqc backend update --platform <p>` for originq/quark/tianyan/logicalqubit/ibm
  (as available), `uniqc backend list --platform originq`.
- Dry-run: `uniqc submit bell.originir --backend originq:<chip> --dry-run` (and equivalent
  for quark/tianyan where supported).
- Execution: **only with explicit maintainer quota authorization** — one small-shot Bell
  task on OriginQ; record backend, shots, task ID, submit/retrieval times, result summary.
  Without authorization: BLOCKED with exact reason.
- PASS: discovery + dry-run succeed for configured platforms, or each failure has a
  documented external cause (token/SDK/region/network).

### Phase 7 — Programmatic documentation alignment

Scripted checks (scripts written ad-hoc, output captured in the report):

- `pyproject.toml [project.scripts]` has `uniqc = "uniqc.cli.main:app"`; docs use
  `uniqc` / `python -m uniqc.cli` (no `python -m uniqc`).
- Every command documented in `docs/source/4_cli/` exists in `uniqc --help`; no
  `uniqc workflow` subcommand claimed as CLI.
- Docs do not recommend removed import paths: `uniqc.transpiler`, `uniqc.task`,
  `uniqc.qasm`, `uniqc.originir`, `uniqc.pytorch`, `uniqc.analyzer`.
- Dummy backend grammar semantics consistent across docs and `resolve_dummy_backend`.
- Config path `~/.uniqc/config.yaml`; AI hints via `--ai-hints` / `--ai-hint` /
  `UNIQC_AI_HINTS=1` / `uniqc config always-ai-hint on`.
- IBM proxy nested key path `uniqc config set ibm.proxy.https ...` documented and functional.
- `[quark]` requires Python ≥ 3.12 and is in `[all]` on supported interpreters.

## Release Recommendation Rules (applied)

- `DO NOT RELEASE`: default-test failures on maintained deps; best-practices/docs build
  failure; CLI/docs disagreement on a recommended-path command; gateway frontend/API
  failure; real discovery/dry-run failure without external cause; docs claim a workflow
  that execution disproves; stale release artifacts in root.
- `RELEASE WITH KNOWN GAPS`: gaps external, documented, off the recommended path.
- `RELEASE`: all mandatory phases pass; untested areas non-critical and maintainer-approved.
