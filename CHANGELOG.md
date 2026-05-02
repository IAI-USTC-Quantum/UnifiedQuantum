# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`Circuit.get_matrix()`** (`uniqc/circuit_builder/matrix.py`): Extracts the unitary matrix representation of a `Circuit` by folding all gate matrices via tensor product and contraction. Supports all standard gates (`H`, `X`, `Y`, `Z`, `S`, `T`, `SX`, `RX`, `RY`, `RZ`, `CNOT`, `CZ`, `CPHASE`, `SWAP`, controlled variants). Raises `NotMatrixableError` for gates without a finite unitary (e.g. measurement, decoherence channels).
- **Measurement probability checks** (`uniqc/transpiler/compiler.py`): `_originir_to_circuit()` now correctly tracks MEASURE gates with non-contiguous qubit and classical bit registers via a deferred `pending_measurements` buffer, fixing circuits where qubits map to non-zero classical bits.
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
- **`uniqc.algorithm`** (`uniqc/algorithm/`): New module for chip-agnostic high-level workflows. All algorithms work with any supported `QuantumAdapter`. WK180-specific code lives in `examples/wk180/`.
- **`uniqc.algorithm.xeb_workflow`** (`uniqc/algorithm/xeb_workflow.py`): `run_1q_xeb_workflow()`, `run_2q_xeb_workflow()`, `run_parallel_xeb_workflow()`. Combines `ReadoutCalibrator` → `ReadoutEM` → `XEBenchmarker` → exponential fit. Reads entangler gate fidelity from `ChipCharacterization.two_qubit_data`.
- **`uniqc.algorithm.readout_em_workflow`** (`uniqc/algorithm/readout_em_workflow.py`): `run_readout_em_workflow()` calibrates readout and returns a ready-to-use `ReadoutEM` instance. `apply_readout_em()` applies EM to a `UnifiedResult`.
- **`examples/wk180/`**: `xeb.py` and `readout_em.py` demonstrating WK180 (OriginQ) chip integration. `dummy=True` fetches chip characterization via `OriginQAdapter.get_chip_characterization()` and uses `DummyAdapter(chip_characterization=...)`. `dummy=False` uses `OriginQAdapter` directly.
- **`uniqc calibrate` CLI** (`uniqc/cli/calibrate.py`): Three subcommands — `uniqc calibrate xeb` (1q/2q XEB), `uniqc calibrate readout` (1q/2q readout calibration), `uniqc calibrate pattern` (parallel execution pattern analysis). All integrate with `algorithm/` workflows and cache.
- **Top-level exports** (`uniqc/__init__.py`): `calibration`, `XEBResult`, `ReadoutCalibrationResult`, `save_calibration_result`, `load_calibration_result`, `find_cached_results`, `qem`, `M3Mitigator`, `StaleCalibrationError`, `ReadoutEM`, `algorithm`.
- **Calibration test suite** (`uniqc/test/calibration/`): 43 tests covering XEB circuits, exponential fitter, parallel patterns (DSatur), readout calibrator, unified `ReadoutEM` dispatch, and `M3Mitigator` with TTL enforcement.

### Changed

- **`_originir_to_circuit()`** (`uniqc/transpiler/compiler.py`): Refactored to use explicit `QINIT`/`CREG`/`MEASURE` opcode handling and a `pending_measurements` dict instead of regex-based `re.findall`; correctly records `qubit_num`, `cbit_num`, `max_qubit`, and `measure_list`.
- **`compile()` Qiskit import** (`uniqc/transpiler/compiler.py`): `transpile_qasm` is now lazily loaded via `_load_transpile_qasm()` — import is deferred until first `compile()` call, with a clear `CompilationFailedException` pointing to `pip install unified-quantum[qiskit]` when Qiskit is absent.
- **`uniqc/transpiler/__init__.py`**: `plot_time_line` import is now lazy with a silent `None` fallback when matplotlib is unavailable; export style normalised to explicit `as` renaming for all public symbols.

### Fixed

- **`Circuit.measure()` API in XEB circuits** (`uniqc/calibration/xeb/circuits.py`): All three XEB circuit generators (`generate_1q_xeb_circuits`, `generate_2q_xeb_circuit`, `generate_parallel_2q_xeb_circuits`) were using the old `measure(qubit, cbit)` signature. The `Circuit` API treats all positional arguments as qubit indices — `measure(0, 0)` means "measure qubit 0 twice", not "measure qubit 0 into classical bit 0". Fixed by using the correct `measure(*qubits)` API: `measure(qubit)` for single-qubit, `measure(qubit_u)` / `measure(qubit_v)` for 2q circuits, and `measure(i)` for parallel circuits. This was causing 1q XEB circuits to generate invalid OriginIR with `CREG N` mismatching `QINIT 1` and duplicate MEASURE statements, leading to empty `simulate_pmeasure` results and a fidelity of 1.0 (perfect) regardless of noise.
- **`seed=0` treated as falsy in XEB circuit generation** (`uniqc/calibration/xeb/circuits.py`): `seed=(seed + i) if seed else None` rejected `seed=0` as an invalid seed. Fixed with `seed is not None`.
- **`rng.choice()` numpy scalar types breaking gate parameter logic** (`uniqc/calibration/xeb/circuits.py`): `np.random.default_rng().choice()` returns numpy scalar types (`numpy.str_`, `numpy.int_`). The comparison `n_params == 0` returned `False` for `numpy.int_(0)`, causing all gates (including H, X, Y, Z, S, T) to be treated as parameterized — generating `gate q[0], (None)` in OriginIR which the parser rejects. Fixed by explicitly casting: `name = str(name)` and `n_params = int(n_params)`.
- **numpy fallback exponential fitter returning r=0.63 for ideal XEB data** (`uniqc/calibration/xeb/fitter.py`): The `_fit_exponential_numpy` fallback (used when scipy is unavailable) set `B = min(fidelities)`. For typical XEB data where fidelity monotonically decreases with depth, the minimum appears at the largest depth, making the residual at that point near zero. `log(residual) = -inf` destroys the linear regression slope, producing wildly inaccurate per-layer fidelity estimates (e.g. r=0.63 instead of r=0.99). Fixed by using a fixed `B = 0.5` (the ideal XEB asymptotic floor for maximal mixing), which avoids the singularity entirely.
- **Missing `print_warning` import causing CLI crash** (`uniqc/cli/calibrate.py`): The `print_warning` function was called at line 115 but was not imported, causing `NameError` at runtime when running `uniqc calibrate xeb` with `--type 2q` and no chip topology.
- **`DummyAdapter` using non-existent `ErrorModel(name=..., params=...)` API** (`uniqc/task/adapters/dummy_adapter.py`): `_build_error_loader_from_chip` and `_build_error_loader_from_model` were constructing errors as `ErrorModel(name="Depolarizing", params=[p])`. The `ErrorModel` base class accepts `Depolarizing(p)` or `TwoQubitDepolarizing(p)` directly; it does not accept a `name` keyword argument. Fixed by using `Depolarizing(p)` and `TwoQubitDepolarizing(p)` subclasses directly.
- **`TwoQubitDepolarizing` passed to single-qubit gate contexts** (`uniqc/task/adapters/dummy_adapter.py`): `gatetype_error` dict entries (CNOT, CZ, ISWAP generic errors) were using `TwoQubitDepolarizing(p)`, but these errors are applied in single-qubit processing contexts that only handle 1q error channels. Fixed by using `Depolarizing(p)` for all `gatetype_error` entries; `TwoQubitDepolarizing` is reserved for exact edge-match entries only.
- **`OriginIR_NoisySimulator` missing `backend_type` causing `simulate_pmeasure` to fail** (`uniqc/task/adapters/dummy_adapter.py`): `simulate_pmeasure()` is only available on density-operator backends. `OriginIR_NoisySimulator` defaults to `backend_type="statevector"`, so calling `simulate_pmeasure` raised `ValueError: simulate_pmeasure only for density_operator`. Fixed by explicitly passing `backend_type="density_operator"` when constructing noisy simulators in both `_build_error_loader_from_chip` and `_build_error_loader_from_model`.
- **`OriginQAdapter` default `backend_name` pointing to non-existent chip** (`uniqc/task/adapters/originq_adapter.py`): `submit()`, `submit_batch()`, and `dry_run()` all hardcoded a fallback `backend_name="origin:wuyuan:d5"` which does not exist in the OriginQ cloud backend list. Any `OriginQAdapter` not explicitly given a `backend_name` kwarg would raise `RuntimeError: resource is null` when submitting to hardware. Fixed in three steps: (1) `OriginQAdapter.__init__` now accepts `backend_name: str | None = None` (defaults to `"PQPUMESH8"`); (2) all three methods now fall back to `self._last_backend_name` instead of the hardcoded wrong value; (3) `_get_adapter()` in both workflow files and `calibrate.py` CLI now extract the chip name from the `originq:CHIPNAME` format and pass it to `OriginQAdapter(backend_name=chip)`.
- **`_format_counts` not handling OriginQ cloud bitstring list return** (`uniqc/task/adapters/originq_adapter.py`): OriginQ cloud returns a flat list of bitstrings (one per shot, e.g. `['00','01','10','11']`) in some configurations. The `_format_counts` method's `isinstance(counts, list)` branch only handled list-of-dicts (batch results), treating the list-of-strings case as zero-count and returning `{str(list_of_strings): 1}`. Fixed by adding a nested `elif isinstance(c, str)` branch that increments `merged[c]` for each bitstring.
- **`ReadoutCalibrator._submit_and_measure` not waiting for cloud task completion** (`uniqc/calibration/readout/calibrator.py`): `_submit_and_measure` and `_submit_and_measure_2q` called `adapter.query()` once and immediately used the result. For cloud backends (OriginQ, Quafu, IBM) where tasks are asynchronous, `query()` returns `"running"` status on the first call, leading to empty counts and `assignment_fidelity=0.0`. Fixed by adding a 60-second polling loop (2s interval) that retries `query()` until `status == "success"`.
- **`XEBenchmarker._get_noisy_probs` accessing wrong result key** (`uniqc/calibration/xeb/benchmarker.py`): `_get_noisy_probs` used `raw.get("counts", {})` to extract shot counts, but for OriginQ adapter `raw = result["result"]` is already the counts dict (not `{"counts": {...})`), so `get("counts", {})` returned `{}` and fidelity was computed against an all-zero probability vector, producing r≈0.15 instead of r=1.0 for ideal DummyAdapter. Fixed with the same pattern as `_submit_and_measure`: check `hasattr(raw, "counts")` first, then `isinstance(raw, dict)`.
- **`XEBenchmarker._circuit_fidelity` wrong qubit count for 2q circuits** (`uniqc/calibration/xeb/benchmarker.py`): `_circuit_fidelity` determined measured-qubit count via `list(range(circuit.qubit_num))`. For 2q XEB circuits using non-contiguous qubits (e.g. pair (0,10)), `circuit.qubit_num = 11` (max index + 1) instead of 2. This caused `n = 2 ** 11 = 2048` in the noisy-probability array while `p_ideal` had only 4 elements, triggering a `ValueError: operands could not be broadcast together with shapes (4,) (2048,)`. Fixed by deriving `n = len(p_ideal)` from the ground-truth ideal probability vector instead of `circuit.qubit_num`.
- **No backend availability validation in `OriginQAdapter`** (`uniqc/task/adapters/originq_adapter.py`): `OriginQAdapter` did not validate whether a hardware backend was available before submitting, causing opaque `RuntimeError: resource is null` from the cloud service. Fixed by adding: (1) `get_available_backends()` method returning only `available == True` backends; (2) `BackendUnavailableError` exception (exported from `uniqc.task.adapters`); (3) `_validate_backend()` called in `submit()` and `submit_batch()` that raises `BackendUnavailableError` with a message pointing users to `uniqc backend list --info`.

## [0.0.7.post1] - 2026-05-01

### Fixed

- **`uniqc simulate --backend density`** (`uniqc/cli/simulate.py`): The CLI `--backend density` option is now correctly normalised to the Python API backend name `densitymatrix`. Previously the simulator raised "Unknown backend type: density" because the raw CLI value was passed directly without mapping. (`#39`)
- **`uniqc submit --dry-run` duplicate `shots` argument** (`uniqc/cli/submit.py`): Fixed `TypeError: dry_run_task() got multiple values for keyword argument 'shots'` caused by `shots` being passed both as a direct keyword argument and inside `**kwargs` in `_handle_dry_run()`. (`#40`)
- **`dry_run_task(backend="dummy")`** (`uniqc/task_manager.py`): `DummyAdapter` is now registered in the `dry_run_task()` adapter map, allowing `dry_run_task(circuit, backend="dummy")` to work without requiring an explicit `dummy=True` override. (`#40`)
- **`uniqc backend list --format json` TypeError** (`uniqc/cli/backend.py`): Fixed `TypeError: json must be str` when running `--format json` by passing the list as `data=json_data` to Rich's `console.print_json()` keyword argument. (`#41`)
- **`uniqc config validate` rejects `active_profile`** (`uniqc/config.py`): `validate_config()` now correctly skips the `active_profile` top-level metadata key (previously reported as "Profile 'active_profile' must be a dictionary"). The `META_KEYS` frozenset was already defined but not consulted during validation. (`#42`)
- **`uniqc submit` batch dummy mode leaves failed tasks** (`uniqc/cli/submit.py`, `uniqc/task_manager.py`): Fixed two bugs: (1) `_submit_batch()` now correctly passes `backend="dummy"` instead of `backend="originq"` when `--platform dummy`; (2) `submit_batch()` now calls the existing `_submit_batch_dummy()` helper which pre-populates task results, instead of going through the backend registry path which left tasks in a perpetual `RUNNING` → `FAILED` state. (`#43`)
- **Dummy backend shot count integrity** (`uniqc/task/result_types.py`): `UnifiedResult.from_probabilities()` now uses `round()` instead of `int()` for converting probabilities to counts, with explicit compensation to guarantee `sum(counts.values()) == shots`. Previously `int()` truncation could cause counts to sum below the requested shot count due to floating-point precision errors. (`#44`)
- **Python API tokens not read from YAML config** (`uniqc/task/config.py`): `load_originq_config()`, `load_quafu_config()`, and `load_ibm_config()` now fall back to reading tokens from `~/.uniqc/uniqc.yml` (written by `uniqc config set`) when the respective environment variable is not set. This unifies CLI and Python API credential handling. (`#45`)
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
- **`submit_task(..., dummy=True)` / `submit_batch(..., dummy=True)`** (`uniqc/task_manager.py`): The `dummy=` parameter is deprecated. Use `backend="dummy"` instead, which now routes through the properly registered `DummyBackend` — no functional change for existing callers, but a `DeprecationWarning` is emitted.
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
