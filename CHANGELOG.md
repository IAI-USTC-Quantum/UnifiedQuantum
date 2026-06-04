# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.15] - 2026-06-04

This release focuses on **native PyTorch parameter integration**, an
**OriginIR-ext superset language**, the project-wide **0.1.0 deprecation
cliff policy**, and **Python 3.14 support**. It also closes the gaps
documented in `RELEASE_REPORT_0.0.15.md`.

Two highlights for users:

- ``Circuit`` now exposes ``param_map`` / ``param_dict`` / ``has_param`` /
  ``set_param_last`` so trainable parameters are first-class — gates with
  ``torch.Tensor`` operands are auto-registered as ``nn.Parameter``\s and
  reachable by name. A new backend-agnostic ``expectation()`` returns a
  differentiable expectation value across simulator backends. See the
  new best-practice example ``examples/3_best_practices/11_native_torch_training.py``.
- ``OriginIR-ext`` is a strict superset of OriginIR that adds gate-list
  primitives (e.g. ``GLIST``) and converts back to standard OriginIR via
  ``uniqc.originir_ext.to_originir``. Useful when you want to author
  larger gate blocks ergonomically but still submit through the official
  OriginIR path.

### Added

- **Native PyTorch parameter integration** (#116):
  - ``Circuit.param_map`` — register tensor-valued parameters explicitly
    or implicitly via ``add_gate`` so trainable circuits work without
    boilerplate.
  - ``Circuit.param_dict`` — name-keyed access to parameters for friendly
    state-dict round-trips.
  - ``Circuit.has_param`` — TorchQuantum-aligned semantics: ``True`` only
    when at least one parameter is a tensor (i.e., actually trainable).
  - ``Circuit.set_param_last`` — convenience setter for the most recently
    added parametric gate, with a proper ``IndexError`` when the circuit
    has no parametric gates yet.
  - Tensor parameters are auto-registered as ``nn.Parameter`` instances
    when passed into ``add_gate`` / convenience gate methods.
  - ``simulator.expectation()`` — backend-agnostic differentiable
    expectation value (statevector / TorchQuantum simulators).
- **OriginIR-ext superset language** (#115): ``uniqc.originir_ext`` with
  ``GLIST`` and other gate-list primitives, plus a strict
  ``to_originir()`` converter that emits official OriginIR.
- **`11_native_torch_training` best-practice example** — end-to-end
  training loop using only native ``Circuit.param_map`` + ``expectation()``.
- **Python 3.14 support**: cp310–cp314 wheels are now built. Core uniqc
  and the ``[simulation]``, ``[visualization]``, ``[pytorch]`` extras
  install cleanly on Python 3.14.
- **Deprecation policy doc** —
  ``docs/source/7_releases/deprecation_policy.md`` formalises the
  **0.0.x → 0.1.0 compatibility cliff**: every API currently emitting
  ``DeprecationWarning`` will be removed or stop being maintained at
  ``0.1.0``. See ``uniqc._deprecation.warn_removed_in_0_1_0`` for the
  central helper.

### Changed

- **All ``DeprecationWarning`` messages now mention the 0.1.0 cliff
  explicitly.** Messages route through the new
  ``uniqc._deprecation.warn_removed_in_0_1_0`` helper and contain the
  literal substring ``"uniqc 0.1.0"`` for machine-grep compatibility.
  Affected sites: ``simulator.get_backend``, ``IBMAdapter``,
  ``QuafuAdapter`` (module-level), task lookup by platform id in
  ``backend_adapter.task_manager``, and the in-place forms of
  ``qft_circuit``, ``deutsch_jozsa_circuit``, ``dicke_state_circuit``,
  ``thermal_state_circuit``, ``cluster_state``, ``ghz_state``,
  ``w_state``, ``amplitude_estimation_circuit``, ``grover_oracle``,
  ``grover_diffusion`` (including its unused ``ancilla`` kwarg),
  ``grover_operator``, ``vqd_circuit``.
- **``Circuit.has_param`` semantics** — aligned with TorchQuantum: returns
  ``True`` only when at least one parameter is a ``torch.Tensor``. Pure
  Python-float parameters now return ``False`` (they are "fixed", not
  "trainable").
- **`[all]` extra no longer pulls in `[quark]`.** ``quarkstudio`` /
  ``quarkcircuit`` have no win32 wheels and their transitive deps
  (``srpc``, ``proxy.py``) currently lack stable cp314 wheels, which
  broke ``uv sync --extra all --upgrade`` on cross-platform resolvers.
  Install the Quark platform path explicitly with ``[quark]`` on
  Linux/macOS + Python 3.12–3.13. ``[all]`` is now the portable,
  broadly-installable superset.
- **`[originq]` extra is gated to `python_version < '3.14'`** until
  ``pyqpanda3`` ships a cp314 wheel. The core package supports cp314 in
  full; the OriginQ platform path requires Python 3.10–3.13. This is a
  packaging-contract change, called out here per the deprecation policy
  (it is not a ``DeprecationWarning``).
- **`requires-python` widened to `>=3.10,<3.15`** and the cp314 trove
  classifier is published.
- **Pre-release SKILL aligned to the real codebase** — corrected
  ``scripts/generate_best_practice_notebooks.py`` → ``scripts/build_docs.py
  --only 3_best_practices``, and the stale ``docs/source/best_practices/``
  / ``docs/source/releases/`` paths → ``docs/source/3_best_practices/``
  / ``docs/source/7_releases/``.

### Fixed

- **`Circuit.set_param_last` on an empty circuit** now raises a proper
  ``IndexError`` instead of silently mis-indexing.
- **24 MyST `Non-consecutive header level increase; H1 to H3` warnings**
  in ``docs/source/0_quickstart/end_to_end.md``,
  ``docs/source/4_cli/walkthrough.md``, and
  ``docs/source/8_algorithms_examples/*.md`` — fixed by adding ``##``
  section wrappers so the auto-generated example ``###`` headings nest
  cleanly under each host page.
- **`test_ibm_backend_summary_uses_cached_per_edge_details_without_chip_cache`**
  no longer relies on the deprecated ``IBMAdapter`` delegate's hidden
  ``_service`` plumbing; refactored to instantiate ``QiskitAdapter``
  directly so the regression is preserved after ``IBMAdapter`` removal
  in 0.1.0.

### Deprecated

- **All currently-deprecated APIs are on track for removal in 0.1.0.**
  See ``docs/source/7_releases/deprecation_policy.md`` for the
  authoritative list and the project's compatibility-cliff wording.
  Notable entries:
  - ``uniqc.simulator.get_backend()`` — use ``get_simulator()`` /
    ``create_simulator()``.
  - ``IBMAdapter`` class — use ``QiskitAdapter``.
  - Entire ``uniqc.backend_adapter.task.adapters.quafu_adapter`` module
    (Quafu platform path; ``[quafu]`` extra was already removed).
  - In-place ``*_circuit(circuit, ...)`` forms of every algorithm builder
    (use the fragment form ``*_circuit(n_qubits, ...) -> Circuit`` with
    ``circuit.add_circuit(fragment)``).
  - ``grover_diffusion(..., ancilla=...)`` keyword argument (unused).
  - Task lookup by platform task id (use the uniqc ``uqt_*`` id).

## [0.0.14] - 2026-05-18

This release brings a major expansion of the variational algorithm toolkit, a
new cross-platform submission options layer, and QASM2 IR decompose for
cross-platform submission. The documentation is reorganised with a dedicated
algorithm examples chapter and new TorchQuantum / matplotlib examples.

### Added

- **`UnifiedOptions` cross-platform submission options** — new `UnifiedOptions`
  dataclass (`uniqc.backend_adapter.task.options`) lets you write
  backend-agnostic submission code. Pass the same instance to `submit_task`
  against any platform and uniqc translates high-level intent (`optimize_level`,
  `error_mitigation`, `auto_mapping`, `shots`, `backend_name`) into each
  platform's specific `BackendOptions` payload. Unsupported options emit
  `UserWarning` (or raise `BackendOptionsError` when `strict=True`).
  `BackendOptionsFactory.normalize_options()` now accepts `UnifiedOptions`
  alongside `BackendOptions`, `dict`, and `None`.
- **Ansatz module expansion** — the `uniqc.algorithms.core.ansatz` package is
  significantly expanded with new variational ansatz families and supporting
  infrastructure:
  - `hva()` — Hardware Variational Ansatz factory for hardware-efficient
    variational circuits with configurable rotation and entangling layers.
  - `hea_param_count()` — utility to compute the parameter count of an HEA
    circuit before building it.
  - **ADAPT-VQE** (`_operator_pool.py`) — adaptive derivative-assembled
    pseudo-trotter VQE with a Pauli operator pool and greedy operator
    selection.
  - **QAOA variants** (`qaoa_ansatz.py`) — expanded QAOA module with support
    for problem-specific mixer Hamiltonians and multi-round schedules.
  - **HEA expansion** (`hea.py`) — hardware-efficient ansatz now supports
    configurable entanglement topologies and rotation gate sets.
  - **Type system** (`_types.py`) — new `EntanglingGate`, `EntanglementTopology`,
    and `RotationGate` enums for type-safe ansatz configuration.
  - **Hardware-aware selection** (`_hardware_aware.py`) —
    `select_ansatz_config()` automatically picks the best topology and
    entangling gate based on hardware connectivity and basis gates.
  - **Pauli unitary** (`_pauli_unitary.py`) — Pauli-string to unitary matrix
    construction for operator pool generation.
  - **Topology utilities** (`_topology.py`) — graph-topology helpers for
    ansatz edge generation.
- **`Parameter` / `Parameters` class** (`uniqc.circuit_builder.parameter`) —
  symbolic parameter management for variational circuits, replacing raw
  float lists with named, indexable parameter containers.
- **QASM2 IR decompose for cross-platform submit** (`uniqc.compile.decompose`) —
  new `decompose_to_qasm2()` function that converts circuits to OpenQASM 2.0
  with gate decomposition suitable for cross-platform submission.
- **Documentation chapter 8: Algorithm examples** — new standalone chapter
  (`docs/source/8_algorithms_examples/`) extracting algorithm implementation
  examples from the advanced chapter for better discoverability.
- **TorchQuantum & matplotlib examples** — new executable examples
  demonstrating `TorchQuantumLayer` integration and matplotlib figure
  generation, with figures switched from PNG to SVG format.

### Fixed

- **ADAPT-VQE `_parse_pauli_string`** — fixed parsing of compact Pauli string
  format (e.g. `"ZIZ"`) and corrected circuit sizing when the qubit count
  differs from the Pauli string length.
- **`build_docs --only` clobbering index.json** — the `--only` flag now
  preserves existing `index.json` entries instead of overwriting them with
  only the selected subset.
- **Windows clock precision** (`cache.py`) — `age_seconds` is now clamped to
  non-negative to prevent negative age values on Windows where clock
  resolution can cause backwards time jumps.

### Changed

- **Documentation structure** — algorithm implementation examples extracted
  from `docs/source/2_advanced/` into a new standalone
  `docs/source/8_algorithms_examples/` chapter covering circuit building
  blocks, core algorithms, variational hybrid methods, state preparation,
  measurement/tomography, and real-hardware workflows.

## [0.0.13] - 2026-05-14

This release unifies the front-door surface of UnifiedQuantum: a single
`--backend` flag on the CLI, a single `Simulator` / `NoisySimulator` for both
OriginIR and OpenQASM, and a single `AnyQuantumCircuit` input type across the
Python API. Qiskit becomes a core dependency, Quafu is archived behind a
deprecation warning, and the documentation site is rebuilt around an
8-chapter, two-step pipeline on the Furo theme.

### ⚠ BREAKING

- **`uniqc submit --platform` removed** — `uniqc submit` no longer accepts
  `--platform` / `-p`. Use a single `--backend <provider>:<chip>` instead
  (e.g. `--backend originq:WK_C180`, `--backend ibm:ibm_fez`,
  `--backend dummy:local:simulator`, `--backend dummy:originq:WK_C180`).
  Omitting `--backend` now defaults to `dummy:local:simulator`. The bare
  string `dummy` is accepted as an alias for `dummy:local:simulator`.
  Note: `uniqc backend list/update`, `uniqc task list`, and `uniqc result`
  still accept `--platform` for cache/scoping operations.
- **`OriginIR_Simulator` and `QASM_Simulator` removed** — both classes are
  replaced by a single `Simulator` (and `NoisySimulator`) in
  `uniqc.simulator` that auto-detects the input format (OriginIR vs
  OpenQASM 2.0) at runtime. Update imports to
  `from uniqc.simulator import Simulator, NoisySimulator`. The
  `program_type=` factory parameter is gone. `originir_simulator.py` and
  `qasm_simulator.py` are deleted.
- **`AnyQuantumCircuit` input type** — public APIs that take a circuit
  (compile, simulate, submit) now accept the new `AnyQuantumCircuit`
  alias (uniqc `Circuit` / OriginIR `str` / OpenQASM 2.0 `str` /
  `qiskit.QuantumCircuit` / `pyqpanda3` circuit) and normalize internally
  via `normalize_to_circuit()`. `NormalizedCircuit.original_format` is
  renamed to `NormalizedCircuit.type`.
- **`[qiskit]` extra removed** — `qiskit`, `qiskit-aer`, and
  `qiskit-ibm-runtime` are now part of the **core dependencies** of
  `unified-quantum`. Users no longer need to install
  `unified-quantum[qiskit]`; a plain `pip install unified-quantum` is
  enough for compile / IBM Quantum / Qiskit-backed paths. If
  `import qiskit` fails after install, the environment is broken —
  reinstall with `pip install --upgrade unified-quantum`.
- **`[quafu]` extra removed; Quafu support archived** — the Quafu adapter
  code is retained for backwards compatibility but is now **deprecated**
  and emits a `DeprecationWarning` at import time. The `[quafu]` extra is
  no longer available. Users who still need Quafu must install `pyquafu`
  directly with `pip install pyquafu` and accept that it requires
  `numpy<2`. Future releases do not guarantee consistency or completeness
  of Quafu-related code, and support may stop at any time.
- **`submit_task` rejects bare `dummy:`-less platform strings** —
  `submit_task` now enforces a `provider:chip-name` format on `backend=`.
  Bare `"originq"` / `"ibm"` strings raise; pass `originq:WK_C180`,
  `ibm:ibm_fez`, or a `dummy:...` rule string instead. `auto_compile` is
  fixed to actually run when no `compile_options` are provided.

### Added

- **`uniqc doctor` CLI** — environment diagnostics command (
  `uv run uniqc doctor`) that checks Python version, optional dependency
  groups, configured tokens, cached backends, and known broken-import
  shims. Use this as the first step when triaging install / config
  issues.
- **Parallel-CZ XEB calibration module** — new
  `uniqc.calibration.xeb.parallel_cz` module and a strict pre-flight
  policy (the calibration entry-points refuse to dispatch experiments
  whose chip-level prerequisites are not satisfied, instead of failing
  silently downstream). Exposed through `uniqc calibrate xeb`.
- **`uniqc.get_platform_task_ids` / `uniqc task shards` continued** —
  schema and CLI introduced in `v0.0.12` are kept; the new
  `Simulator`/`AnyQuantumCircuit` paths and the v0.0.13 batch-result
  flatten fix all preserve the `uqt_*` indirection layer.
- **Top-level result helpers** — `uniqc.get_result` and
  `uniqc.poll_result` (in addition to the existing `wait_for_result`)
  are now re-exported from the `uniqc` namespace, mirroring the new
  async-result API.
- **`Circuit.to_qiskit_circuit()` / `Circuit.to_pyqpanda3_circuit()`** —
  first-class converters from uniqc `Circuit` to other in-process
  circuit types, plus assorted previously-missing gates wired into
  the unified normalize path.
- **Fake-backend tests** — new fake-backend test fixtures broaden CLI /
  adapter coverage without requiring real cloud credentials.
- **Chip-cache refresh paths for IBM / Quafu / Quark** —
  `uniqc backend update --platform ibm|quafu|quark` now actually
  refreshes the on-disk chip cache via each adapter's
  `get_chip_characterization` (previously raised "Cache refresh not
  implemented for provider …").
- **Doc-site auxiliary scripts and prose** — `uniqc-build-docs` skill
  for local Sphinx builds; deep-prose pages for `simulation.md`,
  `submit_task.md`, `compiler_options_region.md`,
  `platform_conventions.md`, `installation.md`, `best_practices.md`,
  and the four section-index pages.

### Changed

- **CLI overhaul** — `_dummy_backend_id()` is renamed to
  `_normalize_backend_id()` with unified logic for dummy + real
  backends; `_submit_single`, `_submit_batch`, and `_handle_dry_run`
  are simplified accordingly. All `--ai-hints` / `--ai-hint` text in
  `uniqc.cli.refs` uses the new `--backend` syntax. `uniqc task list`
  threads `--limit` / `--offset` through to the SQLite store, and
  `uniqc task clear` uses `store.count()` instead of fully
  materialising the cache (matters once you have hundreds of cached
  tasks).
- **API error messages** — every public-facing error / warning is now
  enriched with a doc link and a troubleshooting hint pointing at a
  specific API page (instead of the doc-site root). Affects
  `MissingDependencyError`, `TopologyError`, `UnsupportedGateError`,
  and the cloud-platform adapters.
- **Quafu / IBM bitstring convention** — both adapters now enforce the
  `c[0] = LSB` bitstring convention end-to-end so per-bit indexing
  matches OriginQ, the dummy backend, and the simulator.
- **Documentation structure** — site moved from a 6-area layout to an
  8 chapter-numbered structure under `docs/source/<N>_<chapter>/`,
  with examples reorganised under `examples/<N>_<chapter>/`. The build
  is now a two-step pipeline (`pre-doc-execution` runs every example
  end-to-end, then `sphinx-build` produces HTML), and the theme is
  switched to Furo. `make html` is the canonical entry point.
- **Quafu visibility on the doc site** — the public site / front-end
  surfaces only `originq` / `ibm` / `quark` / `dummy` and hides Quafu;
  the `uniqc submit` / `compile_for_backend` paths still work for
  Quafu, but it is no longer a recommended option.
- Updated docstrings, error messages, troubleshooting hints, README
  tables and installation / task_manager / submit_task / best_practices
  / platform_conventions / compiler_options_region docs to remove
  `pip install unified-quantum[qiskit]` and
  `pip install unified-quantum[quafu]` references and replace them
  with the appropriate guidance (qiskit is core; quafu is archived /
  install pyquafu manually).
- `uniqc.backend_adapter.task.optional_deps.require()` now accepts an
  optional `install_hint` and special-cases the legacy `extra="quafu"`
  argument so that callers automatically get the deprecation /
  `pip install pyquafu` message.
- `MissingDependencyError` raised from the Quafu adapter /
  cloud-platform SDK paths now points at `pip install pyquafu` instead
  of a non-existent extra.

### Fixed

- **IBM backend discovery silently broken** —
  `_build_adapter(Platform.IBM)` returned a bare `QiskitAdapter`,
  whose inherited `list_backends` raised `NotImplementedError`; the
  generic `except Exception` in `fetch_platform_backends` swallowed
  it and `uniqc backend update --platform ibm` reported success while
  the cache stayed days stale. `list_backends` and
  `get_chip_characterization` are moved onto `QiskitAdapter` (the
  canonical IBM adapter today); the deprecation-shim `IBMAdapter`
  delegates to it.
- **Qiskit `query_batch` produced nested results** — when a single
  Sampler job covered multiple PUBs (IBM's native batch),
  `QiskitAdapter.query_batch` returned `list[list[dict]]` instead of a
  flat `list[dict]`, breaking `pytest --real-cloud-test`. Mirror the
  OriginQ adapter pattern: extend if the per-job payload is a list,
  append if it is a dict.
- **`dummy:originq:WK_C180` skipped basis-gate compile** —
  `_compile_for_chip_backed_dummy` returned the source IR verbatim
  whenever active qubits were inside the chip's `available_qubits`,
  so a Bell circuit reached the simulator as raw H + CNOT and raised
  `TopologyError("Unsupported topology")`. Drop the unconditional
  early-return and rely on the `available_qubits`-based coupling-map
  filter already in `compile_with_config`.
- **`uniqc submit ... --wait` table empty** —
  `extract_counts_and_probs` only handled raw `dict` / `list` payloads
  but `wait_for_result` returns a `UnifiedResult` (single circuit) or
  `list[UnifiedResult]` (native batch). The helper now unwraps both,
  with regression tests.
- **`uniqc submit ... --backend originq:WK_C180 --dry-run`** —
  previously raised
  `OriginQCircuitAdapter object has no attribute dry_run` because the
  non-dummy dry-run path resolved a translation-only `CircuitAdapter`.
  Resolve through `backend_module.get_backend(backend).adapter` so
  `dry_run` is available on every supported provider.
- **`fetch_platform_backends` clobbered cache on silent SDK failure** —
  when an SDK call returned 0 backends (e.g. IBM credentials missing
  / wrong instance), the previous code persisted a fresh empty list
  on top of an existing cache and reported success. Keep the existing
  cache and report `fetched_newly=False` so
  `/api/backends/refresh` surfaces a warning.
- **`NoisySimulator` MRO bypassed noise injection** — the previous
  multiple-inheritance order silently dropped the noise-injection
  hooks on some `NoisySimulator` paths.
- **`UnifiedResult` JSON serialisation** — `uniqc submit ... --json`
  now correctly serialises `UnifiedResult` payloads instead of falling
  through to the default repr.
- **MPS form flattening on the CLI** — bare `dummy` is rejected,
  `dummy:mps:linear-N` parses cleanly, and the form-string layout
  matches the documented one in `submit_task.md`.
- **OriginQ failure-message propagation** (carried through from
  `v0.0.12`) — error strings nested under `result["result"]["error"]`
  are now surfaced on `TaskInfo.error_message` and
  `TaskShard.error_message` for both single tasks and batches.
- **Doc commands using `--platform`** — 8 user-facing doc commands
  across `0_quickstart/end_to_end.md`, `4_cli/{workflow,walkthrough,
  backend}.md`, `docs/index.md`, `examples/3_best_practices/...` and
  `examples/4_cli/cli_example/...` were rewritten to the canonical
  `--backend <provider>:<chip>` / `--backend dummy:local:...` form.
- Test-suite pinning: `least_qubit_remapping=False` restored on
  `test_random_QASM` and `test_benchmark` so QASM benchmarks compare
  apples-to-apples; bitstring-endianness test on `dummy:originq` now
  gates on OriginQ credentials so it doesn't fail in the open-source
  CI lane.
- `pybind11-stubgen` added to `[dependency-groups].dev` so
  `scripts/stubgen.py` works from a fresh dev install.

### Migration notes

- **CLI**: replace every `uniqc submit ... --platform <p> [--backend <b>]`
  invocation with `uniqc submit ... --backend <provider>:<chip>` (or
  `--backend dummy:local:simulator`). Other `--platform` flags
  (`uniqc backend update --platform`, `uniqc task list --platform`,
  `uniqc result --platform`) are unchanged.
- **Python API**: replace `from uniqc.simulator import OriginIR_Simulator,
  QASM_Simulator` with `from uniqc.simulator import Simulator,
  NoisySimulator`, drop `program_type=`, and pass any
  `AnyQuantumCircuit` value directly.
- **Install**: drop `[qiskit]` and `[quafu]` from `pip install
  unified-quantum[...]`; if you previously relied on the `[quafu]`
  extra, run `pip install pyquafu` separately and pin `numpy<2`.
- **Submit**: callers that built `submit_task(backend="originq", ...)`
  must now spell the chip explicitly:
  `submit_task(backend="originq:WK_C180", ...)`. Use
  `uniqc backend list --platform originq` to find available chips.

## [0.0.12] - 2026-05-07

### ⚠ BREAKING

- **uniqc-managed task IDs (`uqt_*`)** — `submit_task` / `submit_batch` now
  always return a single opaque uniqc task id of the form
  `uqt_<32-hex>` (36 chars total) rather than the underlying platform's
  raw id. Internally the new `task_shards` table maps each `uqt_*` to
  one or more platform-issued ids and tracks per-shard status. Migration
  is automatic — pre-existing rows in the local sqlite cache are
  upgraded to the new layout on first use (each old row becomes its own
  `uqt_*` parent + 1 shard, with the original platform id preserved
  under `metadata.legacy_platform_id`). Querying with a raw platform
  id still works but emits a `DeprecationWarning` and resolves via the
  shard index.

  Why: the previous behaviour leaked platform-specific id formats
  (OriginQ MD5, IBM `cp...` job ids, Quafu UUIDs, dummy `0xabc...`)
  through every downstream tool; uniqc now exposes one consistent
  format. It also enables transparent **auto-sharding**: when a batch
  exceeds an adapter's `max_native_batch_size` (OriginQ default 200 via
  `originq.task_group_size`, IBM 100), uniqc splits it into multiple
  cloud submissions, each tracked as a separate shard, while the user
  still sees one task id.

  Impact: any caller that compared returned task ids against a regex
  for the old platform format, or that persisted platform ids into its
  own database, must update to use `uqt_*` ids. To recover the
  underlying platform ids, call `uniqc.get_platform_task_ids(uid)` (also
  exposed via `uniqc task shards <uid>` and
  `GET /api/tasks/{uid}/shards`).

### Added

- `uniqc.get_platform_task_ids(task_id) -> list[TaskShard]` — public API
  for inspecting the shard mapping behind a `uqt_*` id. Each shard
  exposes `platform_task_id`, `shard_index`, `circuit_count`,
  `sub_index_offset`, `status`, `error_message`, `submit_time` and
  `update_time`.
- `uniqc task shards <uid>` CLI subcommand (`--format table|json`).
- `GET /api/tasks/{uniqc_id}/shards` REST endpoint on the gateway.
- `submit_batch(..., return_platform_ids=True)` opt-in that returns the
  list of platform ids in submission order (for callers that want both
  the uniqc id and the per-circuit platform ids; the uniqc id is still
  the canonical handle for `query_task` / `wait_for_result`).
- `QuantumAdapter.max_native_batch_size` class attribute (default 1).
  OriginQ exposes it as a property reading
  `originq.task_group_size` (default 200); qiskit hard-codes 100.
- Schema v4 (`task_shards` + `archived_task_shards` tables with FK
  `ON DELETE CASCADE`) and v5 (legacy-row migration). Schema version is
  bumped from 2 → 5; the gateway `ArchiveStore.archive_task` /
  `restore_task` / `delete_archived` paths now cascade shard rows
  alongside the parent.

### Fixed

- Cloud failure messages from OriginQ are now propagated to
  `TaskInfo.error_message` (and `TaskShard.error_message`). Previously
  the adapter nested the error under `result["result"]["error"]`, but
  `query_task` and friends only inspected `result.get("error")`,
  silently leaving `error_message=None` on every failed task.
- Pre-existing bug in `gateway.db.archive_store.ArchiveStore.restore_task`
  that iterated a sqlite3 `Row` as values instead of keys (made
  archive→restore round-trip raise `IndexError`).

### Added

- **Native batch submission for OriginQ and IBM** (`uniqc/backend_adapter/task/adapters/originq_adapter.py`, `qiskit_adapter.py`, `uniqc/backend_adapter/task_manager.py`, `uniqc/backend_adapter/backend.py`):
  `submit_batch(circuits, ..., native_batch=True)` (default) now packs all
  circuits into a single cloud job — one queue position, one task ID per
  batch — by routing through pyqpanda3's
  `QCloudBackend.run(list[QProg], shots, options)` overload for OriginQ
  and through qiskit-runtime's native `Sampler.run([circuits])` for IBM.
  `wait_for_result(batch_id)` returns a `list[UnifiedResult]` for native
  batches, with each child `task_id` formatted as `"{batch_id}#{idx}"`
  (preserves submission order). Pass `native_batch=False` to fall back to
  one cloud job per circuit (legacy behaviour). Live-verified on WK_C180
  for batches of 3 circuits, and end-to-end through `wait_for_result`.
  This dramatically reduces queueing time for high-throughput workflows
  like XEB and noise characterization.

## [0.0.11.post1] - 2026-05-07

### Fixed

- **Chip-backed dummy `local_compile=0` honoured + `available_qubits` enforced** (`uniqc/backend_adapter/task_manager.py`, `uniqc/compile/compiler.py`):
  Previously `dummy:originq:WK_C180` and other chip-backed dummies always
  ran the qiskit layout pass inside `_compile_for_chip_backed_dummy`,
  silently re-mapping the user's hand-picked safe qubits onto whatever
  physical qubits `RegionSelector` chose — including chip qubits the
  caller had explicitly excluded via `available_qubits` (e.g. q[58]/q[68]
  silently moved onto the broken q[13]/q[21]). Three coupled fixes:
  (1) `_compile_for_chip_backed_dummy(...)` now honours `local_compile=0`
      and passes the source IR through verbatim;
  (2) when `available_qubits` is forwarded (or recovered from the dummy
      spec) and the source circuit's actively-touched qubits already lie
      inside that allow-list, the IR is also passed through verbatim
      regardless of `local_compile` — the user has chosen the layout and
      we MUST NOT silently relabel;
  (3) `compile()` / `compile_with_config()` / `compile_full()` /
      `_route_with_fidelity()` now accept `available_qubits` and filter
      both the coupling map and per-qubit/edge fidelity tables before
      mapping selection, so any genuine relayout cannot land on excluded
      qubits.
  `submit_task` / `_submit_dummy` / `submit_batch` / `_submit_batch_dummy`
  thread `local_compile` and `available_qubits` end-to-end. Regression
  tests added in `uniqc/test/cloud/test_dummy_backend_design.py`.

## [0.0.11] - 2026-05-07

This is a large release driven by a four-round end-to-end audit of every public
API and its documentation. Beyond the new MPS simulator, the headline change is
a sweeping cleanup of variational / state-prep / oracular / measurement
algorithms into a single "circuit fragment" design, plus a unified
exception system, a new compile-level model that replaces ad-hoc
`auto_compile` flags, and substantial cloud-platform reliability fixes.

### Added

#### Simulation

- **MPS simulator** (`uniqc/simulator/mps_simulator.py`): New pure-Python `MPSSimulator` and `MPSConfig` classes implementing an open-boundary, nearest-neighbour matrix-product-state engine with χ-bounded SVD truncation. Supports the OriginIR gate set used by the rest of `uniqc` (`H/X/Y/Z/S/T/SX/RX/RY/RZ/U1/U2/U3/RPhi*` 1q, `CNOT/CZ/SWAP/ISWAP/ECR` 2q, `XX/YY/ZZ/XY/PHASE2Q` parameterised 2q). Public API: `simulate_pmeasure` (≤24 measured qubits), `simulate_shots` (per-site MPS sampling, scales to hundreds of qubits), `simulate_statevector` (≤24 qubits). Exposes `max_bond` and `truncation_errors` for diagnostics. Rejects long-range 2-qubit gates and `CONTROL`/`controlled_by` operations. Does NOT inherit `BaseSimulator`, keeping the C++ runtime out of its dependency closure.
- **`dummy:local:mps-linear-N` backend** (`uniqc/backend_adapter/dummy_backend.py`, `dummy_adapter.py`): Resolver now recognises identifiers of the form `dummy:local:mps-linear-<N>[:chi=<int>][:cutoff=<float>][:seed=<int>]`, which build a noiseless `MPSSimulator` over an open-chain topology. `DummyBackendSpec` gains `simulator_kind` and `simulator_kwargs`; `DummyAdapter` validates that MPS is not combined with `noise_model`/`chip_characterization`, dispatches `simulate_shots` directly, and short-circuits the C++ availability check when `simulator_kind == "mps"`.

#### Circuit & Compiler

- **`Circuit.get_matrix()`** (`uniqc/circuit_builder/matrix.py`): Extracts the unitary matrix representation of a `Circuit` by folding all gate matrices via tensor product and contraction. Supports all standard gates; raises `NotMatrixableError` for gates without a finite unitary (measurement, decoherence channels). Exposed at the top level (A-U2).
- **`Circuit.draw()`** (`uniqc/circuit_builder/qcircuit.py`): Convenience visualisation helper alongside the existing timeline view (A-U6).
- **`Circuit.xy(q1, q2, theta)`** parameterised 2q gate.
- **OpenQASM 2 user `gate def` support** (`uniqc/qasm/qasm2parser.py`): The base parser now recognises user-defined `gate` blocks, recursively inlines custom gate calls during parsing, and supports parameterised, parameter-less, nested, and overriding definitions. Round-trip export of `iswap`, `rphi`, `phase2q`, `xy`, `uu15` etc. into QASM2 now works via auto-generated `gate def` blocks (A-U3).
- **Compile-level model** (`uniqc/backend_adapter/task/options.py`, `docs/source/guide/compile_levels.md`): Replaces `auto_compile=True/False` with explicit `local_compile` / `cloud_compile` integers (0..3, mirroring the qiskit transpilation level convention). IR-language compatibility is always hard-enforced, separately from the soft `skip_validation` flag (NEW-U2).

#### Algorithms (refactor — see "Changed" for breaking notes)

- **Algorithm fragment design** (`uniqc/algorithms/`, `docs/source/guide/algorithm_design.md`): Variational ansatz factories use the `_ansatz` suffix and return a fresh `Circuit`; state-prep primitives use the `_circuit` suffix and accept `n_qubits`/`qubits`; oracular algorithms accept a `Circuit` (the oracle) as their first argument; measurement primitives become classes (`PauliExpectation`, `StateTomography`, `ClassicalShadow`, `BasisRotationMeasurement`) with `.get_readout_circuits()` and `.execute(backend, *, program_type='qasm', **kwargs)`. Each module also exports a `<name>_example()` helper for docs and smoke tests (C-U1).
- **`vqd_ansatz`** introduced (`vqd_circuit` retained as deprecated alias).
- **`qpe_circuit`** (`uniqc/algorithms/core/circuits/qpe.py`): Textbook Quantum Phase Estimation fragment with inverse-QFT, exposed at `uniqc.algorithms.core.circuits` (C-U9).
- **VQE / QAOA / classical-shadow workflows** (`uniqc/algorithms/workflows/`): End-to-end driver helpers for the most common variational and shadow-tomography pipelines (C-U6).
- **`pauli_expectation` accepts three forms**: compact `'ZIZ'`, indexed `'Z0Z1'`, and tuple list `[('Z',0),('Z',1)]` (C-U2).

#### Calibration & QEM

- **Calibration module** (`uniqc/calibration/`): Top-level module with `XEBenchmarker`, `ReadoutCalibrator`, and `~/.uniqc/calibration_cache/` storage with ISO-8601 `calibrated_at` timestamps. `CalibrationResult` / `XEBResult` / `ReadoutCalibrationResult` dataclasses with `to_dict()` / `from_dict()` for JSON serialisation. Architecture: calibration writes cache; QEM reads and enforces TTL freshness.
- **`ReadoutCalibrator.calibrate_1q/2q`** now return `ReadoutCalibrationResult` dataclasses (with backward-compatible `__getitem__`/`__contains__`) instead of bare dicts (E2). Now accept `timeout` / `poll_interval` kwargs (E-U7).
- **M3Mitigator / ReadoutEM `.apply(UnifiedResult)`** pipeline API for clean end-to-end mitigation (E-U5).
- **ZNE placeholder** (`uniqc/qem/zne.py`): `NotImplementedError` + `TODO` for follow-up release (E-U4).

#### Cloud & Backend

- **`RegionSelector.from_backend`** convenience constructor (D-U9).
- **`RegionSelector` time budget + greedy fallback**: `find_best_1D_chain` accepts `max_search_seconds` (default 30s) with deadline checks; on timeout returns the best partial result found (D-U2, D6).
- **`UnifiedResult` dict-like**: exposes counts via `__getitem__` / `values` / `keys` and a `.raw()` accessor (D1).
- **`TaskInfo.error_message`** field (D-U10) and **`DryRunResult.error_kind`** (D-U13).
- **Backend audit visibility**: `fetch_all_backends_with_status()` returns `FetchResult(backends, fetch_failures)`. `audit_backends()` accepts `fetch_failures` and emits `BackendAuditIssue(severity="warning")` for platforms that had credentials but couldn't be fetched (D11).
- **Top-level export of `XEBenchmarker`** from both `uniqc.calibration` and `uniqc.calibration.xeb` (E-U3).
- **`F-U3`**: new `docs/source/cli/gateway.md`.

#### Exception system

- **`uniqc/exceptions.py`**: Consolidated 18+ custom exception classes scattered across 8 files into a single hierarchy rooted at `UnifiedQuantumError`. New: `ConfigError` family, `CompilationFailedError`, `CircuitTranslationError`, QASM parser errors, `TopologyError`, `NotMatrixableError`, `TimelineDurationError`, `BackendOptionsError`, `MissingDependencyError` (#76).

### Changed

- **`uniqc.simulator.get_backend` → `get_simulator`** (`get_backend` retained as deprecated wrapper). Signature unified across `get_simulator` / `create_simulator` to `(backend_type, program_type)` (B-U2, B2).
- **`uniqc.simulator.__init__`** rewritten to re-export `OpcodeSimulator`, `backend_alias`, and all `error_model` classes; cleaned `__all__`; removed `TYPE_CHECKING` leak (B-U1, B-U3, B-U4).
- **`list_backends()`** returns `list[str]`; the dict-by-platform variant is `list_backends_by_platform()` (D8).
- **`auto_compile` removed**; replaced by `local_compile` / `cloud_compile` integers (NEW-U2).
- **`UNIQC_DUMMY` and `UNIQC_SKIP_VALIDATION` env vars removed**: dummy mode is now selected exclusively via the backend prefix (`dummy:...`), and skip-validation via the `skip_validation=True` kwarg (D2, D3).
- **Hard IR-language compatibility check**: language compatibility (e.g. RPhi gates rejected by QASM2-only platforms) is enforced regardless of `skip_validation`. Gate-set, qubit-count, and topology checks remain skippable (NEW-U2).
- **`OriginQAdapter.translate_circuit`** transparently rewrites `SX` / `SX.dagger` to `RX(±π/2)` so OriginQ/`pyqpanda3` accepts circuits originally written in the SX basis (NEW-U2.b).
- **OriginQ backend default** changed from `origin:wuyuan:d5` → `originq:WK_C180` everywhere (CLI, defaults, docs) (D-U5/NEW-U5, D9, D10).
- **`_get_adapter` accepts `<platform>:<chip>` suffix** with helpful errors otherwise (NEW-U2). `dry_run_task` now uses the same resolver and matches `submit_task` API surface (D-U4).
- **Case-insensitive backend aliases** (D-U3).
- **Density-matrix CLI alias** (`density_matrix` → `density_operator_qutip`) normalisation + help text (B-U6).
- **`Platform.IBM` defaults to `QiskitAdapter`** (`IBMAdapter` is deprecated) (NEW-U7).
- **`wait_for_result`** drops the now-unused `backend` keyword — task ID alone is sufficient (D-U11).
- **`state_tomography`** drops the qutip dependency and returns a plain dict (C-U4).
- **Config validation** warns on unknown platform keys to surface typos (e.g. `tokn` instead of `token`) (F9).
- **Backend platform fetch** distinguishes "no credentials" (silent skip) from "credentials present but fetch failed" (raises `BackendError` with original cause) (D11).
- **`save_calibration_result`** writes ISO-8601 with trailing `Z` instead of `+0000` (E-U1).
- **`always-ai-hints`** alias of `always-ai-hint` is hidden in CLI help (F-U2).
- **`batch_execute_with_params`** now in `torch_adapter.batch_executor.__all__` (F-U5).
- **Documentation overhaul**: All guides, CLI pages, and API references aligned with the post-audit surface; `algorithmics.*` references replaced with `uniqc.algorithms.core.*` (C-U8); guide examples use `UnifiedResult` attribute access (`.counts`/`.probabilities`) (D-U1); MPS chi_max default corrected to 64; QuantumLayer constructor + VQE optimizer example fixed (B5-B7, F6-F8). New `docs/source/api_index.md` API landing page; `uniqc_api.rst` now points at the autoapi-generated tree (B-U5).

### Fixed

- **`algorithms.dicke_state` / `w_state`**: produce correct W superposition (C1, C2).
- **`algorithms.state_tomography`**: fix qutip-fallback dtype, identity element, and Hermitian symmetrisation (C3).
- **`qem/m3`**: `M3Mitigator` accepts `ReadoutCalibrationResult` and runs freshness check on the calibration_result branch (E1, E5).
- **`qem/readout_em`**: parse bitstrings as binary in the ≥3-qubit path (E3).
- **`backend_adapter/region_selector`**: skip self-loops in graph build (D7).
- **`backend_adapter/task/options`**: `from_kwargs` accepts both dict and `**kwargs`; default `backend_name` updated to `originq:WK_C180`.
- **`task_manager.wait_for_result`** returns `UnifiedResult | None`; `clear_completed_tasks` accepts a status filter (D1, F1).
- **Compile pipeline** correctly tracks MEASURE gates with non-contiguous qubit/classical bit registers via a deferred `pending_measurements` buffer.
- **Exception classes** in `compile/_utils`, `qem/m3`, `task/options` now inherit from `UnifiedQuantumError` + the original parent for cross-catch compatibility (F5).
- **CLI `task clear --status X`** actually filters by status (F1).
- **Routing fix** (NEW-U1): routing now uses qiskit `initial_layout` (no OriginIR rewrite); fetches the full chip topology, picks the highest-fidelity edge for 2q jobs and a 1D-chain for >2q jobs.
- **Backend aggregator** no longer silently drops platforms; `ImportError` and unexpected errors surface as `fetch_failures` (NEW-U4).
- **TaskInfo + duplicate-measure ban**: circuits with duplicate `MEASURE` on the same qubit are rejected with a clear error (D-U10).
- **`basis_rotation_measurement`** raises `ValueError` if the input circuit has no `MEASURE` (C-U5).
- **QiskitAdapter proxy detection** (`uniqc/backend_adapter/task/adapters/qiskit_adapter.py`): Auto-detects system proxy settings when no proxy is configured in the IBM section, enabling IBM Quantum access through corporate proxies.

### Testing

Full test matrix on this release: **1456 passed, 16 skipped** (`pytest -q` against `pyproject` `[all]` extras). Tests added across `test_mps_simulator.py`, `test_calibration_*`, `test_quark_adapter.py`, algorithm-fragment regression tests, and `test_compile_levels.py`.

### Migration notes

- Replace `from uniqc.algorithmics import ...` with `from uniqc.algorithms.core import ...`.
- Replace `auto_compile=True/False` with `local_compile=<int>` and/or `cloud_compile=<int>` (see `docs/source/guide/compile_levels.md`).
- Replace `submit_task(..., backend='origin:wuyuan:d5')` with `submit_task(..., backend='originq:WK_C180')`.
- `wait_for_result(task_id, backend='originq')` → `wait_for_result(task_id)`.
- `simulator.get_backend(...)` → `simulator.get_simulator(backend_type, program_type)`.
- `os.environ['UNIQC_DUMMY']` / `UNIQC_SKIP_VALIDATION` → use `backend='dummy:...'` / `skip_validation=True` kwarg.
- `vqd_circuit(...)` → `vqd_ansatz(...)` (old name still works with `DeprecationWarning`).

## [0.0.10] - 2026-05-05

### Added

- **Release automation skills** (`.claude/skills/`): New `uniqc-release` skill for automated release workflow (CHANGELOG update, release branch, PR, post-merge tag + PyPI publish), and updated `uniqc-test-before-release` skill with C++ stubgen step.

### Changed

- **QiskitAdapter proxy detection** (`uniqc/backend_adapter/task/adapters/qiskit_adapter.py`): Now automatically detects and uses system proxy settings when no proxy is explicitly configured in the IBM config section, enabling IBM Quantum access through corporate proxies without manual configuration.
- **Quark IPython dependency** (`pyproject.toml`): Added `ipython` dependency to quark extras.
- **Wheel CI pybind11** (`.github/workflows/python_build_wheel.yml`): Updated to use PyPI pybind11 instead of git submodule.

## [0.0.9] - 2026-05-04

### Added

- **`Circuit.get_matrix()`** (`uniqc/circuit_builder/matrix.py`): Extracts the unitary matrix representation of a `Circuit` by folding all gate matrices via tensor product and contraction. Supports all standard gates (`H`, `X`, `Y`, `Z`, `S`, `T`, `SX`, `RX`, `RY`, `RZ`, `CNOT`, `CZ`, `CPHASE`, `SWAP`, controlled variants). Raises `NotMatrixableError` for gates without a finite unitary (e.g. measurement, decoherence channels).
- **Measurement probability checks** (`uniqc/compile/compiler.py`): `_originir_to_circuit()` now correctly tracks MEASURE gates with non-contiguous qubit and classical bit registers via a deferred `pending_measurements` buffer, fixing circuits where qubits map to non-zero classical bits.
- **Calibration module** (`uniqc/calibration/`): New top-level module for chip calibration experiments. All results are saved to `~/.uniqc/calibration_cache/` with ISO-8601 `calibrated_at` timestamps. Architecture: calibration writes cache; QEM reads and enforces TTL freshness. Future PEC/ZNE follow the same split.
- **`uniqc.calibration.results`** (`calibration/results.py`): `CalibrationResult`, `XEBResult`, `ReadoutCalibrationResult` dataclasses with `to_dict()`/`from_dict()` for JSON serialization. `save_calibration_result()`, `load_calibration_result()`, `find_cached_results()` for cache I/O. File naming: `{type}_{backend}_{identifier}_{timestamp}.json`.
- **`uniqc.calibration.xeb.circuits`** (`calibration/xeb/circuits.py`): Random XEB circuit generators. `generate_1q_xeb_circuits()` creates single-qubit random circuits (H, X, Y, Z, S, T, RX, RY, RZ). `generate_2q_xeb_circuit()` and `generate_parallel_2q_xeb_circuits()` for two-qubit and parallel execution. Seeded RNG via `np.random.default_rng(seed)` for reproducibility.
- **`uniqc.calibration.xeb.fitter`** (`calibration/xeb/fitter.py`): `compute_hellinger_fidelity()` (Sørensen-Dice overlap: F = (Σ√(p_i·q_i))²) and `fit_exponential()` which fits F(m) = A·r^m + B via `scipy.optimize.curve_fit` with numpy log-scale fallback. Returns `{r, A, B, r_stderr, method}`.
- **`uniqc.calibration.xeb.benchmarker`** (`calibration/xeb/benchmarker.py`): `XEBenchmarker` class integrating circuit execution, optional `ReadoutEM` application, Hellinger fidelity computation, and exponential fitting. `run_1q()`, `run_2q()`, `run_parallel_2q()` → `XEBResult`. All results saved to calibration cache.
- **`uniqc.calibration.xeb.patterns`** (`calibration/xeb/patterns.py`): `ParallelPatternGenerator` using DSatur (saturation-degree greedy) graph coloring to find the minimum parallel schedule for 2-qubit gates. `auto_generate(topology)` partitions chip edges into rounds; `from_circuit(originir)` extracts parallel pattern from compiled circuit. Supports all 2-qubit OriginIR gates (CNOT, CZ, ECR, SWAP, ISWAP, XX, YY, ZZ, XY).
- **`uniqc.calibration.readout`** (`calibration/readout/calibrator.py`): `ReadoutCalibrator` for 1-qubit (2 circuits: |0⟩,|1⟩) and 2-qubit (4 circuits: |00⟩,|01⟩,|10⟩,|11⟩) readout error characterization. Builds 2×2 or 4×4 confusion matrices and saves to cache.
- **`uniqc.qem`** (`uniqc/qem/`): New quantum error mitigation module. **Calibration module writes cache; QEM module reads and enforces TTL.** Split enables future PEC and ZNE to follow the same architecture.
- **`uniqc.qem.m3`** (`uniqc/qem/m3.py`): `M3Mitigator` and `StaleCalibrationError`. Applies confusion matrix linear inversion (`p_corrected = C⁻¹ · p_obs`, renormalized). `_load_calibration()` parses `calibrated_at` timestamp and raises `StaleCalibrationError` if data exceeds `max_age_hours`. Supports both direct `ReadoutCalibrationResult` injection and cache-file loading.
- **`uniqc.qem.readout_em`** (`uniqc/qem/readout_em.py`): `ReadoutEM` — unified readout error mitigation interface. Automatically calls 1q/2q calibrator as needed. `mitigate_counts(counts, measured_qubits)` dispatches to `_mitigate_1q`, `_mitigate_2q`, or `_mitigate_nq` (tensor-product approximation for n>2 qubits). Internally caches `M3Mitigator` instances.
- **`uniqc.algorithms.workflows`** (`uniqc/algorithms/workflows/`): New module for chip-agnostic high-level workflows. All algorithms work with any supported `QuantumAdapter`. WK180-specific code lives in `examples/wk180/`.
- **`uniqc.algorithms.workflows.xeb_workflow`** (`uniqc/algorithms/workflows/xeb_workflow.py`): `run_1q_xeb_workflow()`, `run_2q_xeb_workflow()`, `run_parallel_xeb_workflow()`. Combines `ReadoutCalibrator` → `ReadoutEM` → `XEBenchmarker` → exponential fit. Reads entangler gate fidelity from `ChipCharacterization.two_qubit_data`.
- **`uniqc.algorithms.workflows.readout_em_workflow`** (`uniqc/algorithms/workflows/readout_em_workflow.py`): `run_readout_em_workflow()` calibrates readout and returns a ready-to-use `ReadoutEM` instance. `apply_readout_em()` applies EM to a `UnifiedResult`.
- **`examples/wk180/`**: `xeb.py` and `readout_em.py` demonstrating WK180 (OriginQ) chip integration. Generic workflows should use explicit backend ids such as `dummy:originq:WK_C180` for local noisy simulation or `originq:WK_C180` for hardware execution; legacy `dummy=True` paths remain compatibility helpers only.
- **`uniqc calibrate` CLI** (`uniqc/cli/calibrate.py`): Three subcommands — `uniqc calibrate xeb` (1q/2q XEB), `uniqc calibrate readout` (1q/2q readout calibration), `uniqc calibrate pattern` (parallel execution pattern analysis). All integrate with `uniqc.algorithms.workflows` and the calibration cache.
- **Top-level exports** (`uniqc/__init__.py`): `calibration`, `XEBResult`, `ReadoutCalibrationResult`, `save_calibration_result`, `load_calibration_result`, `find_cached_results`, `qem`, `M3Mitigator`, `StaleCalibrationError`, `ReadoutEM`, `algorithms`.
- **Calibration test suite** (`uniqc/test/calibration/`): 43 tests covering XEB circuits, exponential fitter, parallel patterns (DSatur), readout calibrator, unified `ReadoutEM` dispatch, and `M3Mitigator` with TTL enforcement.
- **Canonical dummy backend identifiers** (`uniqc/backend_adapter/dummy_backend.py`, `uniqc/backend_adapter/task_manager.py`, `uniqc/cli/submit.py`): Added `dummy` for unconstrained noiseless simulation, `dummy:local:virtual-line-N` and `dummy:local:virtual-grid-RxC` for noiseless constrained virtual topologies, and rule-based `dummy:<platform>:<backend>` identifiers for local noisy simulation against real backend topology and calibration data.

### Changed

- **Package layout**: backend/config/network/region/task code now lives under `uniqc.backend_adapter`; compiler, transpiler, QASM, and OriginIR parsers now live under `uniqc.compile`; visualization code lives under `uniqc.visualization`; shared analysis helpers live under `uniqc.utils`; PyTorch integration lives under `uniqc.torch_adapter`.
- **Import convention**: common user-facing objects are exported from `uniqc` directly, so examples and docs should prefer `from uniqc import Circuit, compile, get_backend` over deep package imports.
- **CLI entrypoint**: the package root no longer has `uniqc/__main__.py`; `python -m uniqc` is intentionally unsupported. Use `uniqc ...` or `python -m uniqc.cli ...`.
- **Dependency policy**: `pyproject.toml` keeps third-party dependencies unpinned and `uv.lock` is not tracked. Maintainer and CI environments should resolve latest dependencies with `uv sync --all-extras --group dev --upgrade`.
- **`_originir_to_circuit()`** (`uniqc/compile/compiler.py`): Refactored to use explicit `QINIT`/`CREG`/`MEASURE` opcode handling and a `pending_measurements` dict instead of regex-based `re.findall`; correctly records `qubit_num`, `cbit_num`, `max_qubit`, and `measure_list`.
- **`compile()` Qiskit import** (`uniqc/compile/compiler.py`): `transpile_qasm` is now lazily loaded via `_load_transpile_qasm()` — import is deferred until first `compile()` call, with a clear `CompilationFailedException` pointing to `pip install unified-quantum[qiskit]` when Qiskit is absent.
- **API docs generation**: per-module Sphinx `.rst` files are generated by `docs/Makefile` via `sphinx-apidoc`; generated `docs/source/uniqc*.rst` files stay out of version control.
- **Chip-backed dummy execution path** (`uniqc/backend_adapter/task_manager.py`, `uniqc/backend_adapter/task/adapters/dummy_adapter.py`): `dummy:<platform>:<backend>` now resolves the real backend topology and chip characterization, runs the normal compile/transpile path against that real target, stores `compiled_circuit_ir` and `executed_circuit_ir` in task metadata, and then executes locally with chip-derived noise. These rule-based identifiers are accepted by Python API, workflows, and CLI (`uniqc submit --platform dummy --backend originq:WK_C180`) but are intentionally not listed as standalone backend cards or registry rows.
- **Dummy workflow guidance**: `dummy=True` remains deprecated. Documentation and examples now prefer explicit backend ids: `dummy`, `dummy:local:virtual-line-3`, `dummy:local:virtual-grid-2x2`, and `dummy:originq:WK_C180`.

### Fixed

- **`Circuit.measure()` API in XEB circuits** (`uniqc/calibration/xeb/circuits.py`): All three XEB circuit generators (`generate_1q_xeb_circuits`, `generate_2q_xeb_circuit`, `generate_parallel_2q_xeb_circuits`) were using the old `measure(qubit, cbit)` signature. The `Circuit` API treats all positional arguments as qubit indices — `measure(0, 0)` means "measure qubit 0 twice", not "measure qubit 0 into classical bit 0". Fixed by using the correct `measure(*qubits)` API: `measure(qubit)` for single-qubit, `measure(qubit_u)` / `measure(qubit_v)` for 2q circuits, and `measure(i)` for parallel circuits. This was causing 1q XEB circuits to generate invalid OriginIR with `CREG N` mismatching `QINIT 1` and duplicate MEASURE statements, leading to empty `simulate_pmeasure` results and a fidelity of 1.0 (perfect) regardless of noise.
- **`seed=0` treated as falsy in XEB circuit generation** (`uniqc/calibration/xeb/circuits.py`): `seed=(seed + i) if seed else None` rejected `seed=0` as an invalid seed. Fixed with `seed is not None`.
- **`rng.choice()` numpy scalar types breaking gate parameter logic** (`uniqc/calibration/xeb/circuits.py`): `np.random.default_rng().choice()` returns numpy scalar types (`numpy.str_`, `numpy.int_`). The comparison `n_params == 0` returned `False` for `numpy.int_(0)`, causing all gates (including H, X, Y, Z, S, T) to be treated as parameterized — generating `gate q[0], (None)` in OriginIR which the parser rejects. Fixed by explicitly casting: `name = str(name)` and `n_params = int(n_params)`.
- **numpy fallback exponential fitter returning r=0.63 for ideal XEB data** (`uniqc/calibration/xeb/fitter.py`): The `_fit_exponential_numpy` fallback (used when scipy is unavailable) set `B = min(fidelities)`. For typical XEB data where fidelity monotonically decreases with depth, the minimum appears at the largest depth, making the residual at that point near zero. `log(residual) = -inf` destroys the linear regression slope, producing wildly inaccurate per-layer fidelity estimates (e.g. r=0.63 instead of r=0.99). Fixed by using a fixed `B = 0.5` (the ideal XEB asymptotic floor for maximal mixing), which avoids the singularity entirely.
- **Missing `print_warning` import causing CLI crash** (`uniqc/cli/calibrate.py`): The `print_warning` function was called at line 115 but was not imported, causing `NameError` at runtime when running `uniqc calibrate xeb` with `--type 2q` and no chip topology.
- **`DummyAdapter` using non-existent `ErrorModel(name=..., params=...)` API** (`uniqc/backend_adapter/task/adapters/dummy_adapter.py`): `_build_error_loader_from_chip` and `_build_error_loader_from_model` were constructing errors as `ErrorModel(name="Depolarizing", params=[p])`. The `ErrorModel` base class accepts `Depolarizing(p)` or `TwoQubitDepolarizing(p)` directly; it does not accept a `name` keyword argument. Fixed by using `Depolarizing(p)` and `TwoQubitDepolarizing(p)` subclasses directly.
- **`TwoQubitDepolarizing` passed to single-qubit gate contexts** (`uniqc/backend_adapter/task/adapters/dummy_adapter.py`): `gatetype_error` dict entries (CNOT, CZ, ISWAP generic errors) were using `TwoQubitDepolarizing(p)`, but these errors are applied in single-qubit processing contexts that only handle 1q error channels. Fixed by using `Depolarizing(p)` for all `gatetype_error` entries; `TwoQubitDepolarizing` is reserved for exact edge-match entries only.
- **`OriginIR_NoisySimulator` missing `backend_type` causing `simulate_pmeasure` to fail** (`uniqc/backend_adapter/task/adapters/dummy_adapter.py`): `simulate_pmeasure()` is only available on density-operator backends. `OriginIR_NoisySimulator` defaults to `backend_type="statevector"`, so calling `simulate_pmeasure` raised `ValueError: simulate_pmeasure only for density_operator`. Fixed by explicitly passing `backend_type="density_operator"` when constructing noisy simulators in both `_build_error_loader_from_chip` and `_build_error_loader_from_model`.
- **IBM backend gate fidelity flattened to one value** (`uniqc/backend_adapter/task/adapters/ibm_adapter.py`, `uniqc/gateway/api/backends.py`): IBM backend listing now reads per-qubit and per-edge `InstructionProperties(error=..., duration=...)` from `backend.target` (with `BackendProperties.gate_error()` fallback) and preserves those calibration details in the backend cache. Gateway topology rendering now uses these per-edge values even when chip-cache data is absent, instead of falling back to one global average 2Q fidelity for every edge.
- **Quafu backend topology missing from Gateway cards** (`uniqc/backend_adapter/task/adapters/quafu_adapter.py`, `uniqc/backend_adapter/backend_registry.py`, `uniqc/gateway/api/backends.py`): Quafu backend updates now parse the SDK `get_chip_info()` payload's `full_info.topological_structure` edge map (for example `Q0_Q1 -> {cz: {fidelity}}`), preserve topology and per-edge gate fidelities in the backend cache, and render those cached edges in Gateway even when the chip-characterization cache has not been populated. Reverse directed edge records are collapsed conservatively using the lower fidelity, matching PyQuafu's own topology drawing behavior.
- **`OriginQAdapter` default `backend_name` pointing to non-existent chip** (`uniqc/backend_adapter/task/adapters/originq_adapter.py`): `submit()`, `submit_batch()`, and `dry_run()` all hardcoded a fallback `backend_name="origin:wuyuan:d5"` which does not exist in the OriginQ cloud backend list. Any `OriginQAdapter` not explicitly given a `backend_name` kwarg would raise `RuntimeError: resource is null` when submitting to hardware. Fixed in three steps: (1) `OriginQAdapter.__init__` now accepts `backend_name: str | None = None` (defaults to `"PQPUMESH8"`); (2) all three methods now fall back to `self._last_backend_name` instead of the hardcoded wrong value; (3) `_get_adapter()` in both workflow files and `calibrate.py` CLI now extract the chip name from the `originq:CHIPNAME` format and pass it to `OriginQAdapter(backend_name=chip)`.
- **`_format_counts` not handling OriginQ cloud bitstring list return** (`uniqc/backend_adapter/task/adapters/originq_adapter.py`): OriginQ cloud returns a flat list of bitstrings (one per shot, e.g. `['00','01','10','11']`) in some configurations. The `_format_counts` method's `isinstance(counts, list)` branch only handled list-of-dicts (batch results), treating the list-of-strings case as zero-count and returning `{str(list_of_strings): 1}`. Fixed by adding a nested `elif isinstance(c, str)` branch that increments `merged[c]` for each bitstring.
- **`ReadoutCalibrator._submit_and_measure` not waiting for cloud task completion** (`uniqc/calibration/readout/calibrator.py`): `_submit_and_measure` and `_submit_and_measure_2q` called `adapter.query()` once and immediately used the result. For cloud backends (OriginQ, Quafu, IBM) where tasks are asynchronous, `query()` returns `"running"` status on the first call, leading to empty counts and `assignment_fidelity=0.0`. Fixed by adding a 60-second polling loop (2s interval) that retries `query()` until `status == "success"`.
- **`XEBenchmarker._get_noisy_probs` accessing wrong result key** (`uniqc/calibration/xeb/benchmarker.py`): `_get_noisy_probs` used `raw.get("counts", {})` to extract shot counts, but for OriginQ adapter `raw = result["result"]` is already the counts dict (not `{"counts": {...})`), so `get("counts", {})` returned `{}` and fidelity was computed against an all-zero probability vector, producing r≈0.15 instead of r=1.0 for ideal DummyAdapter. Fixed with the same pattern as `_submit_and_measure`: check `hasattr(raw, "counts")` first, then `isinstance(raw, dict)`.
- **`XEBenchmarker._circuit_fidelity` wrong qubit count for 2q circuits** (`uniqc/calibration/xeb/benchmarker.py`): `_circuit_fidelity` determined measured-qubit count via `list(range(circuit.qubit_num))`. For 2q XEB circuits using non-contiguous qubits (e.g. pair (0,10)), `circuit.qubit_num = 11` (max index + 1) instead of 2. This caused `n = 2 ** 11 = 2048` in the noisy-probability array while `p_ideal` had only 4 elements, triggering a `ValueError: operands could not be broadcast together with shapes (4,) (2048,)`. Fixed by deriving `n = len(p_ideal)` from the ground-truth ideal probability vector instead of `circuit.qubit_num`.
- **No backend availability validation in `OriginQAdapter`** (`uniqc/backend_adapter/task/adapters/originq_adapter.py`): `OriginQAdapter` did not validate whether a hardware backend was available before submitting, causing opaque `RuntimeError: resource is null` from the cloud service. Fixed by adding: (1) `get_available_backends()` method returning only `available == True` backends; (2) `BackendUnavailableError` exception (exported from `uniqc.backend_adapter.task.adapters`); (3) `_validate_backend()` called in `submit()` and `submit_batch()` that raises `BackendUnavailableError` with a message pointing users to `uniqc backend list --info`.
- **Bug 17 — `qubit_id` from pyqpanda3 is string not int** (`uniqc/backend_adapter/task/adapters/originq_adapter.py`): `sq.get_qubit_id()` returns `numpy.str_` (e.g. `'0'`, `'10'`), not `int`. The `SingleQubitData` construction used this directly, making `qubit_id == q` (int comparison) always `False`. Result: `DummyAdapter` with `chip_characterization` injected zero noise — fidelity stayed at 1.0 for noisy simulation. Fixed by wrapping with `int()` at the construction site.
- **Bug 18 — `available_qubits` from chip_info() returns strings** (`uniqc/backend_adapter/task/adapters/originq_adapter.py`): `ci.available_qubits()` returns strings, making `0 in chip.available_qubits` return `False`. Fixed by converting to `tuple(int(q) for q in ci.available_qubits())`.
- **Noisy XEB fidelity stuck at 1.0 — shot sampling destroying noise signal** (`uniqc/calibration/xeb/benchmarker.py`, `uniqc/backend_adapter/task/adapters/dummy_adapter.py`): The XEB benchmarker was computing `p_noisy` from shot counts (via `submit/query`), then normalizing — this adds sampling noise that overwhelms the weak hardware noise. For `DummyAdapter` with chip characterization, the injected noise (WK_C180: ~0.9994 1Q fidelity) was invisible against shot variance. Fixed by adding `DummyAdapter.simulate_pmeasure(originir)` which returns the exact density-matrix probability vector (no shot sampling). The benchmarker now calls `adapter.simulate_pmeasure()` when available, giving faithful Hellinger fidelity comparison.
- **Wheel CI after root cleanup** (`.github/workflows/python_build_wheel.yml`): Updated the wheel workflow to call `scripts/stubgen.py` after the root-level `stubgen.py` cleanup and to install `pybind11-stubgen` explicitly before generating C++ extension stubs.
- **numpy fallback fitter returning r=1.0 for non-monotonic XEB data** (`uniqc/calibration/xeb/fitter.py`): `_fit_exponential_numpy` clipped the fitted slope to `r = exp(clip(slope, log(0.001), 0))`. With weak noise and shallow depths, mean fidelity per depth is non-monotonic (circuit-to-circuit variance dominates), giving a positive slope and `r=1.0`. Fixed by adding a pairwise ratio method: for each (i,j) pair of data points, `r_ij = ((F_i - B)/(F_j - B))^(1/(m_i - m_j))`, then take the geometric mean. When slope >= 0 the pairwise result is used instead of the clipped linear regression.

## [0.0.7.post1] - 2026-05-01

### Fixed

- **`uniqc simulate --backend density`** (`uniqc/cli/simulate.py`): The CLI `--backend density` option is now correctly normalised to the Python API backend name `densitymatrix`. Previously the simulator raised "Unknown backend type: density" because the raw CLI value was passed directly without mapping. (`#39`)
- **`uniqc submit --dry-run` duplicate `shots` argument** (`uniqc/cli/submit.py`): Fixed `TypeError: dry_run_task() got multiple values for keyword argument 'shots'` caused by `shots` being passed both as a direct keyword argument and inside `**kwargs` in `_handle_dry_run()`. (`#40`)
- **`dry_run_task(backend="dummy:local:simulator")`** (`uniqc/task_manager.py`): `DummyAdapter` is now registered in the `dry_run_task()` adapter map, allowing `dry_run_task(circuit, backend="dummy:local:simulator")` to work without requiring an explicit `dummy=True` override. (`#40`)
- **`uniqc backend list --format json` TypeError** (`uniqc/cli/backend.py`): Fixed `TypeError: json must be str` when running `--format json` by passing the list as `data=json_data` to Rich's `console.print_json()` keyword argument. (`#41`)
- **`uniqc config validate` rejects `active_profile`** (`uniqc/config.py`): `validate_config()` now correctly skips the `active_profile` top-level metadata key (previously reported as "Profile 'active_profile' must be a dictionary"). The `META_KEYS` frozenset was already defined but not consulted during validation. (`#42`)
- **`uniqc submit` batch dummy mode leaves failed tasks** (`uniqc/cli/submit.py`, `uniqc/task_manager.py`): Fixed two bugs: (1) `_submit_batch()` now correctly passes `backend="dummy:local:simulator"` instead of `backend="originq"` when `--platform dummy`; (2) `submit_batch()` now calls the existing `_submit_batch_dummy()` helper which pre-populates task results, instead of going through the backend registry path which left tasks in a perpetual `RUNNING` → `FAILED` state. (`#43`)
- **Dummy backend shot count integrity** (`uniqc/task/result_types.py`): `UnifiedResult.from_probabilities()` now uses `round()` instead of `int()` for converting probabilities to counts, with explicit compensation to guarantee `sum(counts.values()) == shots`. Previously `int()` truncation could cause counts to sum below the requested shot count due to floating-point precision errors. (`#44`)
- **Python API tokens not read from YAML config** (`uniqc/task/config.py`): `load_originq_config()`, `load_quafu_config()`, and `load_ibm_config()` now fall back to reading tokens from `~/.uniqc/config.yaml` (written by `uniqc config set`) when the respective environment variable is not set. This unifies CLI and Python API credential handling. (`#45`)
- **`unified-quantum[all]` qiskit conflict** (`pyproject.toml`): Removed `qiskit-ibm-provider>=0.10` from the `qiskit` and `all` extras. `qiskit-ibm-provider` is only compatible with qiskit 0.44–0.46 and is incompatible with `qiskit>=1.0`. IBM Quantum users should install `qiskit-ibm-runtime` separately for qiskit 1.x/2.x support. (`#46`)
- **`uniqc backend chip-display` shows `0,0` qubit pairs** (`uniqc/task/adapters/originq_adapter.py`): `get_chip_characterization()` now uses the chip topology index to look up qubit pair `(u, v)` identifiers, fixing the per-pair 2Q gate table showing repeated `0, 0` for all pairs. The previous fallback of `hasattr(dq, "get_qubit_u")` was returning `False` for the OriginQ `double_qubits_info()` objects. (`#47`)
- **OriginQ simulator backends not usable via `submit_task`** (`uniqc/task/adapters/originq_adapter.py`): Simulator backends (`full_amplitude`, `partial_amplitude`, `single_amplitude`) are now routed to the `QCloudSimulator` API instead of the QPU `QCloudOptions` path. Previously all OriginQ backends used `backend.run(qprog, shots, options=QCloudOptions(...))` which raised "Run with QCloudOptions is only for QPU" for simulator backends. (`#48`)

## [0.0.7] - 2026-05-01

### Added

- **`Circuit.get_matrix()`** (`uniqc/circuit_builder/matrix.py`): Extracts the unitary matrix representation of a `Circuit` by folding all gate matrices via tensor product and contraction. Supports all standard gates (`H`, `X`, `Y`, `Z`, `S`, `T`, `SX`, `RX`, `RY`, `RZ`, `CNOT`, `CZ`, `CPHASE`, `SWAP`, controlled variants). Raises `NotMatrixableError` for gates without a finite unitary (e.g. measurement, decoherence channels).
- **`uniqc backend chip-display` CLI** (`uniqc/cli/chip_display.py`): New `chip-display` subcommand under `uniqc backend` — displays per-qubit chip characterisation data (T1/T2 times, single- and two-qubit gate fidelity, readout fidelity, topology) for any platform backend. Replaces the former standalone `uniqc chip` command; the data layer (`chip_info.py` / `chip_cache.py` / `chip_service.py`) is unchanged.
- **AI-friendly CLI help system** (`uniqc/cli/`): Every `--help` output now includes documentation links and GitHub reference panels rendered in Rich markup. New `--ai-hints` flag (and `UNIQC_AI_HINTS=1` env var) surfaces a Rich panel with AI workflow guidance, error recovery hints, and command chaining examples for every operation. `uniqc/cli/refs.py` is the single source of truth for all URLs and hint copy.
- **Chip characterisation data layer** (`uniqc/cli/chip_info.py`, `chip_cache.py`, `chip_service.py`): Unified `SingleQubitData`, `TwoQubitData`, `ChipGlobalInfo`, `ChipCharacterization` dataclasses for per-qubit T1/T2, gate/readout fidelity, connectivity, and global chip properties. `ChipCache` persists data as JSON in `~/.uniqc/backend-cache/`. `ChipService` orchestrates fetch from OriginQ/Quafu/IBM via adapter `get_chip_characterization()`.
- **Enhanced Transpiler** (`uniqc/transpiler/compiler.py`): New `compile()` function — the canonical chip-aware circuit transpilation entry point for UnifiedQuantum. Wraps Qiskit transpilation with `BackendInfo`/`ChipCharacterization`-aware routing, multiple output formats, and typed `TranspilerConfig`. Supports `output_format="circuit"` (default, returns `Circuit`), `"originir"`, and `"qasm"`. `level` parameter maps directly to Qiskit optimization levels 0–3. `basis_gates` accepts a custom gate set (default: `["cz", "sx", "rz"]`).
- **`TranspilerConfig` dataclass** (`uniqc/transpiler/compiler.py`): Typed configuration object for `compile()`, frozen and hashable. Validates `type` and `level` at construction time.
- **`CompilationResult` dataclass** (`uniqc/transpiler/compiler.py`): Holds compiled output, estimated fidelity, SWAP overhead count, and informational messages from the transpiler pipeline.
- **Fidelity-weighted routing** (`_route_with_fidelity`): Dijkstra-based SWAP insertion that treats each edge weight as `1 - fidelity`, preferring high-fidelity qubit chains. Computes a cumulative circuit fidelity estimate as a by-product.
- **`BackendOptions` hierarchy** (`uniqc/task/options.py`): Typed `BackendOptions` base class with platform-specific subclasses — `OriginQOptions`, `QuafuOptions`, `IBMOptions`, `DummyOptions` — and a `BackendOptionsFactory` for constructing from `**kwargs` dicts or direct instantiation. All fields are validated with sensible defaults; `to_kwargs()` bridges back to the existing adapter `**kwargs` interface.
- **`BackendOptionsFactory`**: Three-mode factory — accepts `None` (returns platform defaults), a `BackendOptions` instance (returned unchanged), or a `dict` (treated as `**kwargs`). Main integration point is `normalize_options()`.
- **`RegionSelector`** (`uniqc/region_selector.py`): Finds optimal physical qubit regions from `ChipCharacterization` calibration data. `find_best_1D_chain(length)` uses greedy expansion with DFS backtracking fallback to return the lexicographically-first highest-fidelity chain. `find_best_2D_from_circuit(circuit)` enumerates rectangular subgraphs and scores them by `estimate_circuit_fidelity()`. All three methods support product-of-fidelities fidelity estimation.
- **Top-level exports**: `compile`, `TranspilerConfig`, `CompilationResult`, `CompilationFailedException`, `RegionSelector`, `ChainSearchResult`, `RegionSearchResult`, `OriginQOptions`, `QuafuOptions`, `IBMOptions`, `DummyOptions`, `BackendOptionsFactory`, `BackendOptionsError` are now exported from `uniqc/__init__.py`.
- **`DummyBackend`** (`uniqc/backend.py`): New `QuantumBackend` subclass registered as `"dummy"` in `BACKENDS`. Accepts `config` dict with keys: `chip_characterization` (chip data auto-converted to noise), `chip_id` (fetched from OriginQ and auto-converted), `noise_model`, `available_qubits`, `available_topology`. Enables `get_backend("dummy")` and `submit_task(circuit, "dummy", ...)` as first-class citizens. Use cases::

    ```python
    from uniqc.backend import get_backend
    from uniqc.task.adapters.originq_adapter import OriginQAdapter

    # Noiseless simulation
    backend = get_backend("dummy")
    task_id = backend.submit(circuit, shots=1000)

    # Realistic noise from chip characterization
    chip = OriginQAdapter().get_chip_characterization("origin:wuyuan:d5")
    backend = get_backend("dummy", config={"chip_characterization": chip})
    task_id = backend.submit(circuit, shots=1000)
    ```

- **`uniqc backend` CLI docs** (`docs/source/cli/backend.md`): Full reference for all four `uniqc backend` subcommands — `list`, `update`, `show`, `chip-display` — with examples and a quick-reference table.
- **Platform conventions guide** (`docs/source/guide/platform_conventions.md`): Documents input/output formats, run modes, gate support, chip naming conventions, token configuration, and proxy settings for every platform (OriginQ / Quafu / IBM / Dummy).
- **4-qubit GHZ CLI example** (`examples/CLI_example/`): Step-by-step guide (Chinese + English) covering config validation, backend discovery, circuit submission, and result polling — with circuit files in both OriginIR and OpenQASM 2.0 formats.

### Changed

- **`_originir_to_circuit()`** (`uniqc/transpiler/compiler.py`): Refactored to use explicit `QINIT`/`CREG`/`MEASURE` opcode handling and a `pending_measurements` dict instead of regex-based `re.findall`; correctly records `qubit_num`, `cbit_num`, `max_qubit`, and `measure_list`. Measurement shots are now validated against the probability vector resolution.
- **`compile()` Qiskit import** (`uniqc/transpiler/compiler.py`): `transpile_qasm` is now lazily loaded via `_load_transpile_qasm()` — import is deferred until first `compile()` call, with a clear `CompilationFailedException` pointing to `pip install unified-quantum[qiskit]` when Qiskit is absent.
- **`uniqc/transpiler/__init__.py`**: `plot_time_line` import is now lazy with a silent `None` fallback when matplotlib is unavailable; export style normalised to explicit `as` renaming for all public symbols.
- **`submit_task()` / `submit_batch()`** (`uniqc/task_manager.py`): Added optional `options` parameter accepting `BackendOptions | dict | None`. When provided, options are normalised via `BackendOptionsFactory.normalize_options()` and merged with any extra `**kwargs`. Fully backward-compatible — existing `**kwargs`-only calls are unchanged.
- **`submit_task(..., dummy=True)` / `submit_batch(..., dummy=True)`** (`uniqc/task_manager.py`): The `dummy=` parameter is deprecated. Use `backend="dummy:local:simulator"` instead, which now routes through the properly registered `DummyBackend` — no functional change for existing callers, but a `DeprecationWarning` is emitted.
- **`DummyAdapter`** (`uniqc/task/adapters/dummy_adapter.py`): Now accepts `chip_characterization: ChipCharacterization | None` at construction. When provided, automatically derives realistic noise parameters from per-qubit (single-gate fidelity, T1/T2, readout fidelity) and per-pair (two-qubit gate fidelity) calibration data. Readout errors are also injected via the `readout_error` parameter of `OriginIR_NoisySimulator`. Explicit `noise_model` takes precedence over chip-derived noise.
- **`Platform` enum** (`uniqc/backend_info.py`): Added `DUMMY = "dummy"` variant to support the dummy simulator in `BackendOptions`.
- **`uniqc chip` → `uniqc backend chip-display`** (`uniqc/cli/`): Chip data modules (`chip_info.py`, `chip_cache.py`, `chip_service.py`) moved from `uniqc/` to `uniqc/cli/` to co-locate CLI-adjacent code. The `uniqc chip` entry point is removed; use `uniqc backend chip-display` instead.
- **`-V` / `--version` flag** (`uniqc/cli/main.py`): Added a typer callback so `uniqc --version` / `uniqc -V` now print the package version instead of delegating to `--help`.
- **CLI docs overhaul** (`docs/source/cli/`): Restructured toctree with a new `cli/backend.md` entry; `cli/submit.md` gains a `--dry-run` section; `cli/workflow.md` incorporates `backend show` / `chip-display` in Step 2 and `--dry-run` in Steps 2/3; `cli/task.md` adds a cross-ref to the result command.

### Fixed

- **`compile(output_format="originir")`**: Was incorrectly returning raw QASM string. Now correctly calls `convert_qasm_to_oir()` before returning.
- **`RegionSelector._backtrack_chain`**: DFS was returning the highest-fidelity path overall instead of the best path of the exact requested length. Added separate `best_exact_path`/`best_exact_fid` tracking so exact-length paths are returned correctly.
- **`RegionSelector._greedy_chain_expand`**: DFS was returning the full longest path even when only `length` qubits were requested. Added truncation to return exactly `length` qubits.
- **`RegionSelector._build_graph`**: Fixed `TypeError` when iterating over `QubitTopology` dataclass edges — changed from tuple unpacking to attribute access (`.u`, `.v`).
- **ECR gate simulation** (`uniqc/originir/originir_simulator.py`): `OpcodeSimulator` had no handler for ECR despite `available_originir_2q_gates` listing it, causing `random_originir()` circuits to fail at simulation with `"Unknown Opcode: ECR"`. Implemented via native-gate decomposition: `SX(0)·SX(1)·X(0)·X(1)·CNOT(0,1)·S(0)`.
- **OriginQ adapter robustness** (`uniqc/task/adapters/originq_adapter.py`): `OriginQCircuitAdapter.adapt()` now returns OriginIR directly (avoids a double-conversion bug); `backend.chip_info()` calls are guarded; `query()` uses `job.query()` instead of `job.status()` for authoritative cloud status; `_format_counts()` returns a flat `{bitstring: shots}` dict; `wait_for_result()` now performs a final uncached query on timeout rather than raising `TaskTimeoutError` for tasks that have actually completed.
- **Dry-run validation** (`uniqc/task/`): Every `QuantumAdapter` now implements `dry_run(originir, shots, **kwargs)` for offline circuit compatibility checking — no cloud API calls are made. `QiskitAdapter` validates against `backend.basis_gates` via `transpile()`; `QuafuAdapter` checks `translate_circuit()`; `OriginQAdapter` calls `convert_originir_string_to_qprog()` locally; `DummyAdapter` always succeeds. Returns `DryRunResult(success, details, error, warnings, circuit_qubits, supported_gates)`. `dry_run_task()` / `dry_run_batch()` exposed in `task_manager`. CLI: `uniqc submit --dry-run` with table or JSON output. A dry-run success followed by actual submission failure is a **critical bug**.
- **Unified adapter `query()` result** (`uniqc/task/adapters/`): All platform adapters (Quafu, IBM, Dummy) now return a flat `{bitstring: shots}` dict, matching the OriginQ format. `UnifiedResult` gains a `to_dict()` method. IBM batch submit now returns ≥1 results per job.
- **Quafu adapter expansion** (`uniqc/task/adapters/quafu_adapter.py`): `_reconstruct_qasm()` now supports `Y`, `Z`, `S`, `SX`, `T`, `SWAP`, `ISWAP`, `BARRIER`. `VALID_CHIP_IDS` expanded to all ScQ-series and simulator chips. Added `wait` param to `submit()` / `submit_batch()` and a `query_sync()` method.
- **`submit_batch` return type** (`uniqc/task/adapters/qiskit_adapter.py`): Was incorrectly returning `str`; now correctly returns `list[str]`.

## [0.0.6] - 2026-04-29

### Added

- **Backend Registry**: New `backend_registry`, `backend_info`, and `backend_cache` modules providing a unified backend discovery and caching layer across all cloud platforms.
- **`uniqc backend` CLI subcommand**: New `backend list`, `backend show <backend>`, and `backend update` commands for querying and inspecting available cloud backends (supports `--all`, `--info` flags, fidelity display, and topology info).
- **IBM Quantum adapter** (`ibm_adapter.py`): New `QuantumAdapter` implementation for IBM Quantum Platform, registered under the `ibm` platform key. Also re-exported as `IBMAdapter` via the existing `qiskit_adapter` module.
- **OriginQ qubit count on submit**: `OriginQAdapter.submit()` now automatically queries `backend.chip_info().qubits_num` to determine the backend qubit count, stored for use in subsequent query operations. `submit_batch()` applies the same logic per group.
- **`uniqc config` command**: New `config init` and `config set` subcommands for managing cloud platform tokens interactively.
- **OriginIR noise channel documentation**: The language spec now documents all single- and two-qubit error channels (`Decoherence`, `Depolarizing`, `AmplitudeDamping`, `PhaseDamping`, `Pauli`) with syntax examples.

### Changed

- **Documentation**: Comprehensive OriginIR language specification covering gate operations, control structures (`CONTROL`/`DAGGER`/nesting rules), `DEF` blocks (parameterized definitions, invocation, Python API mapping), named `Circuit` definitions (`@circuit_def` decorator, parameter binding), parametric circuits, error channels, and full examples.
- **README**: Added AI-native positioning and CLI-first design principles, unified-platforms concept diagram, `uv` installation instructions, optional dependency table, and backend query quick reference.
- **CI docs deployment**: `deploy_docs.yml` now triggers on release tags in addition to the `docs/*` branch path, ensuring documentation is published automatically on every release.

### Fixed

- **dill version constraint**: Added `dill>=0.4.1` lower bound to resolve a compatibility issue where `torchquantum` installation downgrades dill to 0.3.4, causing Qiskit transpile to fail with `Tried to instantiate class Qubit._from_owned, but it does not exist!`.
- **Windows CI compatibility**: Removed `2>/dev/null` bash-ism from CI workflows; the `|| true` guard alone is sufficient and works cross-platform.
- **OriginIR measurement preservation**: Fixed `ff8dc2c` which corrected the OriginIR parser to preserve measurement gates during round-trip parsing.

### Refactored

- **Test isolation**: Removed all `unittest.mock` usage from test files. Cloud and platform-specific tests now use real optional dependencies with `pytest` markers (`@pytest.mark.cloud`, `@pytest.mark.skip_cloud`) and skip gracefully when deps are absent. Deleted import isolation test files (`test_*_import_pytest.py`).

## [0.0.5] - 2026-04-21

### Added

- OriginIR and OpenQASM 2.0 dual-format circuit builder (`Circuit.originir` / `Circuit.qasm`)
- `submit_task` / `wait_for_result` cloud execution API
- `uniqc simulate` and `uniqc submit` CLI commands
- Local OriginIR and QASM simulators (statevector, partial amplitude, single amplitude)
- Quafu cloud adapter
- `QuantumLayer` and PyTorch gradient support
- HEA, UCCSD, QAOA ansatz components

### Fixed

- CLI parser edge cases around QASM output format and profile flags
- Wheel ABI tag validation in CI

## [0.0.4] - 2026-04-19

### Added

- `uniqc` CLI entry point with `--help` and subcommand routing
- C++ OriginIR simulator via pybind11 / CMake build
- Documentation on ReadTheDocs / GitHub Pages

## [0.0.3] - 2026-04-18

### Added

- Initial PyPI release (`unified-quantum`)
- `Circuit` class with basic gate API (`h`, `cnot`, `measure`, etc.)
- `Backend` and `Result` abstractions
