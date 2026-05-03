#!/usr/bin/env python
"""WK180 readout EM example for UnifiedQuantum.

This example demonstrates calibrating and applying readout error mitigation
on the WK180 quantum processor from OriginQ.

Usage:
    # Dummy mode
    python examples/wk180/readout_em.py --dummy --qubits 0 1 2

    # Real machine
    python examples/wk180/readout_em.py --backend originq:wuyuan:wk180 --qubits 0 1 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "UnifiedQuantum"))


def _get_wk180_adapter(dummy: bool, backend_name: str | None):
    """Get adapter and chip characterization for WK180."""
    from uniqc.backend_adapter.task.adapters import DummyAdapter, OriginQAdapter

    if dummy:
        originq = OriginQAdapter()
        chip_char = originq.get_chip_characterization(backend_name or "originq:wuyuan:wk180")
        adapter = DummyAdapter(chip_characterization=chip_char)
        return adapter, chip_char
    else:
        adapter = OriginQAdapter()
        chip_char = adapter.get_chip_characterization(backend_name or "originq:wuyuan:wk180")
        return adapter, chip_char


def run_wk180_readout_em(
    dummy: bool = True,
    qubits: list[int] | None = None,
    pairs: list[tuple[int, int]] | None = None,
    max_age_hours: float = 24.0,
    shots: int = 1000,
    backend_name: str | None = None,
    output_file: str | None = None,
) -> dict:
    """Run readout EM calibration on WK180.

    Args:
        dummy: Use local noisy simulation if True, real hardware if False.
        qubits: Qubit indices for 1q calibration.
        pairs: Qubit pairs for 2q calibration.
        max_age_hours: Maximum acceptable age of cached calibration data.
        shots: Number of shots per calibration circuit.
        backend_name: OriginQ backend name.
        output_file: If provided, save results to this JSON file.

    Returns:
        Dict with calibration results.
    """
    from uniqc import readout_em_workflow

    if qubits is None:
        qubits = [0, 1, 2, 3]

    adapter, chip_char = _get_wk180_adapter(dummy, backend_name)
    backend_label = "dummy" if dummy else (backend_name or "originq:wuyuan:wk180")

    print(f"[WK180] Running readout EM calibration on {backend_label}...")
    print(f"  1q qubits: {qubits}")
    print(f"  2q pairs: {pairs}")

    readout_em = readout_em_workflow.run_readout_em_workflow(
        backend=backend_label,
        qubits=qubits,
        pairs=pairs,
        shots=shots,
        max_age_hours=max_age_hours,
        chip_characterization=chip_char,
    )

    # Report calibration quality
    print("[WK180] Calibration complete. Assignment fidelities:")

    from uniqc.calibration.results import find_cached_results

    for q in qubits:
        paths = find_cached_results(
            backend_label, "readout_1q", max_age_hours=max_age_hours
        )
        q_paths = [p for p in paths if f"_q{q}_" in p.name]
        if q_paths:
            import json

            with open(q_paths[-1]) as f:
                d = json.load(f)
            print(f"  Qubit {q}: assignment fidelity = {d['assignment_fidelity']:.5f}")

    if pairs:
        for pu, pv in pairs:
            paths = find_cached_results(
                backend_label, "readout_2q", max_age_hours=max_age_hours
            )
            pair_paths = [p for p in paths if f"pair-{pu}-{pv}" in p.name or f"pair-{pv}-{pu}" in p.name]
            if pair_paths:
                import json

                with open(pair_paths[-1]) as f:
                    d = json.load(f)
                print(f"  Pair ({pu},{pv}): assignment fidelity = {d['assignment_fidelity']:.5f}")

    if output_file:
        from uniqc.calibration.results import find_cached_results

        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        all_results = {}
        for q in qubits:
            paths = [p for p in find_cached_results(backend_label, "readout_1q")
                     if f"_q{q}_" in p.name]
            if paths:
                import json

                with open(paths[-1]) as f:
                    all_results[f"1q_q{q}"] = json.load(f)
        for pu, pv in (pairs or []):
            paths = [p for p in find_cached_results(backend_label, "readout_2q")
                     if f"pair-{pu}-{pv}" in p.name or f"pair-{pv}-{pu}" in p.name]
            if paths:
                import json

                with open(paths[-1]) as f:
                    all_results[f"2q_{pu}_{pv}"] = json.load(f)
        with open(out_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"[WK180] Calibration results saved to {out_path}")

    return {"readout_em": readout_em}


def main() -> None:
    parser = argparse.ArgumentParser(description="WK180 readout EM calibration")
    parser.add_argument("--dummy", action="store_true", help="Use dummy mode")
    parser.add_argument("--backend", type=str, default=None, help="OriginQ backend name")
    parser.add_argument("--qubits", type=int, nargs="+", default=None, help="Qubit indices")
    parser.add_argument("--pairs", type=int, nargs="+", default=None,
                        help="Qubit pairs as: u1 v1 u2 v2 ...")
    parser.add_argument("--max-age-hours", type=float, default=24.0, dest="max_age_hours")
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    pairs = None
    if args.pairs:
        if len(args.pairs) % 2 != 0:
            print("Error: --pairs requires an even number of arguments", file=sys.stderr)
            sys.exit(1)
        pairs = [(args.pairs[i], args.pairs[i + 1]) for i in range(0, len(args.pairs), 2)]

    try:
        run_wk180_readout_em(
            dummy=args.dummy,
            qubits=args.qubits,
            pairs=pairs,
            max_age_hours=args.max_age_hours,
            shots=args.shots,
            backend_name=args.backend,
            output_file=args.output,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
