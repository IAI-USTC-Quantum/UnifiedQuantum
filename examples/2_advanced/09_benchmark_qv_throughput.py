#!/usr/bin/env python
"""Quantum Volume and local compile/execute throughput benchmark entries.

Demonstrates the two NISQ-framework benchmark entries added this round:

* Quantum Volume (Cross et al. 2019) — seeded model circuits, heavy-output
  judgement, QV = 2**width on success.
* Local compile/execute throughput — circuits/hour at a fixed
  shots-per-circuit budget, with the timing boundary recorded in the report.

Both entries run entirely on the local simulator stack (no cloud task).

Usage:
    python 09_benchmark_qv_throughput.py

[doc-require: ]
[doc-title: 量子体积与本地编译/执行吞吐基准]
"""

from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from uniqc.benchmark import run_quantum_volume, run_throughput_benchmark  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None, help="Write both reports to this JSON file.")
    args = parser.parse_args()

    qv = run_quantum_volume(width=4, trials=5, shots=500, base_seed=7)
    print("== Quantum Volume (width=4, trials=5, shots=500, seed=7) ==")
    print(f"mean heavy-output probability : {qv.mean_h:.4f} +/- {qv.sigma_mean:.4f}")
    print(f"trials passed                 : {qv.trials_passed}/{qv.trials}")
    print(f"criterion mean_h - 2*sigma > 2/3 : {'PASS' if qv.passed else 'FAIL'}")
    print(f"Quantum Volume                : {qv.quantum_volume}")

    throughput = run_throughput_benchmark(
        circuits=100, n_qubits=8, depth=6, shots=1000, seed=11, backend_id="dummy:local:simulator"
    )
    print()
    print("== Local compile/execute throughput (100 circuits x 8q depth 6, 1000 shots) ==")
    print(f"compile   : {throughput.compile_seconds:.3f}s ({throughput.compile_circuits_per_hour:,.0f} circuits/h)")
    print(f"execute   : {throughput.execute_seconds:.3f}s ({throughput.execute_circuits_per_hour:,.0f} circuits/h)")
    print(f"total     : {throughput.total_seconds:.3f}s -> {throughput.circuits_per_hour:,.0f} circuits/h")
    print(f">= 30,000 circuits/hour        : {'PASS' if throughput.meets_30000_per_hour else 'BELOW'}")
    print(f"timing boundary               : {throughput.to_json_dict()['criterion']}")
    print(f"cpu backend                   : {throughput.environment['cpu_backend']}")

    if args.output:
        payload = {"quantum_volume": qv.to_json_dict(), "throughput": throughput.to_json_dict()}
        with open(args.output, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
        print(f"reports written to {args.output}")


if __name__ == "__main__":
    main()
