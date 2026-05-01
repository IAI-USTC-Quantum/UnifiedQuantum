# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow

The `main` branch is protected — never push directly to it. Always:

1. Create a feature branch from `main`
2. Commit changes and push to the remote branch
3. Open a pull request targeting `main`
4. Wait for review and approval before merging

## Project Overview

UnifiedQuantum is a Python-native quantum programming framework for NISQ devices. It provides circuit construction, simulation (local and cloud), and result analysis. The core includes a C++ simulation backend compiled via pybind11.

## Build Commands

**Requirements:** Python 3.10–3.13, git with submodules, CMake >= 3.26, C++17 compiler.

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum
```

### Recommended: Full development environment

```bash
uv tool install -e ".[all]"
```

This installs in **editable mode** with:
- The C++ simulation backend (`uniqc_cpp`) compiled via pybind11/CMake
- All optional dependencies (Qiskit, Quafu, IBM Runtime, pandas, etc.)
- Development tools (pytest, ruff, pre-commit)

This is the default/recommended command for active development. All tests (including those requiring `uniqc_cpp`) run normally.

### CMake Requirement

The C++ backend requires CMake >= 3.26. On systems with an older CMake (e.g. Ubuntu 22.04 ships cmake 3.22), install a newer version via pip:

```bash
pip install cmake --upgrade
```

The newer cmake is installed to `~/.local/bin/` or your Python bin directory — make sure it comes first in `PATH` before the system cmake.

### Without uv

```bash
pip install cmake --upgrade
pip install -e ".[all]"
```

## Testing

```bash
# All tests
pytest uniqc/test/ -v

# Single test file
pytest uniqc/test/test_simulator.py -v

# Single test function
pytest uniqc/test/test_simulator.py -v -k "test_function_name"
```

Test files follow `test_*.py` naming. Test classes: `Test*` or `RunTest*`. Test functions: `test_*` or `run_test_*`.

## Linting & Formatting

```bash
ruff check .          # lint
ruff format .         # format
ruff check . --fix    # auto-fix lint issues
```

Ruff config: line length 120, target Python 3.10. Rules: E, F, W, I, N, UP, B, C4, SIM. E501 and physics naming conventions (N801/N803/N806) are intentionally ignored.

Pre-commit hooks are configured (ruff lint + format, YAML check, trailing whitespace).

## Architecture

### Core Flow: Circuit -> Simulator/Backend -> Result

1. **Circuit Builder** (`uniqc/circuit_builder/`): The `Circuit` class provides a fluent API for constructing quantum circuits. It outputs OriginIR or OpenQASM 2.0 format strings. Gate definitions live in `opcode.py` (logical gate list), `originir_spec.py` (OriginIR gate syntax), and `qasm_spec.py` (QASM gate syntax).

2. **Simulators** (`uniqc/simulator/`): Local simulation backends that consume OriginIR or QASM strings.
   - `OriginIR_Simulator` — primary simulator supporting statevector, density matrix, and noisy simulation
   - `QASM_Simulator` — OpenQASM 2.0 simulator
   - `uniqc_cpp` — C++ extension (pybind11)

3. **Parsers** (`uniqc/originir/`, `uniqc/qasm/`): Parse OriginIR and OpenQASM 2.0 assembly strings into structured representations.

4. **Cloud Task Submission** (`uniqc/task/`): Adapter pattern for submitting circuits to quantum cloud platforms. Each provider (OriginQ, Quafu, IBM) has an adapter under `task/adapters/`. Configuration is via environment variables. The `task_manager` module provides a unified API (`submit_task`, `query_task`, `wait_for_result`).

   **Dry-run validation**: Every adapter implements `dry_run(originir, shots, **kwargs)` which validates the circuit offline — no cloud API calls are made. Use `uniqc submit --dry-run` in the CLI or `dry_run_task()` in Python to check circuit compatibility before submitting. If a dry-run succeeds but the actual submission fails, that is a **critical bug**.

5. **Transpiler** (`uniqc/transpiler/`): Converts between Qiskit circuits and OriginIR format.

6. **Analyzer** (`uniqc/analyzer/`): Post-processing tools for measurement results — expectation values, measurement tomography, state tomography, etc.

### C++ Backend

`UniqcCpp/` contains the C++ simulation backend compiled as a pybind11 extension (`uniqc_cpp`). Dependencies (pybind11 v2.13.6, fmt) are git submodules under `UniqcCpp/Thirdparty/`. The `CMakeExtension` class in `setup.py` handles CMake-based compilation.

## Releasing

The package version is automatically managed by [setuptools_scm](https://setuptools-scm.readthedocs.io/), which extracts the version from git tags. The version is determined at build time from the latest git tag matching `v*`.

To release a new version:

1. Ensure all changes are committed and merged to `main`
2. Tag the release: `git tag vX.Y.Z` (the tag **must start with `v`**)
3. Push the tag: `git push origin --tags`

Pushing a `v*` tag triggers `pypi-publish.yml`, which builds wheels (Linux manylinux + Windows, Python 3.10–3.13) with the C++ extension via `cibuildwheel` and publishes them to PyPI using Trusted Publishing (OIDC). No manual version bump is needed — the version is automatically extracted from the git tag.
