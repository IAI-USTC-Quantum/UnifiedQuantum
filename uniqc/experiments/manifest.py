"""Experiment coverage manifest: tomography / mitigation / calibration entries.

Audits the existing (business-frozen) experiment flows against UniQC's
unified interface and packages, for each experiment:

- the unified-interface entry point(s) callable today,
- an exact **local verification command** that runs offline (no cloud task),
- the frozen **real-machine re-test command** for the later authorized
  re-measurement window (recording only — running it consumes real quota
  and is out of scope for this round),
- where the historical records live (task store, calibration cache,
  example execution logs),
- freeze status notes (business-frozen vs. registered unimplemented
  placeholder).

This module is read-only documentation-as-data; it never executes or
submits anything itself.  The frozen business sources are guarded by
``scripts/check_engineering_freeze.py`` (134 files, manifest
``engineering-business-freeze.json``) — this package adds coverage without
touching them.
"""

from __future__ import annotations

import copy
from typing import Any

__all__ = ["EXPERIMENTS", "get_manifest", "render_text"]

TASK_STORE_NOTE = "Task store: ~/.uniqc/cache/tasks.sqlite (uniqc task list / show / shards)"
CAL_CACHE_NOTE = "Calibration cache: ~/.uniqc/calibration_cache/ (TTL-enforced)"
FREEZE_NOTE = (
    "Frozen business sources: engineering-business-freeze.json "
    "(134 files, checked by scripts/check_engineering_freeze.py); "
    "circuits/mapping/shots/randomization/submission-recovery/bit-order/formulas unchanged."
)

EXPERIMENTS: list[dict[str, Any]] = [
    {
        "id": "xeb",
        "name": "Cross-entropy benchmarking (XEB, 1q/2q/parallel-CZ patterns)",
        "category": "calibration",
        "unified_interface": [
            "uniqc.calibration.xeb (benchmarker/fitter/patterns)",
            "CLI: uniqc calibrate xeb",
        ],
        "local_verify": "uv run uniqc calibrate xeb --backend dummy:local:simulator --type 1q --qubits 0 1 2",
        "retest_command": (
            "uv run uniqc calibrate xeb --backend originq:WK_C180 --type 2q "
            "--qubits <frozen qubit set> --shots <frozen shots>  # real machine; requires token + quota"
        ),
        "retest_note": "Frozen experiment business; do not run this round. Requires originq credentials.",
        "record_sources": [CAL_CACHE_NOTE, TASK_STORE_NOTE, "examples/2_advanced/wk180/xeb.py (pre-flight policy)"],
        "freeze": FREEZE_NOTE,
        "status": "frozen_business__local_verify_available",
    },
    {
        "id": "readout_calibration",
        "name": "Readout error calibration (1q confusion matrices, 2q joint)",
        "category": "calibration",
        "unified_interface": [
            "uniqc.calibration.readout.ReadoutCalibrator",
            "CLI: uniqc calibrate readout",
        ],
        "local_verify": "uv run uniqc calibrate readout --backend dummy:local:simulator --qubits 0 1",
        "retest_command": (
            "uv run uniqc calibrate readout --backend originq:WK_C180 --qubits <frozen qubit set> "
            "--shots <frozen shots>  # real machine; requires token + quota"
        ),
        "retest_note": "Frozen experiment business; do not run this round.",
        "record_sources": [CAL_CACHE_NOTE, TASK_STORE_NOTE],
        "freeze": FREEZE_NOTE,
        "status": "frozen_business__local_verify_available",
    },
    {
        "id": "readout_em",
        "name": "Readout error mitigation (ReadoutEM over M3 mitigator)",
        "category": "mitigation",
        "unified_interface": [
            "uniqc.qem.ReadoutEM / uniqc.qem.M3Mitigator",
            "uniqc.algorithms.workflows.readout_em_workflow.run_readout_em_workflow",
            "uniqc.noise_bridge.qram_cases (this round: mitigate on imported noisy VM)",
        ],
        "local_verify": "uv run python -c \"from uniqc import run_readout_em_workflow; print(run_readout_em_workflow(backend='dummy:local:simulator', qubits=[0,1]))\"",
        "retest_command": (
            "python examples/2_advanced/wk180/readout_em.py --backend originq:wuyuan:wk180 "
            "--qubits <frozen qubit set>  # real machine; frozen business"
        ),
        "retest_note": "Frozen experiment business; do not run this round.",
        "record_sources": [CAL_CACHE_NOTE, TASK_STORE_NOTE, "examples/2_advanced/wk180/readout_em.py"],
        "freeze": FREEZE_NOTE,
        "status": "frozen_business__local_verify_available",
    },
    {
        "id": "zne",
        "name": "Zero-noise extrapolation (ZNE)",
        "category": "mitigation",
        "unified_interface": ["uniqc.qem.ZNE (module present)"],
        "local_verify": None,
        "retest_command": None,
        "retest_note": (
            "Historical unimplemented placeholder (4 registered occurrences); "
            "kept separate from this round's business freeze — not a regression of frozen flows."
        ),
        "record_sources": ["uniqc/qem/zne.py (placeholder)"],
        "freeze": FREEZE_NOTE,
        "status": "unimplemented_placeholder__registered",
    },
    {
        "id": "state_tomography",
        "name": "Full quantum state tomography",
        "category": "tomography",
        "unified_interface": [
            "uniqc.algorithms.core.measurement.state_tomography / StateTomography / tomography_summary",
        ],
        "local_verify": "uv run python examples/2_advanced/measurement/state_tomography.py --n-shots 2000",
        "retest_command": (
            "Route the same tomography circuits through submit_task(backend='<platform>:<chip>', "
            "shots=<frozen shots>)  # real machine; frozen business"
        ),
        "retest_note": "Frozen experiment business; do not run this round.",
        "record_sources": [TASK_STORE_NOTE, "examples/2_advanced/measurement/state_tomography.py"],
        "freeze": FREEZE_NOTE,
        "status": "frozen_business__local_verify_available",
    },
    {
        "id": "classical_shadow",
        "name": "Classical shadow tomography",
        "category": "tomography",
        "unified_interface": [
            "uniqc.algorithms.core.measurement.classical_shadow / ClassicalShadow",
        ],
        "local_verify": "uv run python examples/2_advanced/measurement/shadow_tomography.py --n-shots 2000",
        "retest_command": (
            "Route shadow measurement circuits through submit_task(backend='<platform>:<chip>', "
            "shots=<frozen shots>)  # real machine; frozen business"
        ),
        "retest_note": "Frozen experiment business; do not run this round.",
        "record_sources": [TASK_STORE_NOTE, "examples/2_advanced/measurement/shadow_tomography.py"],
        "freeze": FREEZE_NOTE,
        "status": "frozen_business__local_verify_available",
    },
    {
        "id": "noise_model_exchange",
        "name": "Versioned noise-model exchange import (nlearn.noise-model.v1)",
        "category": "calibration",
        "unified_interface": [
            "uniqc.noise_bridge.load_noise_model / ImportedNoiseModel",
            "uniqc.noise_bridge.qram_cases (3-layer QRAM / QPU addressing / readout EM)",
        ],
        "local_verify": (
            'uv run python -c "from uniqc.noise_bridge import write_synthetic_model, load_noise_model; '
            "m = load_noise_model(write_synthetic_model('/tmp/m.json')); print(m.physical_chain)\""
        ),
        "retest_command": (
            'uv run python -c "from uniqc.noise_bridge import load_noise_model; '
            "m = load_noise_model('<owner-delivered historical model.json>'); print(m.data_class)\""
        ),
        "retest_note": (
            "Real historical noise data arrives as hardware_archive/historical_replay exchange "
            "files from the noise-learning product; import is offline and performs no new hardware run."
        ),
        "record_sources": ["exchange file model_sha256 (canonical hash)", TASK_STORE_NOTE],
        "freeze": "New engineering wrapper on top of frozen simulation/QEM sources; no frozen-file changes.",
        "status": "local_verify_available__awaits_owner_model",
    },
    {
        "id": "quantum_volume",
        "name": "Quantum Volume benchmark entry (this round)",
        "category": "benchmark",
        "unified_interface": [
            "uniqc.benchmark.run_quantum_volume",
            "CLI: uniqc benchmark qv",
        ],
        "local_verify": "uv run uniqc benchmark qv --width 4 --trials 20 --shots 1000 --seed 0",
        "retest_command": (
            "Real-device QV runs require a separately authorized cloud campaign "
            "(generate circuits with the same seeds, submit via submit_task); "
            "the local entry never submits."
        ),
        "retest_note": "Software entry validated locally; real-device evidence boundary recorded separately.",
        "record_sources": ["JSON report via --output", TASK_STORE_NOTE],
        "freeze": "New engineering surface; frozen sources untouched.",
        "status": "local_verify_available",
    },
    {
        "id": "compile_execute_throughput",
        "name": "Local compile/execute throughput benchmark (this round)",
        "category": "benchmark",
        "unified_interface": [
            "uniqc.benchmark.run_throughput_benchmark",
            "CLI: uniqc benchmark throughput",
        ],
        "local_verify": "uv run uniqc benchmark throughput --circuits 500 --qubits 8 --depth 6 --shots 1000",
        "retest_command": None,
        "retest_note": (
            "Local-software metric by definition (boundary: OriginIR parse/preprocess + statevector "
            "simulate + shot sampling); not a cloud measurement."
        ),
        "record_sources": ["JSON report via --output (includes input set, timings, environment, load)"],
        "freeze": "New engineering surface; frozen sources untouched.",
        "status": "local_verify_available",
    },
]


def get_manifest() -> list[dict[str, Any]]:
    """Return a deep copy of the experiment manifest."""
    return copy.deepcopy(EXPERIMENTS)


def render_text() -> str:
    """Render the manifest as a human-readable report."""
    lines = []
    for entry in EXPERIMENTS:
        lines.append(f"[{entry['id']}] {entry['name']}  ({entry['category']})")
        lines.append(f"  status          : {entry['status']}")
        for iface in entry["unified_interface"]:
            lines.append(f"  interface       : {iface}")
        lines.append(f"  local verify    : {entry['local_verify'] or '—'}")
        lines.append(f"  re-test command : {entry['retest_command'] or '—'}")
        if entry["retest_note"]:
            lines.append(f"  re-test note    : {entry['retest_note']}")
        for source in entry["record_sources"]:
            lines.append(f"  records         : {source}")
        lines.append("")
    lines.append(FREEZE_NOTE)
    return "\n".join(lines)
