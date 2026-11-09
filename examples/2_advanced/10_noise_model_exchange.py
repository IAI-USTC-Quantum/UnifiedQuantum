#!/usr/bin/env python
"""Versioned noise-model exchange: import, 3-layer QRAM, QPU addressing, mitigation.

Demonstrates the noise-bridge capability added this round:

* generate a synthetic ``nlearn.noise-model.v1`` exchange file
  (WK_C180-scale channels, ``data_class: synthetic`` — not hardware data);
* import it into the noisy VM (density-operator simulator) via
  ``load_noise_model``;
* run the 3-layer (8-entry) QRAM basis lookup and the QPU-superposition
  addressing case;
* mitigate the data-register readout through the unified ``ReadoutEM``
  interface, calibrated on the same noisy VM.

Everything runs locally; no cloud task is submitted. Real historical noise
data arrives as ``hardware_archive``/``historical_replay`` exchange files
produced by the noise-learning product — same import path, no code coupling.

Usage:
    python 10_noise_model_exchange.py

[doc-require: ]
[doc-title: 版本化噪声模型交换与含噪 VM 的 QRAM/QPU 寻址]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from uniqc.noise_bridge import (  # noqa: E402
    load_noise_model,
    run_qpu_addressing_case,
    run_qram_lookup_case,
    write_synthetic_model,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None, help="Write both case reports to this JSON file.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="noise-bridge-") as workdir:
        model_path = write_synthetic_model(Path(workdir) / "model.json", num_qubits=5, seed=42)
        model = load_noise_model(model_path)
        print(f"imported {model.payload['schema']} model sha256={model.model_sha256[:12]}...")
        print(f"data_class={model.data_class}  chain={model.physical_chain}")

        lookup = run_qram_lookup_case(model, address=5, shots=500, seed=3, workdir=Path(workdir) / "cal")
        print()
        print("== 3-layer QRAM basis lookup (address=5, shots=500) ==")
        print(f"expected value      : {lookup['expected_value']} ({format(lookup['expected_value'], '02b')})")
        print(f"raw accuracy        : {lookup['raw_accuracy']:.3f} (top outcome {lookup['raw_top_outcome']})")
        print(
            f"mitigated accuracy  : {lookup['mitigated_accuracy']:.3f} (top outcome {lookup['mitigated_top_outcome']})"
        )
        print(f"noisy counts        : {lookup['noisy_counts']}")
        print(f"mitigated counts    : {lookup['mitigated_counts']}")

        qpu = run_qpu_addressing_case(model, shots=500, seed=4, workdir=Path(workdir) / "cal")
        print()
        print("== QPU superposition addressing (shots=500) ==")
        print(f"ideal distribution  : {qpu['ideal_distribution']}")
        print(f"raw fidelity        : {qpu['raw_fidelity']:.4f}")
        print(f"mitigated fidelity  : {qpu['mitigated_fidelity']:.4f}")

        if args.output:
            payload = {
                "model": {
                    "schema": model.payload["schema"],
                    "sha256": model.model_sha256,
                    "chain": model.physical_chain,
                },
                "lookup": lookup,
                "qpu": qpu,
            }
            with open(args.output, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, ensure_ascii=False)
            print(f"reports written to {args.output}")


if __name__ == "__main__":
    main()
