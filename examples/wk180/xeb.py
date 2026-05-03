#!/usr/bin/env python
"""WK180 XEB benchmark example for UnifiedQuantum.

This example demonstrates running XEB (cross-entropy benchmarking) on the
WK180 quantum processor from OriginQ.

Usage:
    # Dummy mode (local noisy simulation using WK180 chip characterization)
    python examples/wk180/xeb.py --dummy --qubits 0 1 2

    # Real machine (requires UNIQC_ORIGINQ_TOKEN env var)
    python examples/wk180/xeb.py --backend originq:wuyuan:wk180 --qubits 0 1 2

    # 2-qubit XEB
    python examples/wk180/xeb.py --dummy --qubits 0 1 --type 2q --depths 5 10 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "UnifiedQuantum"))


def _get_wk180_backend(dummy: bool, backend_name: str | None) -> tuple:
    """Get adapter and chip characterization for WK180."""
    from uniqc.backend_adapter.task.adapters import DummyAdapter, OriginQAdapter

    if dummy:
        # Fetch WK180 chip characterization from OriginQ cloud, then use DummyAdapter
        originq = OriginQAdapter()
        chip_char = originq.get_chip_characterization(backend_name or "originq:wuyuan:wk180")
        adapter = DummyAdapter(chip_characterization=chip_char)
        return adapter, chip_char
    else:
        # Use OriginQAdapter directly for real-machine execution
        adapter = OriginQAdapter(backend_name=backend_name or "WK_C180")
        chip_char = adapter.get_chip_characterization(backend_name or "originq:wuyuan:wk180")
        return adapter, chip_char


def run_wk180_xeb(
    dummy: bool = True,
    qubits: list[int] | None = None,
    xeb_type: str = "both",
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    max_age_hours: float = 24.0,
    output_file: str | None = None,
    backend_name: str | None = None,
    use_readout_em: bool = True,
) -> dict:
    """Run XEB on WK180.

    Args:
        dummy: If True, use local noisy simulation; if False, use real hardware.
        qubits: Qubit indices. Defaults to [0, 1, 2, 3].
        xeb_type: "1q", "2q", or "both".
        depths: Circuit depths. Defaults to [5, 10, 20, 50].
        n_circuits: Circuits per depth.
        shots: Shots per circuit.
        max_age_hours: Max calibration data age for readout EM.
        output_file: If provided, save results to this JSON file.
        backend_name: OriginQ backend name (e.g. "originq:wuyuan:wk180").
        use_readout_em: Apply readout EM before fidelity computation.

    Returns:
        Dict with all XEB results.
    """
    from uniqc import xeb_workflow

    if depths is None:
        depths = [5, 10, 20, 50]
    if qubits is None:
        qubits = [0, 1, 2, 3]

    adapter, chip_char = _get_wk180_backend(dummy, backend_name)
    if dummy:
        backend_label = "dummy"
    elif backend_name is not None:
        backend_label = backend_name
    elif chip_char is not None:
        backend_label = f"originq:{chip_char.chip_name}"
    else:
        backend_label = "originq:WK_C180"

    results: dict = {}

    if xeb_type in ("1q", "both"):
        print(f"[WK180] Running 1q XEB on qubits {qubits}...")
        results["1q"] = xeb_workflow.run_1q_xeb_workflow(
            backend=backend_label,
            qubits=qubits,
            depths=depths,
            n_circuits=n_circuits,
            shots=shots,
            use_readout_em=use_readout_em,
            max_age_hours=max_age_hours,
            chip_characterization=chip_char,
        )
        for q, r in results["1q"].items():
            print(f"  Qubit {q}: r={r.fidelity_per_layer:.5f} ± {r.fidelity_std_error:.5f}")

    if xeb_type in ("2q", "both"):
        # Use connected pairs from chip topology
        edges = [(e.u, e.v) for e in chip_char.connectivity]
        if qubits:
            target = set(qubits)
            edges = [(u, v) for u, v in edges if u in target and v in target]
        if not edges:
            print("  No edges found in topology for 2q XEB.")
        else:
            print(f"[WK180] Running 2q XEB on pairs {edges}...")
            # Build entangler gate map
            entangler_gates = {}
            for tq_data in chip_char.two_qubit_data:
                u, v = tq_data.qubit_u, tq_data.qubit_v
                best_gate, best_fid = "CNOT", -1.0
                for g in tq_data.gates:
                    if g.fidelity is not None and g.fidelity > best_fid:
                        best_fid = g.fidelity
                        best_gate = g.gate.upper()
                for pair in [(u, v), (v, u)]:
                    if pair in edges:
                        entangler_gates[pair] = best_gate

            results["2q"] = xeb_workflow.run_2q_xeb_workflow(
                backend=backend_label,
                pairs=edges,
                depths=depths,
                n_circuits=n_circuits,
                shots=shots,
                use_readout_em=use_readout_em,
                max_age_hours=max_age_hours,
                chip_characterization=chip_char,
                entangler_gates=entangler_gates,
            )
            for pair, r in results["2q"].items():
                print(f"  Pair {pair}: r={r.fidelity_per_layer:.5f} ± {r.fidelity_std_error:.5f}")

    # Save results
    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = _make_serializable(results)
        with open(out_path, "w") as f:
            json.dump(serializable, f, indent=2)
        print(f"[WK180] Results saved to {out_path}")

    return results


def _make_serializable(results: dict) -> dict:
    """Convert XEBResult objects to JSON-serializable dicts."""
    out = {}
    for key, val in results.items():
        if hasattr(val, "to_dict"):
            out[key] = val.to_dict()
        elif isinstance(val, dict):
            out[key] = {str(k): v.to_dict() if hasattr(v, "to_dict") else v for k, v in val.items()}
        else:
            out[key] = val
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="WK180 XEB benchmark")
    parser.add_argument("--dummy", action="store_true", help="Use dummy mode (local simulation)")
    parser.add_argument("--backend", type=str, default=None, help="OriginQ backend name")
    parser.add_argument("--qubits", type=int, nargs="+", default=None, help="Qubit indices")
    parser.add_argument("--type", choices=["1q", "2q", "both"], default="both", dest="xeb_type")
    parser.add_argument("--depths", type=int, nargs="+", default=None)
    parser.add_argument("--n-circuits", type=int, default=50, dest="n_circuits")
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--no-readout-em", action="store_true", dest="no_readout_em")
    parser.add_argument("--max-age-hours", type=float, default=24.0, dest="max_age_hours")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    try:
        run_wk180_xeb(
            dummy=args.dummy,
            qubits=args.qubits,
            xeb_type=args.xeb_type,
            depths=args.depths,
            n_circuits=args.n_circuits,
            shots=args.shots,
            max_age_hours=args.max_age_hours,
            output_file=args.output,
            backend_name=args.backend,
            use_readout_em=not args.no_readout_em,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
