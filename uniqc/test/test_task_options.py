"""Tests for the BackendOptions class hierarchy."""

from __future__ import annotations

import pytest

from uniqc.backend_adapter.backend_info import Platform
from uniqc.backend_adapter.task.options import (
    BackendOptionsError,
    BackendOptionsFactory,
    DummyOptions,
    IBMOptions,
    OriginQOptions,
    QuafuOptions,
    QuarkOptions,
)


class TestOriginQOptions:
    """Tests for OriginQOptions."""

    def test_defaults(self):
        opts = OriginQOptions()
        assert opts.platform == Platform.ORIGINQ
        assert opts.backend_name == "origin:wuyuan:d5"
        assert opts.circuit_optimize is True
        assert opts.measurement_amend is False
        assert opts.auto_mapping is False
        assert opts.shots == 1000

    def test_to_kwargs(self):
        opts = OriginQOptions(
            backend_name="origin:wuyuan:d6",
            circuit_optimize=False,
            measurement_amend=True,
            auto_mapping=True,
            shots=2000,
        )
        kwargs = opts.to_kwargs()
        assert kwargs["backend_name"] == "origin:wuyuan:d6"
        assert kwargs["circuit_optimize"] is False
        assert kwargs["measurement_amend"] is True
        assert kwargs["auto_mapping"] is True

    def test_shots_not_in_to_kwargs(self):
        """shots is a BackendOptions field, not adapter kwargs."""
        opts = OriginQOptions(shots=500)
        kwargs = opts.to_kwargs()
        assert "shots" not in kwargs


class TestQuafuOptions:
    """Tests for QuafuOptions."""

    def test_defaults(self):
        opts = QuafuOptions()
        assert opts.platform == Platform.QUAFU
        assert opts.chip_id == "ScQ-P18"
        assert opts.auto_mapping is True
        assert opts.task_name is None
        assert opts.group_name is None
        assert opts.wait is False

    def test_to_kwargs(self):
        opts = QuafuOptions(
            chip_id="ScQ-P10",
            auto_mapping=False,
            task_name="my-task",
            group_name="my-group",
            wait=True,
        )
        kwargs = opts.to_kwargs()
        assert kwargs["chip_id"] == "ScQ-P10"
        assert kwargs["auto_mapping"] is False
        assert kwargs["task_name"] == "my-task"
        assert kwargs["group_name"] == "my-group"
        assert kwargs["wait"] is True

    def test_optional_fields_omitted_when_none(self):
        """Optional fields not included when None."""
        opts = QuafuOptions()
        kwargs = opts.to_kwargs()
        assert "task_name" not in kwargs
        assert "group_name" not in kwargs
        assert "wait" not in kwargs


class TestIBMOptions:
    """Tests for IBMOptions."""

    def test_defaults(self):
        opts = IBMOptions()
        assert opts.platform == Platform.IBM
        assert opts.chip_id is None
        assert opts.auto_mapping is True
        assert opts.circuit_optimize is True
        assert opts.task_name is None

    def test_to_kwargs(self):
        opts = IBMOptions(
            chip_id="ibm_kyoto",
            auto_mapping=False,
            circuit_optimize=False,
            task_name="ibm-task",
        )
        kwargs = opts.to_kwargs()
        assert kwargs["chip_id"] == "ibm_kyoto"
        assert kwargs["auto_mapping"] is False
        assert kwargs["circuit_optimize"] is False
        assert kwargs["task_name"] == "ibm-task"


class TestQuarkOptions:
    """Tests for QuarkOptions."""

    def test_defaults(self):
        opts = QuarkOptions()
        assert opts.platform == Platform.QUARK
        assert opts.chip_id == "Baihua"
        assert opts.task_name is None
        assert opts.compile is True
        assert opts.compiler is None

    def test_to_kwargs(self):
        opts = QuarkOptions(
            chip_id="Dongling",
            task_name="quark-task",
            compile=False,
            compiler="qiskit",
            correct=True,
            open_dd="XY4",
            target_qubits=[0, 1],
        )
        kwargs = opts.to_kwargs()
        assert kwargs["chip_id"] == "Dongling"
        assert kwargs["task_name"] == "quark-task"
        assert kwargs["compile"] is False
        assert kwargs["compiler"] == "qiskit"
        assert kwargs["correct"] is True
        assert kwargs["open_dd"] == "XY4"
        assert kwargs["target_qubits"] == [0, 1]


class TestDummyOptions:
    """Tests for DummyOptions."""

    def test_defaults(self):
        opts = DummyOptions()
        assert opts.platform == Platform.DUMMY
        assert opts.noise_model is None
        assert opts.available_qubits == 16
        assert opts.available_topology is None

    def test_to_kwargs(self):
        opts = DummyOptions(available_qubits=8, available_topology=[[0, 1], [1, 2]])
        kwargs = opts.to_kwargs()
        assert kwargs["available_qubits"] == 8
        assert kwargs["available_topology"] == [[0, 1], [1, 2]]


class TestBackendOptionsFactory:
    """Tests for BackendOptionsFactory."""

    def test_from_kwargs_originq(self):
        opts = BackendOptionsFactory.from_kwargs("originq", {"backend_name": "origin:wuyuan:d6"})
        assert isinstance(opts, OriginQOptions)
        assert opts.backend_name == "origin:wuyuan:d6"

    def test_from_kwargs_quafu(self):
        opts = BackendOptionsFactory.from_kwargs("quafu", {"chip_id": "ScQ-P10"})
        assert isinstance(opts, QuafuOptions)
        assert opts.chip_id == "ScQ-P10"

    def test_from_kwargs_ibm(self):
        opts = BackendOptionsFactory.from_kwargs("ibm", {})
        assert isinstance(opts, IBMOptions)
        assert opts.chip_id is None

    def test_from_kwargs_quark(self):
        opts = BackendOptionsFactory.from_kwargs("quark", {"backend_name": "Baihua", "compiler": "qiskit"})
        assert isinstance(opts, QuarkOptions)
        assert opts.chip_id == "Baihua"
        assert opts.compiler == "qiskit"

    def test_from_kwargs_dummy(self):
        opts = BackendOptionsFactory.from_kwargs("dummy", {"available_qubits": 8})
        assert isinstance(opts, DummyOptions)
        assert opts.available_qubits == 8

    def test_from_kwargs_unknown_platform(self):
        with pytest.raises(BackendOptionsError) as exc_info:
            BackendOptionsFactory.from_kwargs("unknown", {})
        assert "unknown" in str(exc_info.value)

    def test_from_kwargs_case_insensitive(self):
        opts = BackendOptionsFactory.from_kwargs("ORIGINQ", {})
        assert isinstance(opts, OriginQOptions)

    def test_create_default(self):
        opts = BackendOptionsFactory.create_default("originq")
        assert isinstance(opts, OriginQOptions)
        assert opts.backend_name == "origin:wuyuan:d5"

    def test_create_default_quark(self):
        opts = BackendOptionsFactory.create_default("quark")
        assert isinstance(opts, QuarkOptions)
        assert opts.chip_id == "Baihua"

    def test_normalize_options_with_none(self):
        opts = BackendOptionsFactory.normalize_options(None, "quafu")
        assert isinstance(opts, QuafuOptions)

    def test_normalize_options_with_instance(self):
        original = QuafuOptions(chip_id="ScQ-P10")
        opts = BackendOptionsFactory.normalize_options(original, "quafu")
        assert opts is original
        assert opts.chip_id == "ScQ-P10"

    def test_normalize_options_with_dict(self):
        opts = BackendOptionsFactory.normalize_options({"backend_name": "origin:wuyuan:d6"}, "originq")
        assert isinstance(opts, OriginQOptions)
        assert opts.backend_name == "origin:wuyuan:d6"

    def test_normalize_options_invalid_type(self):
        with pytest.raises(BackendOptionsError):
            BackendOptionsFactory.normalize_options("not an options object", "originq")

    def test_shots_extracted_from_kwargs(self):
        opts = BackendOptionsFactory.from_kwargs("originq", {"shots": 500, "backend_name": "x"})
        assert opts.shots == 500
        # shots should not appear in to_kwargs
        assert "shots" not in opts.to_kwargs()
