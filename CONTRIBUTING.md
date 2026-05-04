# Contributing to UnifiedQuantum

Thank you for your interest in contributing to UnifiedQuantum! This document outlines how you can get involved and help improve the project.

## Environment Setup

UnifiedQuantum currently recommends [uv](https://github.com/astral-sh/uv) for dependency
management in local development. Maintainers and contributors should prefer `uv sync`
to create/update the development environment and `uv run ...` to execute tools inside
that environment. Pip commands are kept below only as a fallback for environments where
uv cannot be used.

### Prerequisites

- Python 3.10 – 3.13
- [uv](https://github.com/astral-sh/uv) (recommended package manager — install via `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Git
- CMake >= 3.22 (C++ backend build — see [CMake Requirement](#cmake-requirement) below)
- C++ compiler with C++17 support (e.g. `g++` >= 8, `clang++` >= 10)
- pybind11 is installed from PyPI as a build dependency declared in `pyproject.toml`

### Clone & Install

```bash
git clone --recurse-submodules https://github.com/IAI-USTC-Quantum/UnifiedQuantum.git
cd UnifiedQuantum
```

#### Recommended: Full Development Environment with uv

Use uv to install the editable project, all optional dependencies, and the development
and documentation dependency groups:

```bash
uv sync --all-extras --group dev --group docs
```

This creates or updates `.venv` and installs the package in **editable mode** with:
- The C++ simulation backend (`uniqc_cpp`) compiled via pybind11/CMake
- All optional dependencies (Qiskit, Quafu, IBM Runtime, visualization tools, etc.)
- Development tools (pytest, ruff, pre-commit)

Run project commands through uv so they use the managed environment:

```bash
uv run pytest uniqc/test
uv run ruff check .
uv run ruff format .
uv run pre-commit run --all-files
```

#### CMake Requirement

The C++ backend requires CMake >= 3.22. On systems with an older CMake, install a newer version via pip:

```bash
pip install cmake --upgrade
```

The newer cmake is installed to `~/.local/bin/` or your Python bin directory — make sure it comes first in `PATH` before the system cmake.

#### Without uv (pip only fallback)

```bash
pip install cmake --upgrade
pip install -e ".[all]"
```

### Install pre-commit hooks

```bash
pre-commit install
```

## Branch Naming

Use descriptive prefix branches:

| Prefix | Use case |
|--------|----------|
| `feat/<description>` | New features |
| `fix/<description>` | Bug fixes |
| `ci/<description>` | CI/CD changes |
| `docs/<description>` | Documentation updates |
| `refactor/<description>` | Code refactoring (no behavior change) |

Examples: `feat/add-noise-simulator`, `fix/gate-depth-calculation`

## Commit Message Format

We recommend [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**

- `feat` – new feature
- `fix` – bug fix
- `docs` – documentation only
- `style` – formatting, missing semicolons, etc. (no code change)
- `refactor` – code change that neither fixes a bug nor adds a feature
- `test` – adding or correcting tests
- `ci` – CI/CD configuration

**Examples:**

```
feat(simulator): add depolarizing noise model
fix(circuit): correct gate decomposition order
docs(api): clarify Measure result return type
ci: add coverage reporting to GitHub Actions
```

## Development Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** — write code, add tests, update docs.

3. **Run checks locally** before pushing:
   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run pytest uniqc/test
   uv run pre-commit run --all-files
   ```

4. **Commit** your changes with a clear message.

5. **Push** and open a Pull Request:
   ```bash
   git push -u origin feat/your-feature-name
   ```

## Pull Request Process

1. Open a PR against `main` with a clear title and description.
2. Fill in the PR template (if one exists).
3. Ensure all CI checks pass.
4. Request a review from a maintainer.
5. Once approved, a maintainer will merge your PR.

## Release Notes Maintenance

If your change is expected to affect users, please update the release-notes page in the same PR.

Typical examples include:

- user-visible CLI changes
- package rename or import-path changes
- behavior changes that may affect existing scripts
- storage, task, or result format adjustments
- compatibility changes and migration-related notes

Please update:

- `docs/source/releases/index.md` for the user-facing summary
- the release-history generator inputs indirectly through clear commit titles and tag messages

## Before Tagging a Release

Before creating a new `v*` tag, maintainers should quickly review the release-notes page and make sure:

1. Re-run the best-practices notebooks with `python scripts/generate_best_practice_notebooks.py` and review the executed outputs and figures.
2. Confirm the best-practices coverage matrix still matches the supported user paths: config, backend cache, bare/named circuits, API/CLI submission, dummy or virtual backends, visualization, variational circuits, Torch integration, calibration, and QEM.
3. Check `CHANGELOG.md` and make sure the `[Unreleased]` section is accurate.
4. Check `docs/source/releases/index.md` and make sure it reflects the main user-visible changes in the upcoming release.
5. Confirm the generated release history is correct by building the docs or running `scripts/generate_release_notes.py`.
6. Ensure recent commits and tag messages are clear enough for the generated version record.
7. Mention any rename, migration, compatibility change, or incomplete real-cloud verification explicitly.
8. Build the docs site successfully with the updated release-notes and best-practices notebook content.

The best-practices notebooks are a release-time verifiable path check, not CI.
They should stay small enough to run locally, but complete enough to show users a
working path from configuration through execution and result interpretation.

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix and format
uv run ruff format .
```

Run these before committing. The pre-commit hook will also run them automatically.

## Testing

Run the test suite with [pytest](https://pytest.org/):

```bash
uv run pytest uniqc/test
```

The project uses [GitHub Actions](https://github.com/IAI-USTC-Quantum/UnifiedQuantum/actions) for CI. If you encounter test failures, please open an issue.

## Questions?

If you have questions or need help, feel free to open an issue for discussion.
