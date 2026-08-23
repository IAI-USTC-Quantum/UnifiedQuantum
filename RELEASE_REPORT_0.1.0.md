# Pre-Release Test Report — v0.1.0

## Verdict

Recommendation: **RELEASE WITH KNOWN GAPS**

All mandatory local phases pass: default test suite (2488 passed / 0 failed),
best-practices docs gate, CLI help/behavior, docs alignment, gateway frontend
build and API. The gaps are external and documented: (1) OriginQ live backend
discovery fails inside the upstream `pyqpanda3` 0.4.1 SDK (latest on PyPI) —
our stale-cache fallback keeps the feature functional; (2) the configured IBM
token is rejected by IBM Quantum ("Unable to retrieve instances") — credential
issue, not code; (3) no real quantum task was submitted because quota
authorization was not granted for this run; (4) gateway visual rendering was
verified over HTTP/assets only (no browser automation available).

## Release Candidate

- Repository: `IAI-USTC-Quantum/UnifiedQuantum` (local `/home/agony/projects/uniqc-dev/UnifiedQuantum`)
- Branch: `main` (10 commits ahead of `origin/main`)
- Commit: `a49d106` (`docs: refresh example-exec-logs and generated pages`)
- Tag/version candidate: `v0.1.0` (validated when version metadata read `0.0.17.post2.dev26`; the maintainer chose `v0.1.0` for the removal release per the deprecation policy)
- Test start/end time: 2026-08-23 ~20:40 – ~21:35 (local)
- Tester/agent: Kimi Code CLI (uniqc-test-before-release skill)
- Machine/OS/Python/Node: Linux 7.0.0-28-generic x86_64, Python 3.12.3, Node 24.18.0 / npm 11.16.0, uv 0.12.1

## Executive Summary

| Area | Status | Evidence | Notes |
|---|---|---|---|
| Python tests | PASS | `2488 passed, 220 skipped, 0 failed` in 212s (`/tmp/prt_pytest_default.log`) | `--real-cloud-test` variant NOT RUN — submits real quantum tasks, needs quota authorization |
| Best practices | PASS | `build_docs: pass=12 skip=0 fail=0`; Sphinx rc=0, 0 warnings | residual git diff limited to `duration_seconds` (by design since `35d5196`) |
| CLI | PASS | 17/17 help captures clean (`/tmp/prt_cli/`); workflows in `/tmp/prt_cli_wf/` | see findings on `chip-display --update` below |
| AI hints | PASS | `--ai-hint`, `always-ai-hint on/off`, `UNIQC_AI_HINTS=1` all verified (`/tmp/prt_cli_wf/aihints.log`) | |
| Docs alignment | PASS | scripted checks `/tmp/prt_docsalign.log` | no stale import-path recommendations; no `python -m uniqc`; no phantom `workflow` command |
| Gateway frontend | PASS | `npm ci` + `npm run build` rc=0, `dist` assets built in 4.81s | visual rendering NOT RUN (no Playwright/browser) — gap |
| Gateway API | PASS | `/api/health` `/api/version` `/api/backends` `/api/tasks` all HTTP 200; root serves built React app; `/assets/*` 200 | chip-backed `dummy:<platform>:<backend>` correctly absent from backend list |
| Cloud discovery | PASS WITH GAPS | quark ✓ (5), tianyan ✓ (15), logicalqubit ✓ (5) live; originq/ibm fall back to stale cache | originq: upstream `pyqpanda3` 0.4.1 failure; ibm: invalid token (external) |
| Real-device execution | BLOCKED | not attempted | requires explicit maintainer quota authorization (not granted this run) |
| Calibration/QEM/XEB | PASS | default suite + best-practices examples `09_calibration_qem_dummy`, `10_xeb_workflow_dummy` pass | dummy-path calibration cache + QEM TTL exercised |

## Blocking Issues

None.

## Non-Blocking Gaps

1. **OriginQ live discovery broken upstream** — `pyqpanda3 0.4.1` (latest on PyPI,
   verified) raises `RuntimeError: value is not array (which is 3)` from
   `QCloudService.backends()` when called directly with the configured token,
   i.e. below our adapter layer (reproduced via raw SDK call). Effect: `uniqc
   backend update --platform originq` prints a warning and serves the stale
   cache (7 backends, still listed/usable); `backend show`/`chip-display`
   work from cache; dry-run against `dummy:originq:WK_C180` works. Risk
   accepted as external — the OriginQ cloud API response shape appears to have
   changed upstream of the pinned-compatible SDK. Suggested follow-up: report
   to pyqpanda3 / pin or patch once upstream fixes; not introduced by this
   release's changes.
2. **IBM token rejected** — `qiskit-ibm-runtime`: "Unable to retrieve instances.
   Please check that you are using a valid API token." on both discovery and
   `ibm:ibm_fez` dry-run. Credential/expiration issue on the maintainer side,
   not a code defect; stale cache (3 backends) is served as fallback.
3. **Real-device execution not run** — Phase 6 execution bucket and the
   `--real-cloud-test` pytest variant submit real quantum tasks; they were not
   run because quota authorization was not granted for this validation run.
   Maintainer must either authorize a post-report run (one small-shot Bell task
   on OriginQ) or explicitly accept this gap before tagging.
4. **Gateway visual coverage** — no Playwright/browser on this host; the React
   app was verified via `npm run build`, served `index.html`/asset HTTP 200s,
   and API schema inspection. Visual/interaction testing remains a gap.

## Environment and Setup

- `uv sync --extra all --group dev --group docs --upgrade` → rc=0 (262 packages resolved).
- `cd frontend && npm ci` → rc=0.
- `uv run uniqc --version`/help available; console script `uniqc = "uniqc.cli.main:app"` confirmed in `pyproject.toml`.
- `uniqc_cpp`: `import uniqc_cpp` OK; `StatevectorSimulator`, `DensityOperatorSimulator` exposed (note: the wheel exposes no `__version__` attribute — informational only).
- Config: `~/.uniqc/config.yaml`, profile `default`, `config_version=1`; tokens present for originq/ibm/quark/tianyan/logicalqubit.

## Best-Practices Validation

Command: `uv run python scripts/build_docs.py --only 3_best_practices` →
`pass=12 skip=0 listed=0 fail=0`; Sphinx HTML build rc=0 with 0 WARNING/ERROR.

| File | Execution | Key output checked | Mismatch |
|---|---|---|---|
| `00_config_and_backend_cache` | pass | config init/set/list, backend cache listing | none |
| `01_bare_circuit_simulation` | pass | local sim counts ~50/50, figure generated | none |
| `02_named_circuit_and_reuse` | pass | named-circuit reuse, figure | none |
| `03_compile_region_dummy_backend` | pass | region compile against dummy chip | none |
| `04_api_submit_dummy_result` | pass | submit/wait/result via API | none |
| `05_cli_workflow_dummy` | pass | CLI round-trip in subprocess | none |
| `06_cloud_backend_template` | pass | dry-run + API templates (runs since originq creds present) | none |
| `07_variational_circuit` | pass | parameter binding, figure | none |
| `08_torch_quantum_training` | pass | TorchQuantum training converges, figure | none |
| `09_calibration_qem_dummy` | pass | readout calibration → QEM mitigation | none |
| `10_xeb_workflow_dummy` | pass | XEB cycle benchmarking + fit | none |
| `11_native_torch_training` | pass | native torch training loop, figure | none |

The best-practices chapter is aligned with software behavior. Post-run git diff
is limited to `duration_seconds` fields — the determinism work in `35d5196`
(fixed seeds, task-id/timestamp normalization, stable SVG ids) eliminates
content jitter; a content diff on future runs now indicates real behavior change.

## CLI Validation

- Help captured for root + `circuit simulate submit result config task backend
  (list/show/update/chip-display) calibrate gateway sync doctor` and
  `python -m uniqc.cli --help` — 17/17 clean, no errors (`/tmp/prt_cli/`).
- Behavioral workflows (`/tmp/prt_cli_wf/`): `circuit --info` ✓ (2q/2c/depth2),
  `simulate` ✓ (~50/50 Bell), `submit --backend dummy:local:simulator --wait` ✓,
  `submit --backend dummy:local:virtual-line-3 --wait` ✓.
- `submit --backend dummy:originq:WK_C180 --dry-run` on CNOT(0,1) **correctly
  fails** with "Unsupported topology" — WK_C180 has no 0–1 coupling (verified
  against the chip cache); with a coupled pair (0,9) the dry-run **passes**.
  This is the intended behavior of `6231726 feat(adapters): dry-run validates
  circuit qubits against chip data`.
- `backend update --platform originq` → rc=0 with cache fallback (upstream
  fetch failure, see gap 1); `backend list --platform originq` ✓ (6 shown);
  `backend show originq:WK_C180` ✓ (fidelity/coherence from cache);
  `backend chip-display originq/WK_C180` ✓ from cache; `--update` fails for
  originq (same upstream cause) but **works live for `quark/Baihua` and
  `tianyan/tianyan176`** — proving the update path itself is intact.
- AI hints: `config list --ai-hint` shows the hints panel ✓;
  `config always-ai-hint on` → subsequent plain `config list` shows hints ✓;
  `config always-ai-hint off` → hints gone ✓; `UNIQC_AI_HINTS=1 uniqc doctor`
  shows hints ✓ (`/tmp/prt_cli_wf/aihints.log`).
- Docs match help output and behavior. No `uniqc workflow` subcommand exists or
  is claimed; `python -m uniqc.cli` works and is the documented module fallback.

## Gateway Frontend/API Validation

- Build: `npm ci` rc=0; `npm run build` rc=0 (`dist/assets/index-*.js` 372.6 kB).
- Server: `uniqc gateway status` (correctly reported not running) →
  `uniqc gateway start --host 127.0.0.1 --port 18765`; afterwards
  `uniqc gateway stop` cleanly stopped it.
- Endpoints (all HTTP 200): `/api/health` (`{"status":"ok"}`),
  `/api/version` (`0.0.17.post2.dev36` + github/docs URLs),
  `/api/backends` (originq 7 / quark 5 / ibm 3 / dummy 5 / tianyan 15 /
  logicalqubit 5; **no chip-backed `dummy:<platform>:<backend>` enumerated**;
  originq entries correctly flagged `cache_stale: true`),
  `/api/tasks` (dummy tasks incl. OriginIR metadata).
- Frontend rendering: `GET /` serves the built React app (`index.html`
  referencing hashed assets), `GET /assets/index-*.js` → 200. Rendering
  method: HTTP + built-asset inspection. **Visual testing gap**: no browser
  automation available on this host.

## Cloud and Real-Device Validation

**Discovery** (`uniqc backend update --platform <p>`, `/tmp/prt_discovery.log`):

| Platform | Result | Note |
|---|---|---|
| originq | stale-cache fallback (7) | upstream `pyqpanda3` 0.4.1 `backends()` RuntimeError — external |
| quark | live ✓ 5 backends | |
| tianyan | live ✓ 15 backends | |
| logicalqubit | live ✓ 5 backends | |
| ibm | stale-cache fallback (3) | "Unable to retrieve instances… valid API token" — credential issue, external |

**Dry-run** (`/tmp/prt_dryrun.log`): `quark:Baihua` ✓ (advisory: shots should be
a multiple of 1024), `tianyan:tianyan176` ✓ (offline, existence checked at
submission), `logicalqubit:QZ02` ✓ (OriginIR → lqcloud translation clean),
`ibm:ibm_fez` ✗ (same invalid-token cause). OriginQ chip-backed dry-run via
`dummy:originq:WK_C180` ✓ with a topology-valid pair.

**Execution**: NOT RUN — no maintainer quota authorization in this run. No task
IDs to report. This is the one remaining evidence item before an unconditional
release sign-off.

## Programmatic Documentation Alignment

Scripted (`/tmp/prt_docsalign.log`) unless noted:

- Comparison: console script entry vs docs. Source: `pyproject.toml`. Result:
  `uniqc = "uniqc.cli.main:app"` present; docs use `uniqc` / `python -m uniqc.cli`. Mismatches: none.
- Comparison: `[quark]` gating. Source: `pyproject.toml`. Result:
  `quarkstudio`/`quarkcircuit` carry `python_version >= '3.12'` markers and are
  included in `[all]` under the same marker. Mismatches: none.
- Comparison: commands referenced in `docs/source/4_cli/*.md` vs `uniqc --help`.
  Result: all documented subcommands exist (actual: backend, calibrate,
  circuit, config, doctor, gateway, result, simulate, submit, sync, task);
  the only regex outlier was Chinese prose (`uniqc 布局的`, false positive —
  manual check). `workflow` is not a CLI command and is not claimed as one.
  Mismatches: none.
- Comparison: removed import paths (`uniqc.transpiler`, `uniqc.task`,
  `uniqc.qasm`, `uniqc.originir`, `uniqc.pytorch`, `uniqc.analyzer`) in
  docs/examples. Result: only mentioned in
  `docs/source/1_basic_usage/best_practices.md` as an explicit **"do not use
  these old entries"** warning, plus historical release notes. Mismatches: none.
- Comparison: `python -m uniqc` bare module references. Result: none found.
- Comparison: config path / AI-hint surface / IBM proxy key. Result:
  `~/.uniqc/config.yaml`, `--ai-hint(s)`, `UNIQC_AI_HINTS`, `always-ai-hint`,
  and `ibm.proxy.https` all documented (manual + grep).
- Dummy backend semantics: verified behaviorally this run — `dummy` and
  `dummy:local:virtual-line-3` run noiseless; `dummy:originq:WK_C180` enforces
  chip topology in dry-run and is not enumerated by `/api/backends` or
  `uniqc backend list` (manual + API JSON check).

## Final Recommendation

**RELEASE WITH KNOWN GAPS.** Everything on the local recommended path passes:
full default test suite, best-practices gate, CLI, AI hints, docs alignment,
gateway frontend build and API, dummy-backend semantics, and live
discovery/dry-run for quark/tianyan/logicalqubit.

Conditions to clear before (or explicitly accept at) tagging:

1. Authorize and run one small-shot real OriginQ task (Bell, ≤1000 shots) plus
   `uv run pytest uniqc/test -v --real-cloud-test`, or record the maintainer's
   explicit acceptance of the untested real-execution path.
2. Note the upstream `pyqpanda3` 0.4.1 OriginQ discovery failure in the release
   notes (stale-cache fallback mitigates; chip-display/dry-run unaffected when
   caches exist).
3. Refresh or re-verify the IBM token if IBM is in this release's supported
   scope; otherwise document IBM live verification as pending credentials.
4. Optionally run a browser-based gateway UI check on a host with Playwright.
