# UnifiedQuantum (`uniqc`) — Copilot instructions

UnifiedQuantum is a lightweight Python framework that gives quantum circuit
construction, local simulation, and multi-platform cloud execution (OriginQ,
Quafu, Quark, IBM) a single unified API, plus a CLI-first workflow and a
calibration/QEM toolchain. The Python package is `uniqc`; a compiled C++
simulator (`uniqc_cpp`) lives under `UniqcCpp/`.

## Environment & build

- Requires Python 3.10–3.14, CMake ≥ 3.22 (release build targets 3.26), a
  C++17 compiler, and git submodules (fmt). **Clone with `--recurse-submodules`** —
  the C++ backend won't build without `UniqcCpp/Thirdparty/fmt`.
- Preferred workflow uses [`uv`](https://github.com/astral-sh/uv). Full dev env:
  ```bash
  uv sync --all-extras --group dev --group docs   # creates .venv, compiles uniqc_cpp
  ```
  Run tools through the env with `uv run ...` (or activate `.venv`).
- **After editing any C++ source under `UniqcCpp/`**, rebuild the pybind11
  extension before running Python tests that touch it:
  `uv pip install -e . --no-deps` (from the activated `.venv`).
- `pyproject.toml` intentionally does **not** pin third-party versions and `main`
  does **not** commit `uv.lock`; dev/CI resolve latest deps to surface upstream
  breakage. Quafu (`pyquafu`) is deliberately excluded from `[all]` (deprecated,
  pins `numpy<2`).

## Test / lint / docs

- Full suite: `uv run pytest uniqc/test`. Config is in `pytest.ini`
  (`testpaths = uniqc/test`).
- **Single test:** `pytest uniqc/test/<path>/test_x.py::<func> -v`, e.g.
  `pytest uniqc/test/core/test_originir_parser.py::run_test_originir_parser -v`.
- pytest collects **both** `test_*` and `run_test_*` functions (see
  `python_functions` in `pytest.ini`); test classes are `Test*`/`RunTest*`.
  Helper functions must **not** use those prefixes or pytest will collect them.
- Tests that submit real circuits to cloud backends are skipped unless you pass
  `--real-cloud-test`. Optional-dependency and credential markers
  (`requires_cpp`, `requires_qiskit`, `requires_originq_credentials`, `cloud`, …)
  auto-skip via `conftest.py`. Tests using a `dummy:<provider>:<chip>` backend are
  auto-marked with that provider's `requires_*` marker (that path needs the real
  SDK + chip cache, not just a local simulator).
- Lint/format: `uv run ruff check .` and `uv run ruff format .`
  (line-length 120, target py310). Install hooks with `pre-commit install`.
- Docs build is two-step (`cd docs && uv run make html`): `scripts/build_docs.py`
  executes every `examples/<chapter>/*.py`, captures output, and refreshes
  `example-exec-logs/`; then Sphinx builds HTML. **If you change user-visible code
  or examples, run `make html` and commit any `example-exec-logs/` diff** — a diff
  is the signal that example behavior changed. `make html-fast` skips example
  re-execution.

## Architecture (the big picture)

Core philosophy: *build a circuit any way → export OriginIR / OpenQASM 2.0 →
`uniqc` CLI (or `submit_task`) executes it anywhere*. The layers:

- **`uniqc/circuit_builder/`** — the opcode-based `Circuit` class and I/O.
  `OriginIR-ext` is a strict **superset** of official (OriginQ-accepted)
  `OriginIR`: it adds extended gates (ECR/ISWAP/XX/YY/ZZ/XY/PHASE2Q/…), the
  `QRAM` instruction, `DEF`/`ENDDEF` subroutines, error channels, and inline
  `dagger`/`controlled_by(...)`. Keep this distinction when emitting IR for real
  hardware vs. local execution.
- **`uniqc/backend_adapter/`** — the unification layer. `QuantumBackend` ABC +
  `get_backend()` factory; concrete `OriginQ/Quafu/Quark/IBM/Dummy` backends.
  `task/adapters/` translate a circuit per platform; `task/normalizers.py`
  normalize raw results into a `UnifiedResult`. Submission is **async**:
  `submit_task()` returns a `task_id`; `poll_result()` is non-blocking,
  `get_result()`/`wait_for_result()` block.
- **`uniqc/compile/`** — compiler/transpiler, OriginIR & QASM parsers, qiskit
  transpiler bridge, `policy.py` (resolve basis gates / submit language per
  backend), timeline, and compatibility validation.
- **`uniqc/simulator/`** — local simulators: C++ `uniqc_cpp` (statevector +
  density matrix), QuTiP, MPS (linear topology), TorchQuantum. All optional and
  behind guarded imports.
- **`uniqc/calibration/`** (XEB + readout) and **`uniqc/qem/`** (M3, readout EM,
  ZNE). Calibration writes `~/.uniqc/calibration_cache/`; QEM reads it and
  enforces TTL freshness.
- **`uniqc/cli/`** — Typer app, entry point `uniqc.cli.main:app` (console script
  `uniqc`). **`uniqc/gateway/`** — FastAPI + websocket management server; the
  `frontend/` React + Vite + Tailwind app is its Web UI.
- **`uniqc/torch_adapter/`** (QuantumLayer, parameter-shift gradients, batch
  execution) and **`uniqc/algorithms/`** (HEA/UCCSD/QAOA ansätze, standard
  circuits, measurement, state prep, training) sit on top of the core.

## Conventions specific to this repo

- **Backend id grammar:** `dummy` = unconstrained noiseless VM;
  `dummy:local:virtual-line-N` / `dummy:local:virtual-grid-RxC` = noiseless with a
  virtual topology; `dummy:<platform>:<backend>` = compile/transpile against a real
  backend, then run locally with that chip's real calibration noise.
- **Endianness:** result bitstring keys place classical bit `c[0]` as the
  **rightmost** character (LSB). The canonical 2-qubit probe (`x(0)`, measure 0
  then 1) yields dominant outcome `"01"`. See `test_endianness_convention.py`.
- **Flat public API:** import common symbols directly from `uniqc`
  (`Circuit`, `get_backend`, `submit_task`, `compile`, `hea`, …). Torch-heavy
  symbols are lazily loaded via module `__getattr__`; keep optional deps out of
  import-time paths.
- **All user state lives under `~/.uniqc/`** (`config.yaml`, `cache/`,
  `backend/` (backend discovery cache `backends.json`, chip cache `chips/`,
  user-defined noisy virtual machines `virtual/*.yaml` used as
  `dummy:virtual:<name>`), `calibration_cache/`). Configure tokens with
  `uniqc config set <platform>.token <TOKEN>`.
- **Ruff ignores** `E501`, `N801`, `N803`, `N806` on purpose (physics-notation
  variable names like `U`, `H`, `K`, `E`; CapWords loader classes).
- **Deprecation policy:** public APIs marked with `DeprecationWarning` in `0.0.x`
  are removed in `0.1.0`; run `pytest -W error::DeprecationWarning` before
  upgrading.
- Branch prefixes `feat/ fix/ ci/ docs/ refactor/`; commits follow Conventional
  Commits. Examples live **directly under** `examples/<chapter>/` and use
  docstring directives (`[doc-require: ...]`, `[doc-skip-execute]`,
  `[doc-warning-ignore: ...]`, `[doc-title: ...]`) consumed by the docs build.
