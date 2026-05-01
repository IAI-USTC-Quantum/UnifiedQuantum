# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`Circuit.get_matrix()`** (`uniqc/circuit_builder/matrix.py`): Extracts the unitary matrix representation of a `Circuit` by folding all gate matrices via tensor product and contraction. Supports all standard gates (`H`, `X`, `Y`, `Z`, `S`, `T`, `SX`, `RX`, `RY`, `RZ`, `CNOT`, `CZ`, `CPHASE`, `SWAP`, controlled variants). Raises `NotMatrixableError` for gates without a finite unitary (e.g. measurement, decoherence channels).
- **Measurement probability checks** (`uniqc/transpiler/compiler.py`): `_originir_to_circuit()` now correctly tracks MEASURE gates with non-contiguous qubit and classical bit registers via a deferred `pending_measurements` buffer, fixing circuits where qubits map to non-zero classical bits.

### Changed

- **`_originir_to_circuit()`** (`uniqc/transpiler/compiler.py`): Refactored to use explicit `QINIT`/`CREG`/`MEASURE` opcode handling and a `pending_measurements` dict instead of regex-based `re.findall`; correctly records `qubit_num`, `cbit_num`, `max_qubit`, and `measure_list`.
- **`compile()` Qiskit import** (`uniqc/transpiler/compiler.py`): `transpile_qasm` is now lazily loaded via `_load_transpile_qasm()` — import is deferred until first `compile()` call, with a clear `CompilationFailedException` pointing to `pip install unified-quantum[qiskit]` when Qiskit is absent.
- **`uniqc/transpiler/__init__.py`**: `plot_time_line` import is now lazy with a silent `None` fallback when matplotlib is unavailable; export style normalised to explicit `as` renaming for all public symbols.

## [0.0.7] - 2026-05-01

### Added

- **Enhanced Transpiler** (`uniqc/transpiler/compiler.py`): New `compile()` function — the canonical chip-aware circuit transpilation entry point for UnifiedQuantum. Wraps Qiskit transpilation with `BackendInfo`/`ChipCharacterization`-aware routing, multiple output formats, and typed `TranspilerConfig`. Supports `output_format="circuit"` (default, returns `Circuit`), `"originir"`, and `"qasm"`. `level` parameter maps directly to Qiskit optimization levels 0–3. `basis_gates` accepts a custom gate set (default: `["cz", "sx", "rz"]`).
- **`TranspilerConfig` dataclass** (`uniqc/transpiler/compiler.py`): Typed configuration object for `compile()`, frozen and hashable. Validates `type` and `level` at construction time.
- **`CompilationResult` dataclass**: Holds compiled output, estimated fidelity, SWAP overhead count, and informational messages from the transpiler pipeline.
- **Fidelity-weighted routing** (`_route_with_fidelity`): Dijkstra-based SWAP insertion that treats each edge weight as `1 - fidelity`, preferring high-fidelity qubit chains. Computes a cumulative circuit fidelity estimate as a by-product.
- **Backend Options hierarchy** (`uniqc/task/options.py`): Typed `BackendOptions` base class with platform-specific subclasses — `OriginQOptions`, `QuafuOptions`, `IBMOptions`, `DummyOptions` — and a `BackendOptionsFactory` for constructing from `**kwargs` dicts or direct instantiation. All fields are validated with sensible defaults; `to_kwargs()` bridges back to the existing adapter `**kwargs` interface.
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

### Changed

- **`submit_task()` / `submit_batch()`** (`uniqc/task_manager.py`): Added optional `options` parameter accepting `BackendOptions | dict | None`. When provided, options are normalised via `BackendOptionsFactory.normalize_options()` and merged with any extra `**kwargs`. Fully backward-compatible — existing `**kwargs`-only calls are unchanged.
- **`uniqc/transpiler/__init__.py`**: Re-exports `compile`, `TranspilerConfig`, and `CompilationResult` from the new `compiler` submodule.
- **`Platform` enum** (`uniqc/backend_info.py`): Added `DUMMY = "dummy"` variant to support the dummy simulator in `BackendOptions`.
- **`submit_task(..., dummy=True)` / `submit_batch(..., dummy=True)`** (`uniqc/task_manager.py`): The `dummy=` parameter is deprecated. Use `backend="dummy"` instead, which now routes through the properly registered `DummyBackend` — no functional change for existing callers, but a `DeprecationWarning` is emitted.
- **`DummyAdapter`** (`uniqc/task/adapters/dummy_adapter.py`): Now accepts `chip_characterization: ChipCharacterization | None` at construction. When provided, automatically derives realistic noise parameters from per-qubit (single-gate fidelity, T1/T2, readout fidelity) and per-pair (two-qubit gate fidelity) calibration data. Readout errors are also injected via the `readout_error` parameter of `OriginIR_NoisySimulator`. Explicit `noise_model` takes precedence over chip-derived noise.

### Fixed

- **`compile(output_format="originir")`**: Was incorrectly returning raw QASM string. Now correctly calls `convert_qasm_to_oir()` before returning.
- **`RegionSelector._backtrack_chain`**: DFS was returning the highest-fidelity path overall instead of the best path of the exact requested length. Added separate `best_exact_path`/`best_exact_fid` tracking so exact-length paths are returned correctly.
- **`RegionSelector._greedy_chain_expand`**: DFS was returning the full longest path even when only `length` qubits were requested. Added truncation to return exactly `length` qubits.
- **`RegionSelector._build_graph`**: Fixed `TypeError` when iterating over `QubitTopology` dataclass edges — changed from tuple unpacking to attribute access (`.u`, `.v`).

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
