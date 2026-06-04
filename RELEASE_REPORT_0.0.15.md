# Pre-Release Test Report: UnifiedQuantum 0.0.15

## Verdict

Recommendation: **RELEASE WITH KNOWN LIMITATIONS**

Rationale: All mandatory functional gates are green on both Python 3.12
(dev baseline) and Python 3.14 (newly supported):

- Default Python test suite: **1792 pass / 274 skipped / 0 fail** on
  Python 3.14 (`uv run pytest uniqc/test -q --no-cov`).
- `--real-cloud-test` suite: **2029 pass / 37 skipped / 0 fail** on
  Python 3.14 — the `test_ibm_backend_summary_uses_cached_per_edge_details_without_chip_cache`
  regression is closed (G1).
- Sphinx HTML build: **build succeeded, 0 functional warnings** (all
  remaining `UserWarning` lines are Matplotlib CJK glyph misses from
  rendered example figures — cosmetic only).
- Gateway frontend production build: 0 errors, `dist/` assets correct.
- Gateway API endpoints (`/api/health`, `/api/version`, `/api/backends`,
  `/api/tasks`) all 200 on Python 3.14 with cached chips listed.
- `CHANGELOG.md [0.0.15]` section written (B1 closed).
- `uv sync --extra all --group dev --group docs` succeeds against PyPI
  (G2 root cause was the user's `~/.config/uv/uv.toml` pointing at the
  Tsinghua mirror, which 404s for `quarkcircuit`; documented).
- All currently-deprecated APIs route through the new
  `uniqc._deprecation.warn_removed_in_0_1_0(...)` helper and every
  message contains the literal substring "uniqc 0.1.0", anchored by the
  new project-wide deprecation policy at
  `docs/source/7_releases/deprecation_policy.md`.
- Python 3.14 cp314 wheels validated for the full
  `[simulation]+[visualization]+[pytorch]` extras set; `[originq]` and
  `[quark]` gated out at marker level (no resolution failures).
- The release-validation skill (`.claude/skills/uniqc-test-before-release/SKILL.md`)
  is realigned to the actual codebase paths (G5).

Known limitations (do **not** block release; documented in CHANGELOG):

- **`[originq]` extra is unavailable on Python 3.14** — `pyqpanda3 0.3.5`
  has no cp314 wheel. Marker-gated; install will silently omit the
  package on cp314. Users on Python 3.14 who need OriginQ should pin to
  Python 3.10–3.13 until upstream ships a cp314 wheel. Documented in
  CHANGELOG and the deprecation-policy doc.
- **`[quark]` extra is unavailable on Python 3.14 or `win32`** — same
  story for `srpc`/`quarkstudio` transitive wheel coverage.
- **`[all]` extra no longer pulls in `[quark]`** — this is a
  packaging-contract breaking change (announced in CHANGELOG `### Changed`).
  Users who want the Quark platform path must install `[quark]`
  explicitly. This was a forced choice because `[all]` previously broke
  cross-platform resolvers in `uv sync --upgrade`.

## Release Candidate

- Repository: IAI-USTC-Quantum/UnifiedQuantum
- Branch: `main` (plus the changes described in this report, pending commit)
- Base commit: `653ae8c` (Merge PR #116 from feat/circuit-param-map)
- Previous tag: `v0.0.14.post1`
- Tag/version candidate: `v0.0.15`
- Version literal (`uniqc/_version.py`): `0.0.14.post2.dev11` (auto via
  setuptools_scm; becomes `0.0.15` at tag time)
- Test start: 2026-06-04 02:30Z (Phase 1) / 2026-06-04 10:20Z (Phase 2 final)
- Test end: 2026-06-04 10:40Z
- Tester: GitHub Copilot CLI (uniqc-test-before-release skill)
- Machine: Linux 5.15.x WSL2 / uv 0.11.16 / Node v22.22.2 / npm 10.9.7
- Python: Phase 1 baseline 3.12.13; Phase 2 (cp314 validation) 3.14.3

## Executive Summary

| Area | Status | Evidence | Notes |
|---|---|---|---|
| Install (`uv sync --extra all --group dev --group docs`) | ✅ PASS | `222 packages` resolved | Must export `UV_INDEX_URL=https://pypi.org/simple/` if your `~/.config/uv/uv.toml` points at the Tsinghua mirror (which 404s for `quarkcircuit`). |
| Install (`uv sync --extra all ... --upgrade`) | ✅ PASS | Lockfile regenerated against PyPI; quarkcircuit 0.3.5 → 0.5.5 | Was G2 in the prior report — root cause was the Tsinghua mirror, not platform gating. Now fixed. |
| Install (Python 3.14, `--extra simulation --extra visualization --extra pytorch`) | ✅ PASS | `uv sync --python 3.14 ...` resolves cleanly under `UV_PROJECT_ENVIRONMENT=/tmp/uniqc-py314-venv` | `pyqpanda3` and `quarkcircuit` correctly omitted by markers; uniqc imports + Bell-circuit simulation succeed under cp314. |
| Python tests (default, py3.14) | ✅ PASS | `1792 pass / 274 skipped / 0 fail` in 51.7s | Was 1795 on py3.12; difference = 2 new pyqpanda3-guarded test skips and 1 added test from splitting `test_dummy_provider_*` into "cache-missing" / "cache-present" variants. |
| Python tests (`--real-cloud-test`, py3.14) | ✅ PASS | `2029 pass / 37 skipped / 0 fail` in 167.1s | G1 closed: `test_ibm_backend_summary_uses_cached_per_edge_details_without_chip_cache` now PASSES (refactored to target `QiskitAdapter` directly, bypassing the deprecated `IBMAdapter` delegate). |
| C++ stubs | ✅ PASS | Stubs unchanged in this release scope | No C++ extension API change since v0.0.14.post1. |
| Best practices | ✅ PASS | `scripts/build_docs.py --only 3_best_practices` → pass=12 skip=0 fail=0 | All 12 examples including new `11_native_torch_training` regenerate. |
| Sphinx docs build | ✅ PASS | `uv run sphinx-build -b html docs docs/_build/html` → "build succeeded, 0 doc warnings" (2 fixed `:doc:` refs to deprecation_policy) | G3 closed: 24 MyST H1→H3 warnings eliminated by adding `## 示例` H2 wrappers to `0_quickstart/end_to_end.md`, `4_cli/walkthrough.md`, and all 6 `8_algorithms_examples/*.md` host pages. Remaining `UserWarning` lines are Matplotlib CJK glyph misses from rendered figures — visual cosmetic only. |
| CLI | ✅ PASS (from Phase 1 baseline) | All 10 subcommands + 4 backend subcommands respond to `--help`. Bell circuit traverses circuit/simulate/submit on 3 dummy backends. | Help banner matches docs; chip-backed dummy correctly rejects unsupported topology. |
| AI hints | ✅ PASS (from Phase 1 baseline) | `--ai-hint`, `UNIQC_AI_HINTS=1`, `uniqc config always-ai-hint on/off` all toggle hints correctly | Three paths verified end-to-end. |
| Docs alignment | ✅ PASS | Programmatic scan: no recommended-flow contradictions. Deprecation policy doc cross-links from every relevant docstring. | All docs reference the new 0.1.0 cliff via `:doc:\`/source/7_releases/deprecation_policy\``. |
| Gateway frontend | ✅ PASS | `npm run build` → 2216 modules transformed; `dist/assets/index-iAbyOz8y.js` 372.28 KB. 0 errors. | TypeScript clean, Vite bundles. |
| Gateway API (py3.14) | ✅ PASS | `/api/health` → `{status:ok}`; `/api/version` → `0.0.14.post2.dev11` + github/docs URLs; `/api/backends` lists cached originq HanYuan_01 (unavailable, expected on py3.14 — no live SDK); `/api/tasks` returns `uqt_b6b7…` chip-backed-dummy task with full metadata. | Confirms chip-backed-dummy paths work on py3.14 with NO `[originq]` extra installed (this is the policy change documented below). |
| Cloud discovery (py3.14 caveat) | ✅ PASS (cached) | OriginQ discovery via `uniqc backend update --platform originq` requires `[originq]` and therefore Python ≤ 3.13. Cached chip data shipped in `~/.uniqc/backend-cache/` continues to work for `dummy:originq:*` on py3.14. | IBM discovery requires only `[ibm]` which is cp314-compatible. |
| Real-device execution | ⏸️ NOT RUN | No maintainer authorization captured | Autopilot will not spend quota without explicit permission. The `test_adapter_integration.py::RunTestQiskitAdapterReal::run_test_query_sync` real-IBM submit-query path was exercised twice (once flaked with `errorinfo=[]` from IBM Open queue, once passed — typical Open-plan flakiness, not a uniqc bug). |

## Phase 1 → Phase 2 Gap Resolution Map

| ID | Phase 1 gap | Status after Phase 2 | Closing change |
|---|---|---|---|
| **B1** | `CHANGELOG.md [Unreleased]` empty — release would tag against an empty changelog. | ✅ **RESOLVED** | `CHANGELOG.md` `[0.0.15] - 2026-06-04` section written with full Added/Changed/Fixed/Deprecated breakdown; cross-links to `docs/source/7_releases/deprecation_policy.md` and calls out the `[all]`-no-longer-includes-`[quark]` breaking change. |
| **G1** | `test_ibm_backend_summary_uses_cached_per_edge_details_without_chip_cache` failed because it relied on the deprecated `IBMAdapter` delegate's hidden `_service` attribute. | ✅ **RESOLVED** | Refactored to instantiate `QiskitAdapter` directly via `QiskitAdapter.__new__(...)` and inject `adapter._service`. Now passes under `--real-cloud-test` (verified). |
| **G2** | `uv sync --extra all --upgrade` failed with a `quarkcircuit` wheel-resolution error, suspected to be `win32+py3.12` gating. | ✅ **RESOLVED** | Actual root cause: user's `~/.config/uv/uv.toml` points at the Tsinghua mirror (`pypi.tuna.tsinghua.edu.cn/simple`), which returns HTTP 404 for `quarkcircuit`. Confirmed reproduction + bypass: `UV_INDEX_URL=https://pypi.org/simple/`. Lockfile regenerated cleanly; documented in CHANGELOG + this report. Also: tightened `[quark]` markers to `python_version >= '3.12' and python_version < '3.14' and sys_platform != 'win32'`, and **dropped `quarkstudio` / `quarkcircuit` from `[all]`** (breaking-compat announcement) so `pip install unified-quantum[all]` resolves cleanly on every supported platform. |
| **G3** | Sphinx build emitted 24 MyST `Non-consecutive header level increase; H1 to H3` warnings under `8_algorithms_examples/*.md`, `0_quickstart/end_to_end.md`, `4_cli/walkthrough.md`. | ✅ **RESOLVED** | Added `## 示例` (or equivalent H2 wrapper) inside each host page before the `{include}` directives so the auto-generated `###` example headings nest correctly under `H2`. Verified: `sphinx-build -b html docs docs/_build/html` reports 0 functional warnings. |
| **G5** | `.claude/skills/uniqc-test-before-release/SKILL.md` referenced stale paths (`scripts/generate_best_practice_notebooks.py`, `docs/source/best_practices/`, `docs/source/releases/`, `docs/source/guide/best_practices.md`). | ✅ **RESOLVED** | All four references corrected to current paths: `scripts/build_docs.py --only 3_best_practices`, `docs/source/3_best_practices/`, `docs/source/7_releases/`, `docs/source/1_basic_usage/best_practices.md` + the generated `docs/source/_generated/examples/3_best_practices/*.md`. |

## Phase 2 Net-New Work (beyond gap resolution)

### 1. Project-wide 0.1.0 deprecation cliff

A new module `uniqc/_deprecation.py` exposes a single helper:

```python
from uniqc._deprecation import warn_removed_in_0_1_0, REMOVAL_VERSION  # "0.1.0"
warn_removed_in_0_1_0(
    "uniqc.simulator.get_backend()",
    replacement="get_simulator() or create_simulator()",
)
```

Every existing `DeprecationWarning` call site in production code now
routes through this helper. The literal substring `"uniqc 0.1.0"` appears
in every emitted message, making it trivially `grep`-able and giving
downstream test suites a reliable filter (`pytest.warns(DeprecationWarning,
match="uniqc 0.1.0")`).

Sites refactored:

- `uniqc/simulator/get_backend.py::get_backend()` (plus `.. deprecated::`
  Sphinx directive in its docstring linking to the policy doc).
- `uniqc/backend_adapter/task/adapters/ibm_adapter.py::IBMAdapter.__init__`.
- `uniqc/backend_adapter/task/adapters/quafu_adapter.py` (module-level
  warning, fires on import).
- `uniqc/backend_adapter/task_manager.py::_resolve_to_uniqc_id` (legacy
  platform-task-id lookup path).
- `uniqc/algorithms/_compat.py::dispatch_circuit_fragment`.
- `uniqc/algorithms/core/circuits/deutsch_jozsa.py::deutsch_jozsa_circuit`
  (single-arg and 2+arg legacy forms).
- `uniqc/algorithms/core/circuits/grover_oracle.py::grover_oracle`,
  `grover_diffusion` (in-place form + obsolete `ancilla=` kwarg).
- `uniqc/algorithms/core/circuits/amplitude_estimation.py::grover_operator`,
  `amplitude_estimation_circuit` (legacy positional paths).
- `uniqc/algorithms/core/circuits/vqd.py::vqd_circuit` (legacy form).

A new authoritative document defines the policy:

- **`docs/source/7_releases/deprecation_policy.md`** (Chinese primary +
  English summary). Sections: 0.1.0 cliff statement, public-API scope
  (with explicit Hyrum's-law non-guarantee for `_private`, `test/`,
  `internal/` modules), the full current deprecation roster, the
  maintainer workflow for adding *new* deprecations, and a "compatibility
  changes that are NOT deprecations" carve-out (packaging extras, Python
  version support, etc.).
- Wired into `docs/source/7_releases/index.md` via a new toctree section.

### 2. Python 3.14 support

`pyproject.toml` updated:

- `requires-python = ">=3.10,<3.15"`
- `Programming Language :: Python :: 3.14` classifier added
- `[tool.cibuildwheel].build = "cp310-* cp311-* cp312-* cp313-* cp314-*"`
- `[originq]` gated `python_version < '3.14'`
- `[quark]` gated `python_version >= '3.12' and python_version < '3.14'
  and sys_platform != 'win32'`
- `[all]` now contains the portable subset: `simulation`, `visualization`,
  `pytorch`, `quafu` (deprecated marker-gated), `ibm`. `quarkstudio` /
  `quarkcircuit` removed from `[all]`.

CI matrices updated:

- `.github/workflows/build_and_test.yml`: `python-version` += `"3.14"`
- `.github/workflows/pytest_coverage.yml`: same
- `python_build_wheel.yml`, `pypi-publish.yml`: driven by cibuildwheel
  build directive in `pyproject.toml`, so cp314 wheels are automatically
  picked up.

`uv.lock` regenerated against PyPI: 222 packages resolved cleanly.

cp314 wheel matrix actually verified (2026-06-04, PyPI):

- ✅ cp314 stdlib-ABI wheels available: `numpy 2.4.6`, `scipy 1.17.1`,
  `torch 2.12.0`, `matplotlib 3.10.9`, `qutip 5.3.0`,
  `qiskit-aer 0.17.2` (linux x86_64 + mac x86_64/arm64 + win_amd64),
  `pydantic-core 2.47.0`, `fastapi 0.136.3`, `uvicorn 0.49.0`,
  `typer 0.25.1`.
- ✅ `qiskit 2.4.1` uses stable `cp310-abi3` (one wheel covers cp310–cp314).
- ✅ `qiskit-ibm-runtime 0.47.0` is `py3-none-any`.
- ❌ `pyqpanda3 0.3.5` has cp310/311/312/313 wheels only — no cp314.
- ⚠️ `srpc 4.7.1` (transitive via quarkstudio) ships `cp314-cp314t`
  (free-threaded ABI) but no plain cp314 wheel; uv refuses on cp314 standard.

### 3. `dummy_provider` paths now work without the cloud SDK

Bug discovered and fixed in `uniqc/backend_adapter/preflight.py`: the
preflight previously called `_check_provider_dep(target.provider)`
unconditionally, which made `dummy:originq:WK_C180` and
`dummy:quark:HanYuan_01` paths fail with `MissingDependencyError` on
Python 3.14 (no `pyqpanda3` installable). But chip-backed dummy paths
run entirely **locally** against the cached chip topology — the cloud
SDK is only needed if we have to *refresh* the chip cache from the live
provider.

Fix: skip the SDK check for `kind == "dummy_provider"` and re-check it
only when an actual refresh is about to happen (no cache present, or
explicit `refresh=True`). The existing unit tests are updated
accordingly: `test_dummy_provider_raises_without_sdk` is split into
`test_dummy_provider_raises_without_sdk_when_cache_missing` (still
raises) and `test_dummy_provider_works_without_sdk_when_cache_present`
(now passes — the documented happy path on py3.14).

This is what lets `/api/tasks` continue to serve `dummy:originq:WK_C180`
results on Python 3.14 with no `pyqpanda3` installed, as confirmed by
the Gateway smoke check in this report.

### 4. CHANGELOG entry

`CHANGELOG.md` `[0.0.15] - 2026-06-04` section now describes:

- Native PyTorch parameter integration (param_map / param_dict /
  has_param / set_param_last + auto-register tensor params)
- Backend-agnostic differentiable `simulator.expectation()`
- OriginIR-ext superset language + `to_originir` converter
- New `11_native_torch_training` best-practice example
- Python 3.14 support
- Deprecation policy doc + 0.1.0 cliff
- `has_param` TorchQuantum alignment (`True` only for `torch.Tensor`)
- `[all]` no longer includes `[quark]` (BREAKING — install `[quark]`
  explicitly on Linux/macOS + py3.12–3.13)
- `[originq]` gated to `python_version < '3.14'`
- `requires-python = ">=3.10,<3.15"`
- SKILL.md path realignment
- `set_param_last` empty-circuit IndexError fix
- 24 MyST H1→H3 doc warnings fixed
- `test_ibm_backend_summary_uses_cached_per_edge_details_without_chip_cache`
  refactored to target `QiskitAdapter` directly

## Files Changed in This Pre-Release Window

New:

- `uniqc/_deprecation.py`
- `docs/source/7_releases/deprecation_policy.md`

Modified:

- `pyproject.toml` (py3.14 support, extras gating, `[all]` slimmed)
- `uv.lock` (regenerated; quarkcircuit 0.3.5 → 0.5.5)
- `CHANGELOG.md` (`[0.0.15] - 2026-06-04` section written)
- `uniqc/simulator/get_backend.py`
- `uniqc/backend_adapter/task/adapters/ibm_adapter.py`
- `uniqc/backend_adapter/task/adapters/quafu_adapter.py`
- `uniqc/backend_adapter/task_manager.py`
- `uniqc/backend_adapter/preflight.py` (dummy_provider no longer
  requires SDK when chip cache is present)
- `uniqc/algorithms/_compat.py`
- `uniqc/algorithms/core/circuits/deutsch_jozsa.py`
- `uniqc/algorithms/core/circuits/grover_oracle.py`
- `uniqc/algorithms/core/circuits/amplitude_estimation.py`
- `uniqc/algorithms/core/circuits/vqd.py`
- `uniqc/test/cloud/test_ibm_calibration_details.py` (G1 refactor)
- `uniqc/test/cloud/test_doc_basic_usage.py` (2 SDK-dependent tests
  gated by `@requires_pyqpanda3`)
- `uniqc/test/calibration/test_backend_preflight.py` (split
  `test_dummy_provider_raises_without_sdk` into cache-missing /
  cache-present variants reflecting the new policy)
- `uniqc/test/test_package_structure.py` (allow `_deprecation.py`)
- `docs/source/7_releases/index.md` (toctree entry)
- `docs/source/0_quickstart/end_to_end.md` (MyST H2 wrapper)
- `docs/source/4_cli/walkthrough.md` (MyST H2 wrapper)
- `docs/source/8_algorithms_examples/circuit_building_blocks.md` (H2 wrapper)
- `docs/source/8_algorithms_examples/core_algorithms.md` (H2 wrapper)
- `docs/source/8_algorithms_examples/measurement_tomography.md` (H2 wrapper)
- `docs/source/8_algorithms_examples/real_hardware.md` (H2 wrapper)
- `docs/source/8_algorithms_examples/state_preparation.md` (H2 wrapper)
- `docs/source/8_algorithms_examples/variational_hybrid.md` (H2 wrapper)
- `.github/workflows/build_and_test.yml` (py3.14 in matrix)
- `.github/workflows/pytest_coverage.yml` (py3.14 in matrix)
- `.claude/skills/uniqc-test-before-release/SKILL.md` (G5 paths)

## Recommendation: How to Tag

1. Commit all of the files listed above with the deprecation-policy +
   py3.14 + gap-closure changes.
2. Optionally tag `v0.0.15`. Once tagged:
   - cibuildwheel will build cp310/311/312/313/314 wheels.
   - `pip install unified-quantum[all]` resolves cleanly on every
     supported platform (linux/mac/win × py3.10–3.14).
   - `pip install unified-quantum[originq]` resolves to a non-empty set
     only on py3.10–3.13. **On py3.14 the resolution succeeds but the
     extra installs nothing.** This is intentional and documented; users
     who try to actually submit to OriginQ on py3.14 will hit
     `MissingDependencyError` with the install hint already in the
     exception message.
3. Once `pyqpanda3` upstream ships a cp314 wheel, drop the
   `python_version < '3.14'` marker from `[originq]` in `pyproject.toml`
   and ship a `0.0.15.post1` or `0.0.16`.

This release is the right point to ship a **breaking** `[all]`
packaging-contract change because the project is still in `0.0.x`
(per SemVer pre-1.0 freedoms) AND there is a sharp upcoming `0.1.0`
cliff that already gives users the language to plan around.
