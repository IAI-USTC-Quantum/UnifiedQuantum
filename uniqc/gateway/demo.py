"""Local demonstration composition; delegate execution to the existing CLI path."""

from __future__ import annotations

import math
import time
from typing import Literal

from pydantic import BaseModel, Field


class DemoRequest(BaseModel):
    """Bounded presets for the local product demonstration."""

    case: Literal["ghz", "w", "ramsey"] = "ghz"
    qubits: int = Field(default=4, ge=2, le=8, strict=True)
    phase: float = Field(default=math.pi / 2, ge=-2 * math.pi, le=2 * math.pi, allow_inf_nan=False)


def run_demo(request: DemoRequest) -> dict:
    """Build standard circuit fragments and run the unchanged native simulator."""
    from uniqc import Circuit, ghz_state, w_state
    from uniqc.cli.simulate import _run_simulation

    start = time.perf_counter()
    if request.case == "ghz":
        circuit = ghz_state(request.qubits)
    elif request.case == "w":
        circuit = w_state(request.qubits)
    else:
        circuit = Circuit()
        for qubit in range(request.qubits):
            circuit.h(qubit)
            circuit.rz(qubit, request.phase)
            circuit.h(qubit)
    # Fragment builders leave measurement to their caller. The existing CLI
    # reports the explicitly requested measurement marginal, so request all bits.
    for qubit in range(request.qubits):
        circuit.measure(qubit)
    originir = circuit.to_originir()
    probabilities = _run_simulation(originir, "statevector", 1024)
    expected = {}
    for index in range(1 << request.qubits):
        bits = format(index, f"0{request.qubits}b")
        ones = bits.count("1")
        if request.case == "ghz":
            expected[bits] = 0.5 if index in (0, (1 << request.qubits) - 1) else 0.0
        elif request.case == "w":
            expected[bits] = 1 / request.qubits if ones == 1 else 0.0
        else:
            one = math.sin(request.phase / 2) ** 2
            expected[bits] = one ** ones * (1 - one) ** (request.qubits - ones)
    return {"schema": "uniqc.local-demo.v1", "input": request.model_dump(),
            "execution": "native statevector; exact probabilities, no shot sampling",
            "bit_order": "rightmost bit is q[0]", "originir": originir,
            "probabilities": probabilities, "probability_sum": sum(probabilities.values()),
            "max_probability_error": max(abs(probabilities.get(k, 0) - p) for k, p in expected.items()),
            "wall_seconds": time.perf_counter() - start}
