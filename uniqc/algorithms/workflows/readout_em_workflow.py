"""High-level readout EM workflow.

Chip-agnostic: runs readout calibration and returns a ready-to-use ReadoutEM instance.
For WK180-specific usage, see ``examples/wk180/readout_em.py``.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "run_readout_em_workflow",
    "apply_readout_em",
]


def _get_adapter(backend: str, **kwargs) -> Any:
    """Get a QuantumAdapter for the given backend name.

    Args:
        backend: Backend identifier, e.g. "dummy", "originq:PQPUMESH8".
            For OriginQ backends the chip name (after "originq:") is extracted
            and passed as ``backend_name`` to ``OriginQAdapter``.
    """
    from uniqc.backend_adapter.task.adapters import (
        DummyAdapter,
        OriginQAdapter,
        QuafuAdapter,
    )

    if backend == "dummy" or backend.startswith("dummy:"):
        from uniqc.backend_adapter.dummy_backend import dummy_adapter_kwargs

        return DummyAdapter(**dummy_adapter_kwargs(backend, **kwargs))
    elif backend.startswith("origin"):
        # Extract chip name: "originq:PQPUMESH8" → "PQPUMESH8"
        chip = backend.split(":", 1)[1] if ":" in backend else backend
        return OriginQAdapter(backend_name=chip, **kwargs)
    elif backend.startswith("quafu"):
        return QuafuAdapter(**kwargs)
    else:
        return DummyAdapter(**kwargs)


def run_readout_em_workflow(
    backend: str = "dummy",
    qubits: list[int] | None = None,
    pairs: list[tuple[int, int]] | None = None,
    shots: int = 1000,
    max_age_hours: float = 24.0,
    chip_characterization: Any = None,
) -> Any:
    """Run readout calibration and return a ready-to-use ReadoutEM instance.

    This function:
    1. Creates an adapter for the given backend
    2. Runs 1q and/or 2q readout calibration
    3. Returns a ``ReadoutEM`` instance ready for applying mitigation

    Args:
        backend: Backend name (e.g. "dummy", "originq:wuyuan:wk180").
        qubits: List of qubit indices for 1q calibration.
        pairs: List of (u, v) qubit pairs for 2q calibration.
        shots: Number of shots per calibration circuit.
        max_age_hours: Maximum acceptable age of existing calibration data.
        chip_characterization: Optional ChipCharacterization.

    Returns:
        A ``ReadoutEM`` instance. Calibration results are saved to
        ``~/.uniqc/calibration_cache/`` and loaded automatically.
    """
    from uniqc.calibration.readout import ReadoutCalibrator
    from uniqc.qem import ReadoutEM

    adapter_kwargs: dict[str, Any] = {}
    if chip_characterization is not None:
        adapter_kwargs["chip_characterization"] = chip_characterization

    adapter = _get_adapter(backend, **adapter_kwargs)

    # Run calibration
    calibrator = ReadoutCalibrator(adapter=adapter, shots=shots)

    if qubits:
        calibrator.calibrate_qubits(qubits)
    if pairs:
        calibrator.calibrate_pairs(pairs)

    # Return a ReadoutEM instance for applying mitigation
    return ReadoutEM(
        adapter=adapter,
        max_age_hours=max_age_hours,
        shots=shots,
    )


def apply_readout_em(
    result: Any,
    readout_em: Any,
    measured_qubits: list[int],
) -> dict[int, float]:
    """Apply readout EM to a UnifiedResult's counts.

    Args:
        result: A ``UnifiedResult`` or result dict with a ``counts`` field.
        readout_em: A ``ReadoutEM`` instance.
        measured_qubits: List of qubit indices that were measured.

    Returns:
        Dict mapping outcome → corrected probability.
    """
    # Extract counts from result
    if hasattr(result, "counts"):
        counts = result.counts
    elif isinstance(result, dict):
        counts = result.get("counts", result.get("result", {}).get("counts", {}))
    else:
        raise TypeError(f"Unsupported result type: {type(result)}")

    if isinstance(counts, dict) and counts and isinstance(next(iter(counts)), str):
        counts = {int(k): v for k, v in counts.items()}

    corrected_counts = readout_em.mitigate_counts(counts, measured_qubits)
    total = sum(corrected_counts.values())
    if total > 0:
        return {k: v / total for k, v in corrected_counts.items()}
    return corrected_counts
