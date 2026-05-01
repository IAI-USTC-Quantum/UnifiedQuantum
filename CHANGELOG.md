# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
