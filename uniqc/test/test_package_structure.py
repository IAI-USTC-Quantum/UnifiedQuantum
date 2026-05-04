from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "uniqc"

ALLOWED_TOP_LEVEL_FILES = {
    "__init__.py",
    "_version.py",
    "config.py",
    "exceptions.py",
}

ALLOWED_TOP_LEVEL_PACKAGES = {
    "algorithms",
    "backend_adapter",
    "calibration",
    "circuit_builder",
    "cli",
    "compile",
    "gateway",
    "qem",
    "simulator",
    "test",
    "torch_adapter",
    "utils",
    "visualization",
}


def test_uniqc_root_contains_only_package_boundary_files() -> None:
    python_files = {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_file() and path.suffix == ".py"
    }

    assert python_files == ALLOWED_TOP_LEVEL_FILES


def test_uniqc_top_level_packages_match_architecture() -> None:
    packages = {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    }

    assert packages == ALLOWED_TOP_LEVEL_PACKAGES


def test_common_user_imports_are_flat() -> None:
    import uniqc.backend_adapter.config as backend_adapter_config
    from uniqc import (
        BackendInfo,
        Circuit,
        Platform,
        QuantumLayer,
        RegionSelector,
        calculate_expectation,
        compile,
        config,
        qft_circuit,
        submit_task,
    )

    assert Circuit is not None
    assert compile is not None
    assert submit_task is not None
    assert BackendInfo is not None
    assert Platform is not None
    assert RegionSelector is not None
    assert calculate_expectation is not None
    assert qft_circuit is not None
    assert QuantumLayer is not None
    assert config is not None
    assert hasattr(config, "load_originq_config")
    assert hasattr(backend_adapter_config, "get_platform_config")
