#!/usr/bin/env python
"""WK180 chip-wide parallel-CZ XEB example for UnifiedQuantum.

This example partitions every CZ edge of OriginQ's WK_C180 chip into
three disjoint matchings (3-edge-coloring), picks one matching, and
runs a chip-wide *parallel* 2-qubit XEB on that single matching. The
full N-qubit circuit factorises as a tensor product over the disjoint
pairs of the matching, so per-pair F_XEB(d) decays — and therefore
per-pair CZ fidelities — fall out of 2-qubit marginals of the
chip-wide bitstring (no 2^N statevector blow-up needed for analysis).

This is the recommended *pre-flight* characterization step before any
larger experiment that depends on accurate per-pair CZ numbers.

Pre-flight policy (no fallbacks)
--------------------------------
This example refuses to run unless every prerequisite is satisfied:

* ``pyqpanda3`` must be importable (the OriginQ SDK).
* The WK180 chip characterization must be present in the local cache
  *and* younger than 24 hours; otherwise it is refreshed via the
  OriginQ SDK. If the SDK refresh fails (no API key / network /
  invalid chip name), the example aborts with a precise error.
* ``--dummy`` mode is **not** exempt from any of the above — chip-noisy
  simulation is meaningless without real chip data.
* Real-chip submission additionally requires ``--confirm-chip``.

Usage:

    # Inspect the 3-coloring without running anything (still pre-flighted):
    python examples/wk180/xeb.py --list-colors

    # Dummy mode (use --max-qubits to keep the noisy density-op simulator happy):
    python examples/wk180/xeb.py --dummy --max-qubits 10 --color 0

    # Real chip:
    python examples/wk180/xeb.py --backend originq:wuyuan:wk180 \\
        --color 0 --confirm-chip --shots 5000 --instances 20

    # 1q-XEB sanity check on a few qubits:
    python examples/wk180/xeb.py --dummy --type 1q --qubits 0 1 2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "UnifiedQuantum"))

from uniqc.backend_adapter.preflight import (  # noqa: E402
    BackendPreflightError,
    MissingDependencyError,
)


# ---------------------------------------------------------------------------
# Adapter / chip plumbing
# ---------------------------------------------------------------------------


def _get_wk180_backend(
    dummy: bool, backend_name: str | None
) -> tuple[Any, Any, str]:
    """Return ``(adapter, chip_characterization, backend_label)``.

    Strict policy (no fallbacks): if ``pyqpanda3`` (the OriginQ SDK) is
    not importable, or the WK180 chip characterization cannot be
    fetched / refreshed, this raises immediately with a clear install /
    setup hint. ``--dummy`` mode is *not* exempt — noise-aware
    simulation depends on real chip data, so the real-provider checks
    apply.
    """
    from uniqc.backend_adapter.preflight import ensure_backend_ready
    from uniqc.backend_adapter.task.adapters import DummyAdapter, OriginQAdapter

    backend_name = backend_name or "originq:wuyuan:wk180"
    chip_short = backend_name.split(":")[-1] or "WK_C180"

    backend_id = (
        f"dummy:originq:{chip_short}" if dummy else f"originq:{chip_short}"
    )
    chip_char = ensure_backend_ready(backend_id, max_age_hours=24.0)
    if chip_char is None:
        raise RuntimeError(
            f"Preflight returned no chip characterization for {backend_id!r}; "
            "this is a bug — please report it."
        )

    if dummy:
        adapter = DummyAdapter(chip_characterization=chip_char)
        return adapter, chip_char, f"dummy:originq:{chip_short}"
    adapter = OriginQAdapter(backend_name=chip_short)
    return adapter, chip_char, backend_name


# ---------------------------------------------------------------------------
# Three-coloring + region restriction
# ---------------------------------------------------------------------------


def _three_color(chip_char: Any) -> tuple[Any, list[list[tuple[int, int]]]]:
    """Build a chip view + 3-color partition of every CZ edge.

    Returns ``(view, colors)`` where ``colors`` is a list of matchings
    ordered from largest to smallest edge count.
    """
    from uniqc.calibration.xeb import ChipTopologyView, three_color_chip

    view = ChipTopologyView.from_chip_characterization(chip_char)
    colors = [list(c) for c in three_color_chip(view, max_K=4)]
    colors.sort(key=lambda c: -len(c))
    return view, colors


def _restrict_color_to_region(
    view: Any, color: list[tuple[int, int]],
    max_touched_qubits: int, *, seed: int = 0,
) -> tuple[list[int], list[tuple[int, int]]]:
    """Pick a high-fidelity region and intersect ``color`` with its
    induced edges, capping the number of *touched* qubits at
    ``max_touched_qubits`` (so the resulting circuit fits in the
    DummyAdapter's noisy simulator, which is limited to ~10 qubits).

    Strategy: pick the highest-fidelity region of ``2 * (max_touched_qubits)``
    qubits, intersect with the matching, then greedily keep pairs in
    descending pair-fidelity order until the qubit cap is reached.
    """
    from uniqc.calibration.xeb import pick_region

    region_size = max(min(len(view.enabled_qubits), 4 * max_touched_qubits),
                      max_touched_qubits)
    region = pick_region(view, n=int(region_size), seed=seed)
    region_set = set(region.qubits)
    candidates = [
        (a, b) for (a, b) in color if a in region_set and b in region_set
    ]
    # Sort by ascending 2q error (best pairs first).
    candidates.sort(key=lambda e: view.two_qubit_error(*e))

    chosen: list[tuple[int, int]] = []
    touched: set[int] = set()
    for a, b in candidates:
        if len(touched | {a, b}) > max_touched_qubits:
            continue
        chosen.append((a, b))
        touched.update((a, b))
        if len(touched) >= max_touched_qubits:
            break
    return sorted(touched), chosen


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def run_wk180_parallel_cz_xeb(
    *,
    dummy: bool = True,
    backend_name: str | None = None,
    color_idx: int = 0,
    max_qubits: int | None = None,
    region_seed: int = 0,
    depths: list[int] | None = None,
    instances: int = 20,
    shots: int = 5000,
    seed: int = 2026,
    output_file: str | None = None,
    cache_dir: str | None = None,
) -> dict[str, Any]:
    """Run chip-wide parallel-CZ XEB on one 3-coloring matching of WK180.

    Args:
        dummy: If True, run on local DummyAdapter (chip-noisy). For
            dummy mode you almost always want ``max_qubits`` set,
            since simulating ~140 qubits is intractable.
        backend_name: Override OriginQ backend identifier.
        color_idx: Which matching to use (0 = largest by default).
        max_qubits: If set, restrict to a high-fidelity region of this
            many qubits and intersect the matching with its induced edges.
        region_seed: Seed for region picking when ``max_qubits`` is set.
        depths: Depth grid. Defaults to ``[5, 10, 15, 20, 25, 30]``.
        instances: Random circuit instances per depth.
        shots: Shots per circuit.
        seed: Master corpus RNG seed.
        output_file: If supplied, write the full result as JSON.
        cache_dir: Forwarded to the benchmarker for per-pair XEBResult JSON.

    Returns:
        Dict with keys ``region_qubits``, ``patterns``, ``pairs``,
        ``per_pair_decays``, ``per_pair_results``, ``corpus_size``,
        ``color_summary`` (sizes of the three colors).
    """
    from uniqc import xeb_workflow

    if depths is None:
        depths = [5, 10, 15, 20, 25, 30]

    adapter, chip_char, backend_label = _get_wk180_backend(dummy, backend_name)

    view, colors = _three_color(chip_char)
    color_summary = [len(c) for c in colors]
    print(
        f"[WK180] 3-coloring of {len(view.coupling_map)} CZ edges → "
        f"3 matchings of sizes {color_summary} "
        f"({sum(color_summary)} edges total)"
    )
    if not (0 <= color_idx < len(colors)):
        raise SystemExit(
            f"--color={color_idx} out of range; "
            f"only {len(colors)} colors available"
        )
    chosen_color = colors[color_idx]
    chosen_qubits = sorted({q for e in chosen_color for q in e})
    print(
        f"[WK180] selected color {color_idx}: "
        f"{len(chosen_color)} pairs touching {len(chosen_qubits)} qubits"
    )

    if max_qubits is not None and max_qubits < len(chosen_qubits):
        region_qubits, restricted = _restrict_color_to_region(
            view, chosen_color, max_qubits, seed=region_seed,
        )
        print(
            f"[WK180] restricted to a {max_qubits}-qubit high-fidelity "
            f"region; {len(restricted)} pairs of color {color_idx} fall "
            f"inside it (touching {len(region_qubits)} qubits)"
        )
        if not restricted:
            raise SystemExit(
                f"After restricting to {max_qubits}-qubit region, color "
                f"{color_idx} has no edges. Try a different --color or "
                "increase --max-qubits."
            )
        patterns = [restricted]
    else:
        region_qubits = chosen_qubits
        patterns = [chosen_color]

    # The workflow routes through ParallelCZBenchmarker which uses the
    # adapter's simulate_pmeasure fast path on the dummy backend, or
    # submit_batch on real hardware.
    result = xeb_workflow.run_parallel_cz_xeb_workflow(
        backend=backend_label,
        chip_characterization=chip_char,
        region_qubits=region_qubits,
        patterns=patterns,
        depths=depths,
        instances=instances,
        shots=shots,
        seed=seed,
        cache_dir=cache_dir,
    )

    print(
        f"[WK180] ran {result['corpus_size']} circuits "
        f"(1 pattern × {len(depths)} depths × {instances} instances), "
        f"{shots} shots each"
    )
    print(f"[WK180] per-pair CZ fidelity (alpha = per-cycle survival):")
    rows = sorted(result["per_pair_decays"].items(), key=lambda kv: -kv[1].alpha)
    for pair, dec in rows:
        print(
            f"  {pair[0]:>3d} — {pair[1]:<3d}: "
            f"alpha={dec.alpha:.4f} ± {dec.alpha * dec.sigma_log_alpha:.4f}  "
            f"(beta={dec.beta:.3f}, n_pts={dec.n_points})"
        )

    payload = {
        "backend": backend_label,
        "color_summary": color_summary,
        "selected_color_idx": color_idx,
        "selected_color_n_pairs": len(patterns[0]),
        "region_qubits": list(result["region_qubits"]),
        "patterns": [[list(e) for e in p] for p in result["patterns"]],
        "depths": list(depths),
        "instances": instances,
        "shots": shots,
        "corpus_size": result["corpus_size"],
        "per_pair_alpha": {
            f"{p[0]}-{p[1]}": {
                "alpha": dec.alpha,
                "alpha_sigma": dec.alpha * dec.sigma_log_alpha,
                "beta": dec.beta,
                "log_alpha": dec.log_alpha,
                "log_beta": dec.log_beta,
                "n_points": dec.n_points,
                "log_residual_std": dec.log_residual_std,
            }
            for p, dec in result["per_pair_decays"].items()
        },
    }

    if output_file:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"[WK180] results saved to {out_path}")

    return payload


def run_wk180_1q_xeb(
    *,
    dummy: bool = True,
    backend_name: str | None = None,
    qubits: list[int] | None = None,
    depths: list[int] | None = None,
    n_circuits: int = 50,
    shots: int = 1000,
    use_readout_em: bool = True,
) -> dict:
    """Convenience wrapper for 1-qubit XEB on a few WK180 qubits."""
    from uniqc import xeb_workflow

    if depths is None:
        depths = [5, 10, 20, 50]
    if qubits is None:
        qubits = [0, 1, 2]

    adapter, chip_char, backend_label = _get_wk180_backend(dummy, backend_name)
    print(f"[WK180] 1q XEB on qubits {qubits}")
    results = xeb_workflow.run_1q_xeb_workflow(
        backend=backend_label,
        qubits=qubits,
        depths=depths,
        n_circuits=n_circuits,
        shots=shots,
        use_readout_em=use_readout_em,
        chip_characterization=chip_char,
    )
    for q, r in results.items():
        print(
            f"  q{q}: r={r.fidelity_per_layer:.5f} ± "
            f"{r.fidelity_std_error:.5f}"
        )
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WK180 chip-wide parallel-CZ XEB benchmark"
    )
    parser.add_argument("--dummy", action="store_true",
                        help="Run on DummyAdapter (local noisy simulation)")
    parser.add_argument("--backend", type=str, default=None,
                        help="OriginQ backend (default: originq:wuyuan:wk180)")
    parser.add_argument("--type", choices=["parallel_cz", "1q"],
                        default="parallel_cz",
                        help="parallel_cz: chip-wide parallel CZ XEB on one "
                             "3-coloring matching (default). "
                             "1q: separate 1-qubit XEB workflow on --qubits.")
    # parallel-CZ XEB args
    parser.add_argument("--color", type=int, default=0, dest="color_idx",
                        help="Which 3-coloring matching to run (0..2). "
                             "Sorted descending by edge count, so 0 is the largest.")
    parser.add_argument("--list-colors", action="store_true",
                        help="Print the 3-coloring summary and exit.")
    parser.add_argument("--max-qubits", type=int, default=None,
                        help="Cap on actually-touched qubits in the matching "
                             "(recommended for --dummy because the noisy "
                             "DummyAdapter simulator is limited to ~10 qubits). "
                             "Defaults to running every qubit touched by the matching.")
    parser.add_argument("--region-seed", type=int, default=0,
                        help="Seed for region picking when --max-qubits is set.")
    parser.add_argument("--depths", type=int, nargs="+", default=None,
                        help="Depth grid. Default: 5 10 15 20 25 30.")
    parser.add_argument("--instances", type=int, default=20,
                        help="Random circuit instances per depth (default 20).")
    parser.add_argument("--shots", type=int, default=5000,
                        help="Shots per circuit (default 5000).")
    parser.add_argument("--seed", type=int, default=2026,
                        help="Master corpus RNG seed.")
    parser.add_argument("--output", type=str, default=None,
                        help="Write per-pair fidelities to this JSON file.")
    parser.add_argument("--cache-dir", type=str, default=None,
                        help="Per-pair XEBResult JSON output directory.")
    parser.add_argument("--confirm-chip", action="store_true",
                        help="Required to submit to real hardware.")
    # 1q XEB args
    parser.add_argument("--qubits", type=int, nargs="+", default=None,
                        help="Qubits for --type=1q (default 0 1 2).")
    parser.add_argument("--n-circuits", type=int, default=50,
                        dest="n_circuits",
                        help="Random circuits per depth for --type=1q.")
    parser.add_argument("--no-readout-em", action="store_true",
                        dest="no_readout_em",
                        help="Disable readout EM for --type=1q.")
    args = parser.parse_args()

    try:
        if args.list_colors:
            adapter, chip_char, _ = _get_wk180_backend(
                dummy=True, backend_name=args.backend,
            )
            _, colors = _three_color(chip_char)
            for i, c in enumerate(colors):
                qs = sorted({q for e in c for q in e})
                print(f"color {i}: {len(c)} pairs, {len(qs)} qubits")
            return

        if not args.dummy and not args.confirm_chip:
            print(
                "ERROR: real-chip submission requires --confirm-chip "
                "(safety check to prevent accidental chip jobs).",
                file=sys.stderr,
            )
            sys.exit(2)

        if args.type == "1q":
            run_wk180_1q_xeb(
                dummy=args.dummy,
                backend_name=args.backend,
                qubits=args.qubits,
                depths=args.depths,
                n_circuits=args.n_circuits,
                shots=args.shots,
                use_readout_em=not args.no_readout_em,
            )
        else:
            run_wk180_parallel_cz_xeb(
                dummy=args.dummy,
                backend_name=args.backend,
                color_idx=args.color_idx,
                max_qubits=args.max_qubits,
                region_seed=args.region_seed,
                depths=args.depths,
                instances=args.instances,
                shots=args.shots,
                seed=args.seed,
                output_file=args.output,
                cache_dir=args.cache_dir,
            )
    except (MissingDependencyError, BackendPreflightError) as e:
        # Pre-flight rejection: surface the message cleanly, no traceback.
        print(f"\nERROR: {e}\n", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
