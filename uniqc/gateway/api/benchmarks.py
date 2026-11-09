"""Local benchmark API: QV, throughput, and noisy-VM QRAM cases.

All endpoints run real local computation on the package's own simulator
stack (no cloud task is created, no quota consumed).  Inputs are bounded so
a single request cannot pin the gateway for minutes.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class QVRequest(BaseModel):
    """Bounded Quantum Volume run parameters."""

    width: int = Field(default=4, ge=2, le=6, strict=True)
    trials: int = Field(default=20, ge=1, le=100, strict=True)
    shots: int = Field(default=1000, ge=50, le=5000, strict=True)
    seed: int = Field(default=0, ge=0, le=2**31 - 1, strict=True)


class ThroughputRequest(BaseModel):
    """Bounded local compile/execute throughput run parameters."""

    circuits: int = Field(default=200, ge=10, le=2000, strict=True)
    qubits: int = Field(default=8, ge=2, le=16, strict=True)
    depth: int = Field(default=6, ge=1, le=30, strict=True)
    shots: int = Field(default=1000, ge=1, le=5000, strict=True)
    seed: int = Field(default=0, ge=0, le=2**31 - 1, strict=True)
    backend: str = Field(
        default="dummy:local:simulator",
        pattern=r"^dummy:local:(simulator|virtual-line-[1-9][0-9]*|virtual-grid-[1-9][0-9]*x[1-9][0-9]*)$",
    )


class NoiseQRAMRequest(BaseModel):
    """3-layer QRAM / QPU-addressing case on a synthetic noisy VM."""

    case: str = Field(default="lookup", pattern="^(lookup|qpu)$")
    address: int = Field(default=5, ge=0, le=7, strict=True)
    shots: int = Field(default=1000, ge=50, le=5000, strict=True)
    seed: int = Field(default=0, ge=0, le=2**31 - 1, strict=True)
    model_seed: int = Field(default=42, ge=0, le=2**31 - 1, strict=True)


@router.post("/qv")
def quantum_volume(request: QVRequest) -> dict:
    """Run a seeded Quantum Volume benchmark on the local simulator."""
    from uniqc.benchmark import run_quantum_volume

    try:
        result = run_quantum_volume(
            width=request.width,
            trials=request.trials,
            shots=request.shots,
            base_seed=request.seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return result.to_json_dict()


@router.post("/throughput")
def throughput(request: ThroughputRequest) -> dict:
    """Measure local compile/execute throughput (circuits/hour)."""
    from uniqc.benchmark import run_throughput_benchmark

    try:
        result = run_throughput_benchmark(
            circuits=request.circuits,
            n_qubits=request.qubits,
            depth=request.depth,
            shots=request.shots,
            seed=request.seed,
            backend_id=request.backend,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return result.to_json_dict()


@router.post("/noise-qram")
def noise_qram(request: NoiseQRAMRequest) -> dict:
    """Run a 3-layer QRAM case on a synthetic WK_C180-scale noisy VM.

    The exchange model is generated locally (``data_class: synthetic``) with
    the requested seed; hardware-archive models are imported offline via the
    CLI (``uniqc noise import``), not through this endpoint.
    """
    from uniqc.noise_bridge import (
        load_noise_model,
        run_qpu_addressing_case,
        run_qram_lookup_case,
        write_synthetic_model,
    )

    with tempfile.TemporaryDirectory(prefix="uniqc-gw-bench-") as workdir:
        root = Path(workdir)
        try:
            model = load_noise_model(write_synthetic_model(root / "model.json", num_qubits=5, seed=request.model_seed))
            common = {"shots": request.shots, "seed": request.seed, "workdir": root / "cal"}
            if request.case == "lookup":
                report = run_qram_lookup_case(model, address=request.address, **common)
            else:
                report = run_qpu_addressing_case(model, **common)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
    report["boundary"] = (
        "Local density-operator simulation with synthetic WK_C180-scale channels; "
        "not a real-hardware validation; no cloud task submitted."
    )
    return report
