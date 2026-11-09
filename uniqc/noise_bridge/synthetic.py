"""Synthetic noise-model exchange files for local interface verification.

Produces valid ``nlearn.noise-model.v1`` payloads *without* importing the
private ``nlearn`` package: the schema, canonical hash, and Pauli-order
conventions are replicated from the published exchange contract (including
the runtime probe that detects whether the density-operator backend applies
``PauliError2Q`` arguments transposed).

These models are explicitly ``data_class: "synthetic"``.  They carry
WK_C180-scale error magnitudes so that local QRAM/QPU/mitigation cases and
tests exercise the same numerical regime as hardware models, but they are
**not** hardware measurements and must not be cited as such.  Real historical
noise data enters through :func:`uniqc.noise_bridge.exchange.load_noise_model`
with the ``hardware_archive`` / ``historical_replay`` classes produced by the
noise-learning product.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from uniqc.noise_bridge.exchange import SCHEMA, UNIQC_BINDING, _canonical_hash

__all__ = ["PAULI2Q_ORDER", "build_synthetic_model", "write_synthetic_model"]

PAULI2Q_ORDER = [
    "XI",
    "YI",
    "ZI",
    "IX",
    "XX",
    "YX",
    "ZX",
    "IY",
    "XY",
    "YY",
    "ZY",
    "IZ",
    "XZ",
    "YZ",
    "ZZ",
]

_TRANSPOSE_PERM = {
    0: 3,
    1: 7,
    2: 11,
    3: 0,
    4: 4,
    5: 8,
    6: 12,
    7: 1,
    8: 5,
    9: 9,
    10: 13,
    11: 2,
    12: 6,
    13: 10,
    14: 14,
}

_TRANSPOSED: bool | None = None


def _pauli2q_transposed() -> bool:
    """Probe whether the DM backend interprets PauliError2Q ps transposed."""
    global _TRANSPOSED
    if _TRANSPOSED is None:
        import uniqc_cpp

        dm = uniqc_cpp.DensityOperatorSimulator()
        dm.init_n_qubit(2)
        dm.x(0)
        ps = [0.0] * 15
        ps[PAULI2Q_ORDER.index("XI")] = 1.0
        dm.pauli_error_2q(0, 1, ps)
        state = np.asarray(dm.state if isinstance(dm.state, list) else dm.state()).flatten()
        diag = np.abs(state.reshape(4, 4).diagonal())
        _TRANSPOSED = bool(diag[3] > 0.5)
    return _TRANSPOSED


def _ps_for_dm(ps: list[float]) -> list[float]:
    """Reorder ps so the DM backend applies the documented Pauli labels."""
    if not _pauli2q_transposed():
        return list(ps)
    out = [0.0] * 15
    for src, dst in _TRANSPOSE_PERM.items():
        out[dst] = ps[src]
    return out


def _normalised(probabilities: dict[str, float]) -> dict[str, float]:
    """Assemble the full Pauli distribution: keep error rates as-is, I = 1 - sum."""
    identity = 1.0 - sum(value for key, value in probabilities.items() if key != "I")
    if identity < 0.0:
        raise ValueError("synthetic 1q error rates must sum to <= 1")
    return {"I": identity, **{k: v for k, v in probabilities.items() if k != "I"}}


def build_synthetic_model(
    *,
    num_qubits: int = 5,
    seed: int = 0,
    generator_note: str = "WK_C180-scale synthetic channels for local interface verification",
) -> dict[str, Any]:
    """Build a valid synthetic ``nlearn.noise-model.v1`` payload.

    Args:
        num_qubits: Chain length (>= 2).  Line topology ``0-1-...-n-1``.
        seed: Seed for the per-channel magnitude jitter.
        generator_note: Recorded in ``source.evidence``.

    Returns:
        The validated payload dict (with ``model_sha256`` set).
    """
    if num_qubits < 2:
        raise ValueError(f"num_qubits must be >= 2, got {num_qubits}")
    rng = np.random.default_rng(seed)

    one_qubit = []
    gate_errors: list[dict[str, Any]] = []
    readout_binding: dict[str, list[float]] = {}
    readout_channels = []
    for local in range(num_qubits):
        p_x, p_y, p_z = (float(v) for v in rng.uniform(0.0005, 0.0025, size=3))
        probabilities = _normalised({"X": p_x, "Y": p_y, "Z": p_z})
        one_qubit.append(
            {
                "physical_qubit": local,
                "local_qubit": local,
                "gate": "RPhi",
                "channel": "pauli_1q",
                "label_order": ["I", "X", "Y", "Z"],
                "probabilities": probabilities,
            }
        )
        gate_errors.append(
            {
                "gate": "RPhi",
                "qubits": [local],
                "error": {
                    "type": "PauliError1Q",
                    "arguments": [probabilities[label] for label in ("X", "Y", "Z")],
                },
            }
        )
        p01 = float(rng.uniform(0.01, 0.04))
        p10 = float(rng.uniform(0.01, 0.04))
        readout_binding[str(local)] = [p01, p10]
        readout_channels.append({"physical_qubit": local, "local_qubit": local, "p01": p01, "p10": p10})

    two_qubit = []
    for local_a, local_b in zip(range(num_qubits - 1), range(1, num_qubits), strict=True):
        raw = rng.uniform(0.0005, 0.0025, size=15)
        total_error = float(rng.uniform(0.015, 0.03))
        raw = raw / raw.sum() * total_error
        probabilities = {"II": 1.0 - total_error}
        for label, value in zip(PAULI2Q_ORDER, raw, strict=True):
            probabilities[label] = float(value)
        ordered = [probabilities[label] for label in PAULI2Q_ORDER]
        two_qubit.append(
            {
                "physical_edge": [local_a, local_b],
                "local_edge": [local_a, local_b],
                "gate": "CZ",
                "channel": "pauli_2q",
                "label_order": PAULI2Q_ORDER,
                "identity_label": "II",
                "label_convention": "每标签 char0/char1 分别对应 local_edge 顺序，II 单独记录",
                "learning_group_char0_physical_qubit": local_a,
                "labels_swapped_for_consumer_layout": False,
                "middle_edge_xx_yy_boost": 0.0,
                "probabilities": probabilities,
                "uniqc_density_operator_order": _ps_for_dm(ordered),
            }
        )
        gate_errors.append(
            {
                "gate": "CZ",
                "qubits": [local_a, local_b],
                "error": {
                    "type": "PauliError2Q",
                    "arguments": _ps_for_dm(ordered),
                    "argument_convention": "uniqc_cpp density_operator transposed layout probe",
                },
            }
        )

    edge_flip_entries = []
    if num_qubits >= 5:
        edge_flip_entries.append(
            {
                "physical_edge": [3, 4],
                "local_qubits": [3, 4],
                "outcome_xor_mask": (1 << 3) | (1 << 4),
                "rate": float(rng.uniform(0.002, 0.008)),
            }
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generator": {
            "name": "uniqc-noise-bridge",
            "version": "1",
            "adapter": "uniqc.noise_bridge.synthetic",
        },
        "data_class": "synthetic",
        "new_hardware_run": False,
        "source": {
            "session_path": "",
            "session_sha256": hashlib.sha256(b"uniqc-synthetic").hexdigest(),
            "region_sha256": hashlib.sha256(b"uniqc-synthetic-region").hexdigest(),
            "chip": "synthetic-line",
            "learning_group_index": 0,
            "learning_group_qubits": list(range(num_qubits)),
            "readout_calibration": {"inline": True},
            "edge_flip_calibration": None,
            "evidence": {"note": generator_note, "seed": seed},
        },
        "layout": {
            "physical_chain": list(range(num_qubits)),
            "local_to_physical": {str(i): i for i in range(num_qubits)},
            "measurement_order": list(range(num_qubits)),
            "cbit_mapping": {str(i): i for i in range(num_qubits)},
            "bitstring_order": "c_{n-1}...c_0; c0 在最右；局部位置 r 对应 outcome 整数的 bit r",
            "virtual_rz_noiseless": True,
        },
        "topology": {
            "local_edges": [[i, i + 1] for i in range(num_qubits - 1)],
            "physical_edges": [[i, i + 1] for i in range(num_qubits - 1)],
        },
        "channels": {
            "single_qubit": one_qubit,
            "two_qubit": two_qubit,
            "readout": readout_channels,
            "post_measurement_edge_flip": {
                "type": "independent_stochastic_xor_mixture",
                "entries": edge_flip_entries,
                "application": "dummy:virtual/UniQC 采样后按本地掩码施加；不是真机新采集",
            },
        },
        "consumer_bindings": {
            UNIQC_BINDING: {
                "simulator": "density_operator",
                "gate_specific_errors": gate_errors,
                "readout_error": readout_binding,
                "virtual_gate_exclusions": ["RZ"],
                "postprocessing": "channels.post_measurement_edge_flip",
            }
        },
        "dependencies": {},
        "protocol": {
            "fitting": "合成生成，非学习会话",
            "twirl_pec_zne": "不适用",
            "pauli_2q_order": PAULI2Q_ORDER,
            "source_scripts": [],
        },
    }
    if not math.isclose(sum(payload["channels"]["single_qubit"][0]["probabilities"].values()), 1.0, abs_tol=1e-9):
        raise AssertionError("synthetic 1q probabilities must stay normalized")
    payload["model_sha256"] = _canonical_hash(payload)
    from uniqc.noise_bridge.exchange import validate_exchange_payload

    validate_exchange_payload(payload)
    return payload


def write_synthetic_model(
    path: str | Path,
    *,
    num_qubits: int = 5,
    seed: int = 0,
) -> Path:
    """Write a synthetic exchange model file and return its path."""
    path = Path(path)
    payload = build_synthetic_model(num_qubits=num_qubits, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
