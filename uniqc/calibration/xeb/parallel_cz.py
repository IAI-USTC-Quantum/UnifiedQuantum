"""Parallel-CZ XEB calibration: chip-pre-flight 2-qubit gate fidelity.

This module implements a *generic* parallel cross-entropy benchmarking
protocol useful as a pre-flight chip characterization step (i.e.
before running any larger experiment that depends on per-pair CZ
fidelity).

Protocol
--------
For a fixed CZ pattern (a matching of disjoint qubit pairs):

    cycle = U3(haar) on every region qubit, then CZ on every pair in the pattern

Repeat for ``depth`` cycles, then measure all region qubits. Sample
``shots`` bitstrings per circuit and ``K`` random circuit instances per
``(pattern, depth)`` combination.

For each pair in the matching, the full N-qubit circuit factorises as
a tensor product over pairs (1q ops are local; CZs are between
disjoint pairs). The 2-qubit marginal distribution on each pair is
exactly the 2-qubit pure-state distribution of that pair's
sub-circuit, so we can score every pair independently using its
2-qubit ``F_XEB(d)``. Fitting ``F(d) = beta · alpha^d`` per pair
yields the per-cycle CZ fidelity ``alpha``.

Public API
----------
* :class:`Schedule` — replayable per-cycle U3 angles + CZ pattern
* :func:`build_parallel_cz_xeb_circuit` — single circuit + Schedule
* :func:`build_parallel_cz_xeb_corpus` — full corpus
* :func:`pair_marginal_counts` — 2-qubit marginal of N-qubit counts
* :func:`pair_ideal_probs` — 2-qubit ideal probabilities for a pair
* :func:`per_pair_F_XEB` — per-(record, pair) F_XEB
* :func:`fit_pair_decays` — weighted log-LS fit ``F(d) = beta·alpha^d``
* :class:`ParallelCZBenchmarker` — end-to-end runner
"""

from __future__ import annotations

import dataclasses
import math
import time
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import numpy as np

from uniqc.calibration.results import (
    XEBResult,
    save_calibration_result,
)

if TYPE_CHECKING:
    from uniqc.backend_adapter.task.adapters.base import QuantumAdapter

PairKey = tuple[int, int]

__all__ = [
    "Schedule",
    "ProbeCircuit",
    "PairCircuitFit",
    "PairDecay",
    "build_parallel_cz_xeb_circuit",
    "build_parallel_cz_xeb_corpus",
    "pair_marginal_counts",
    "pair_ideal_probs",
    "per_pair_F_XEB",
    "fit_pair_decays",
    "ParallelCZBenchmarker",
]


# ---------------------------------------------------------------------------
# Schedule + circuit construction
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Schedule:
    """Per-cycle U3 angles and CZ pattern for a single XEB instance.

    ``cycles`` is a tuple of ``(angles_per_qubit, pattern)`` pairs.
    ``angles_per_qubit`` is ordered the same as ``region_qubits``.
    """

    region_qubits: tuple[int, ...]
    measured_qubits: tuple[int, ...]
    cycles: tuple[
        tuple[
            tuple[tuple[float, float, float], ...],
            tuple[tuple[int, int], ...],
        ],
        ...,
    ]
    seed: int

    @property
    def depth(self) -> int:
        return len(self.cycles)


@dataclasses.dataclass(frozen=True)
class ProbeCircuit:
    """One built circuit + its replayable schedule and metadata."""

    circuit: Any  # uniqc.Circuit
    schedule: Schedule
    pattern_idx: int
    pattern: tuple[PairKey, ...]
    depth: int
    instance: int
    record_id: str


def _haar_u3_angles(rng: np.random.Generator) -> tuple[float, float, float]:
    """Draw one Haar-random U3 Euler triple (theta, phi, lam).

    Sampled from the Haar measure on SU(2):
      cos(theta) ~ U[-1, 1] (i.e. theta = arccos(1 - 2u), u ~ U[0,1])
      phi ~ U[0, 2π], lam ~ U[0, 2π]
    """
    u = float(rng.random())
    theta = float(math.acos(1.0 - 2.0 * u))
    phi = float(rng.uniform(0.0, 2.0 * math.pi))
    lam = float(rng.uniform(0.0, 2.0 * math.pi))
    return theta, phi, lam


def _pattern_id(pattern: Sequence[tuple[int, int]]) -> int:
    """Deterministic 32-bit fingerprint of a pattern (independent of Python's
    randomised tuple hashing)."""
    h = 0
    for a, b in pattern:
        h = (h * 1_000_003 + int(a) * 65537 + int(b)) & 0xFFFF_FFFF
    return h


def build_parallel_cz_xeb_circuit(
    region_qubits: Sequence[int],
    pattern: Sequence[tuple[int, int]],
    depth: int,
    *,
    seed: int = 0,
    instance: int = 0,
) -> ProbeCircuit:
    """Build one parallel-CZ XEB probe circuit.

    Each cycle is ``U3(haar) on every region qubit, then CZ on every
    pair in pattern``. Single-qubit angles are drawn from a
    deterministic RNG seeded by ``(seed, depth, instance, pattern_id)``
    so different patterns get statistically independent fillings.
    """
    if depth <= 0:
        raise ValueError("depth must be positive")
    region = tuple(int(q) for q in region_qubits)
    qset = set(region)
    pat_t = tuple((int(a), int(b)) for a, b in pattern)
    for a, b in pat_t:
        if a not in qset or b not in qset:
            raise ValueError(f"pattern edge ({a},{b}) outside region {region}")

    from uniqc import Circuit

    # 0x50435A58 = "PCZX" — fixed salt, makes seeds disjoint from other XEB families
    ss = np.random.SeedSequence([int(seed), int(depth), int(instance), 0x50435A58, _pattern_id(pat_t)])
    rng = np.random.default_rng(ss)

    cycles: list[tuple[tuple[tuple[float, float, float], ...], tuple[tuple[int, int], ...]]] = []
    circuit = Circuit()
    for _ in range(depth):
        angles: list[tuple[float, float, float]] = []
        for q in region:
            theta, phi, lam = _haar_u3_angles(rng)
            angles.append((theta, phi, lam))
            circuit.u3(q, theta, phi, lam)
        for a, b in pat_t:
            circuit.cz(a, b)
        cycles.append((tuple(angles), pat_t))
    for q in region:
        circuit.measure(q)

    schedule = Schedule(
        region_qubits=region,
        measured_qubits=region,
        cycles=tuple(cycles),
        seed=int(seed),
    )
    return ProbeCircuit(
        circuit=circuit,
        schedule=schedule,
        pattern_idx=0,
        pattern=pat_t,
        depth=int(depth),
        instance=int(instance),
        record_id=f"P0_d{int(depth)}_inst{int(instance)}",
    )


def build_parallel_cz_xeb_corpus(
    region_qubits: Sequence[int],
    patterns: Sequence[Sequence[tuple[int, int]]],
    depths: Sequence[int],
    instances: int,
    *,
    seed: int = 2026,
) -> list[ProbeCircuit]:
    """Build the full XEB corpus.

    Returns ``len(patterns) * len(depths) * instances`` probes. Within a
    single ``(pattern, depth)`` slot, ``instances`` independent random
    U3 fillings are emitted.
    """
    out: list[ProbeCircuit] = []
    for p_idx, pat in enumerate(patterns):
        pat_t = tuple((int(a), int(b)) for a, b in pat)
        for d in depths:
            for inst in range(instances):
                pc = build_parallel_cz_xeb_circuit(
                    region_qubits,
                    pat_t,
                    depth=int(d),
                    seed=seed,
                    instance=int(inst),
                )
                rid = f"P{p_idx}_d{int(d)}_inst{int(inst)}"
                out.append(
                    dataclasses.replace(
                        pc,
                        pattern_idx=p_idx,
                        record_id=rid,
                    )
                )
    return out


# ---------------------------------------------------------------------------
# 2-qubit marginal counts + ideal probabilities
# ---------------------------------------------------------------------------


def _outcome_to_int(outcome: Any, width: int) -> int:
    """Normalise a counts dict key to a non-negative integer.

    Accepts ``int`` (used as-is), ``"0b…"``, or a binary string of any
    length (padded / truncated from the right to ``width`` bits via
    ``int(text[-width:], 2)`` to match standard left-padded conventions).
    """
    if isinstance(outcome, int):
        return int(outcome)
    text = str(outcome).strip()
    if text.startswith("0b"):
        return int(text, 2)
    if set(text) <= {"0", "1"} and len(text) >= 1:
        return int(text[-width:] if width > 0 and len(text) >= width else text, 2)
    return int(text)


def pair_marginal_counts(
    counts: Mapping[Any, int],
    measured_qubits: Sequence[int],
    pair: PairKey,
) -> dict[int, int]:
    """Marginalise full N-qubit counts to a 2-qubit pair.

    ``measured_qubits`` defines the bit positions of the count keys: the
    integer index of an outcome has **bit ``k`` (LSB+k) = state of the
    ``k``-th measured qubit**. This matches ``Simulator``'s
    ``simulate_pmeasure`` ordering when ``format(idx, f'0{n}b')`` is used
    to render the count key as a binary string.

    Returns counts indexed by ``(bb << 1) | ba`` where ``ba`` (bit 0,
    LSB) is the measured outcome on ``pair[0]`` and ``bb`` (bit 1) is the
    outcome on ``pair[1]``. This matches the layout produced by the
    2-qubit reference simulation in :func:`pair_ideal_probs`.
    """
    a, b = int(pair[0]), int(pair[1])
    measured = list(int(q) for q in measured_qubits)
    pos_a = measured.index(a)
    pos_b = measured.index(b)
    n = len(measured)
    out: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    for k, v in counts.items():
        ki = _outcome_to_int(k, n)
        ba = (ki >> pos_a) & 1
        bb = (ki >> pos_b) & 1
        out[(bb << 1) | ba] += int(v)
    return {k: v for k, v in out.items() if v > 0}


def pair_ideal_probs(schedule: Schedule, pair: PairKey) -> np.ndarray:
    """Build and simulate the 2-qubit subcircuit on ``pair``.

    Only the cycle's 1q ops on the pair's two qubits and the CZ on
    that pair (when present in the cycle's pattern) are kept. Returns
    a length-4 probability vector indexed as ``(bb << 1) | ba`` where
    ``ba`` is ``pair[0]``'s outcome and ``bb`` is ``pair[1]``'s — i.e.
    the index has **bit 0 = pair[0]**, **bit 1 = pair[1]**, matching
    the layout produced by :func:`pair_marginal_counts`.
    """
    from uniqc import Circuit
    from uniqc.simulator import Simulator

    a, b = int(pair[0]), int(pair[1])
    region = schedule.region_qubits
    pos_a = region.index(a)
    pos_b = region.index(b)

    c = Circuit()
    for angles, pattern in schedule.cycles:
        ta, pa, la = angles[pos_a]
        tb, pb, lb = angles[pos_b]
        c.u3(0, ta, pa, la)
        c.u3(1, tb, pb, lb)
        if (a, b) in pattern or (b, a) in pattern:
            c.cz(0, 1)
    # measure(0) -> bit 0 of integer index = sim-q0 = pair[0]
    # measure(1) -> bit 1 = sim-q1 = pair[1]
    c.measure(0)
    c.measure(1)
    sim = Simulator(backend_type="statevector")
    return np.asarray(sim.simulate_pmeasure(c.originir), dtype=float)


# ---------------------------------------------------------------------------
# Per-record / per-pair XEB + decay fit
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PairCircuitFit:
    """Per-(record, pair) F_XEB computed on the 2-qubit marginal."""

    record_id: str
    pair: PairKey
    pattern_idx: int
    depth: int
    instance: int
    F_XEB: float
    F_XEB_sigma: float
    shots: float


@dataclasses.dataclass(frozen=True)
class PairDecay:
    """Per-pair weighted log-LS fit ``F(d) = beta · alpha^d``."""

    pair: PairKey
    n_points: int
    alpha: float
    beta: float
    log_alpha: float
    log_beta: float
    sigma_log_alpha: float
    sigma_log_beta: float
    log_residual_std: float


def _record_view(probe: ProbeCircuit | dict, counts: Mapping[Any, int]) -> dict:
    """Normalise either a ``ProbeCircuit`` + counts pair, or a dict view,
    into the dict shape used by the per-pair pipeline."""
    if isinstance(probe, ProbeCircuit):
        return {
            "record_id": probe.record_id,
            "schedule": probe.schedule,
            "pattern_idx": probe.pattern_idx,
            "pattern": probe.pattern,
            "depth": probe.depth,
            "instance": probe.instance,
            "counts": dict(counts),
        }
    out = dict(probe)
    if "counts" not in out:
        out["counts"] = dict(counts)
    return out


def per_pair_F_XEB(
    records: Iterable[dict | ProbeCircuit],
    pairs: Sequence[PairKey],
    *,
    counts_by_record: Mapping[str, Mapping[Any, int]] | None = None,
) -> list[PairCircuitFit]:
    """Compute per-pair F_XEB for every (record, pair) combination.

    Each ``record`` must carry a :class:`Schedule` (under key
    ``"schedule"``) plus ``record_id``, ``pattern_idx``, ``depth``,
    ``instance``. Counts may be embedded under ``"counts"`` or
    supplied via ``counts_by_record`` (keyed by ``record_id``).

    Uses the *normalised* (un-biased at small N) linear XEB estimator

        F = (<P_id>_meas - 1/D) / (Σ P_id² - 1/D)

    which equals ``1`` for the noiseless circuit and ``0`` for a fully
    depolarised pair, regardless of depth-dependent deviations from
    Porter–Thomas. Returns one :class:`PairCircuitFit` per (record,
    pair) where the pair is in the record's ``measured_qubits``.
    """
    out: list[PairCircuitFit] = []
    for r in records:
        if isinstance(r, ProbeCircuit):
            counts = counts_by_record.get(r.record_id, {}) if counts_by_record else {}
            d = _record_view(r, counts)
        else:
            counts = (
                counts_by_record.get(r["record_id"], r.get("counts", {})) if counts_by_record else r.get("counts", {})
            )
            d = _record_view(r, counts)
        sched: Schedule = d["schedule"]
        if not isinstance(sched, Schedule):
            raise TypeError("record['schedule'] must be a Schedule instance")
        measured = sched.measured_qubits
        for pair in pairs:
            if pair[0] not in measured or pair[1] not in measured:
                continue
            ideal = pair_ideal_probs(sched, pair)
            marg = pair_marginal_counts(d["counts"], measured, pair)
            if not marg:
                continue
            shots = float(sum(marg.values()))
            keys = np.fromiter(marg.keys(), dtype=np.int64)
            wts = np.fromiter(marg.values(), dtype=np.float64)
            p_at_keys = ideal[keys]
            mean_p_meas = float(np.dot(wts, p_at_keys) / shots)
            D = float(ideal.size)  # 4 for 2-qubit
            uniform_overlap = 1.0 / D
            ideal_contrast = float(np.dot(ideal, ideal)) - uniform_overlap
            if abs(ideal_contrast) < 1e-12:
                # Ideal distribution is uniform — F is undefined; skip.
                continue
            f_xeb = (mean_p_meas - uniform_overlap) / ideal_contrast
            var_p = float(np.dot(wts, (p_at_keys - mean_p_meas) ** 2) / shots)
            sigma = math.sqrt(max(var_p, 0.0) / shots) / abs(ideal_contrast)
            out.append(
                PairCircuitFit(
                    record_id=str(d["record_id"]),
                    pair=(int(pair[0]), int(pair[1])),
                    pattern_idx=int(d["pattern_idx"]),
                    depth=int(d["depth"]),
                    instance=int(d["instance"]),
                    F_XEB=f_xeb,
                    F_XEB_sigma=sigma,
                    shots=shots,
                )
            )
    return out


def fit_pair_decays(
    fits: Sequence[PairCircuitFit],
    *,
    log_floor: float = 1e-4,
) -> dict[PairKey, PairDecay]:
    """Per-pair weighted log-LS fit of ``F(d) = beta · alpha^d``.

    Drops circuits where ``F <= log_floor`` (cannot take log).
    Weights are ``1/sigma_logF^2`` with ``sigma_logF = sigma_F / F``.
    """
    by_pair: dict[PairKey, list[PairCircuitFit]] = {}
    for f in fits:
        by_pair.setdefault(f.pair, []).append(f)

    out: dict[PairKey, PairDecay] = {}
    for pair, group in by_pair.items():
        depths = np.array([g.depth for g in group], dtype=float)
        Fs = np.array([g.F_XEB for g in group], dtype=float)
        sig = np.array([max(g.F_XEB_sigma, 1e-9) for g in group], dtype=float)
        mask = Fs > log_floor
        if mask.sum() < 2:
            continue
        ds_m, fs_m, sig_m = depths[mask], Fs[mask], sig[mask]
        log_f = np.log(fs_m)
        sig_log = sig_m / fs_m
        w = 1.0 / np.maximum(sig_log, 1e-9) ** 2
        A = np.vstack([ds_m, np.ones_like(ds_m)]).T
        AtWA = A.T @ (w[:, None] * A)
        AtWy = A.T @ (w * log_f)
        try:
            cov = np.linalg.inv(AtWA)
        except np.linalg.LinAlgError:
            continue
        sol = cov @ AtWy
        m, c = float(sol[0]), float(sol[1])
        sigma_m = float(math.sqrt(max(cov[0, 0], 0.0)))
        sigma_c = float(math.sqrt(max(cov[1, 1], 0.0)))
        residuals = log_f - (m * ds_m + c)
        res_std = float(np.std(residuals, ddof=1)) if mask.sum() > 2 else 0.0
        out[pair] = PairDecay(
            pair=pair,
            n_points=int(mask.sum()),
            alpha=float(np.exp(m)),
            beta=float(np.exp(c)),
            log_alpha=m,
            log_beta=c,
            sigma_log_alpha=sigma_m,
            sigma_log_beta=sigma_c,
            log_residual_std=res_std,
        )
    return out


# ---------------------------------------------------------------------------
# Benchmarker
# ---------------------------------------------------------------------------


class ParallelCZBenchmarker:
    """End-to-end parallel-CZ XEB runner.

    Args:
        adapter: A ``QuantumAdapter`` supporting ``submit``/``query`` (and
            optionally ``submit_batch``/``query_batch``). DummyAdapter is
            also supported via its ``simulate_pmeasure`` fast path.
        shots: Number of shots per circuit.
        cache_dir: If supplied, per-pair :class:`XEBResult` objects are
            saved here under the standard naming convention.
        seed: Master seed for the corpus RNG.
        query_timeout: Per-circuit / per-batch poll timeout (seconds).
        query_interval: Poll interval (seconds).
    """

    def __init__(
        self,
        adapter: QuantumAdapter,
        shots: int = 5000,
        cache_dir: str | None = None,
        seed: int | None = None,
        query_timeout: float = 600.0,
        query_interval: float = 2.0,
    ) -> None:
        self.adapter = adapter
        self.shots = int(shots)
        self.cache_dir = cache_dir
        self.seed = 2026 if seed is None else int(seed)
        self.query_timeout = float(query_timeout)
        self.query_interval = float(query_interval)

    # -- public API ------------------------------------------------------

    def run(
        self,
        region_qubits: Sequence[int],
        patterns: Sequence[Sequence[tuple[int, int]]],
        depths: Sequence[int],
        instances: int = 20,
    ) -> dict:
        """Build a corpus, execute it, fit per-pair decays.

        Returns a dict with keys:
          * ``corpus``: list[ProbeCircuit]
          * ``counts_by_record``: dict[record_id, counts]
          * ``per_pair_fits``: list[PairCircuitFit]
          * ``per_pair_decays``: dict[pair, PairDecay]
          * ``per_pair_results``: dict[pair, XEBResult]
        """
        corpus = build_parallel_cz_xeb_corpus(
            region_qubits,
            patterns,
            depths,
            instances,
            seed=self.seed,
        )
        counts_by_record = self._execute(corpus)
        records = [_record_view(pc, counts_by_record.get(pc.record_id, {})) for pc in corpus]
        all_pairs: dict[PairKey, None] = {}
        for pat in patterns:
            for a, b in pat:
                all_pairs.setdefault((int(a), int(b)), None)
        pairs = list(all_pairs.keys())
        fits = per_pair_F_XEB(records, pairs)
        decays = fit_pair_decays(fits)

        backend_name = getattr(self.adapter, "name", None) or type(self.adapter).__name__.lower()
        per_pair_results: dict[PairKey, XEBResult] = {}
        depth_tuple = tuple(int(d) for d in depths)
        ts = _utc_now()
        for pair, decay in decays.items():
            r = XEBResult(
                calibrated_at=ts,
                backend=str(backend_name),
                type="xeb_2q_parallel",
                qubit=None,
                pairs=[pair],
                fidelity_per_layer=float(decay.alpha),
                fidelity_std_error=float(decay.alpha * decay.sigma_log_alpha),
                fit_a=float(decay.beta),
                fit_b=0.0,
                fit_r=float(decay.alpha),
                depths=depth_tuple,
                n_circuits=int(instances),
                shots=self.shots,
            )
            per_pair_results[pair] = r
            if self.cache_dir is not None:
                save_calibration_result(
                    r,
                    type_prefix="xeb_2q_parallel",
                    cache_dir=self.cache_dir,
                )
        return {
            "corpus": corpus,
            "counts_by_record": counts_by_record,
            "per_pair_fits": fits,
            "per_pair_decays": decays,
            "per_pair_results": per_pair_results,
        }

    # -- internal --------------------------------------------------------

    def _execute(self, corpus: Sequence[ProbeCircuit]) -> dict[str, dict[Any, int]]:
        """Run the corpus on the adapter and return a {record_id: counts} map."""
        # DummyAdapter fast path: exact pmeasure -> sample shots locally.
        if hasattr(self.adapter, "simulate_pmeasure"):
            return self._execute_via_pmeasure(corpus)

        # Cloud / generic adapters: prefer batch when available.
        if hasattr(self.adapter, "submit_batch") and hasattr(self.adapter, "query_batch"):
            return self._execute_via_batch(corpus)

        # Fallback: per-circuit submit/query loop.
        out: dict[str, dict[Any, int]] = {}
        for pc in corpus:
            counts = self._submit_and_wait_counts(pc.circuit.originir)
            out[pc.record_id] = counts
        return out

    def _execute_via_pmeasure(self, corpus: Sequence[ProbeCircuit]) -> dict[str, dict[Any, int]]:
        rng = np.random.default_rng(self.seed + 1)
        out: dict[str, dict[Any, int]] = {}
        for pc in corpus:
            probs = np.asarray(
                self.adapter.simulate_pmeasure(pc.circuit.originir),
                dtype=float,
            )
            n_meas = len(pc.schedule.measured_qubits)
            if probs.size == 0:
                out[pc.record_id] = {}
                continue
            probs = probs / probs.sum()
            samples = rng.choice(probs.size, size=self.shots, p=probs)
            keys, vals = np.unique(samples, return_counts=True)
            out[pc.record_id] = {format(int(k), f"0{n_meas}b"): int(v) for k, v in zip(keys, vals)}
        return out

    def _execute_via_batch(self, corpus: Sequence[ProbeCircuit]) -> dict[str, dict[Any, int]]:
        originirs = [pc.circuit.originir for pc in corpus]
        task_ids = self.adapter.submit_batch(originirs, shots=self.shots)
        deadline = time.time() + max(self.query_timeout, self.query_timeout * len(originirs) / 20)
        while True:
            result = self.adapter.query_batch(task_ids)
            status = result.get("status", "")
            if status == "success":
                payload = result.get("result", [])
                if isinstance(payload, dict):
                    payload = [payload]
                if not isinstance(payload, list) or len(payload) != len(corpus):
                    raise RuntimeError(
                        f"Unexpected batch result payload: "
                        f"got {len(payload) if hasattr(payload, '__len__') else '?'}"
                        f" results for {len(corpus)} circuits"
                    )
                return {pc.record_id: dict(p) for pc, p in zip(corpus, payload)}
            if status == "failed":
                raise RuntimeError(f"XEB batch failed: {result.get('result') or result.get('error')}")
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for XEB batch task(s) {task_ids}")
            time.sleep(self.query_interval)

    def _submit_and_wait_counts(self, originir: str) -> dict[Any, int]:
        task_id = self.adapter.submit(originir, shots=self.shots)
        deadline = time.time() + self.query_timeout
        while True:
            result = self.adapter.query(task_id)
            status = result.get("status", "")
            if status == "success":
                raw = result.get("result", {})
                if hasattr(raw, "counts"):
                    return raw.counts
                if isinstance(raw, dict):
                    return raw
                return {}
            if status == "failed":
                raise RuntimeError(f"XEB circuit failed: {result.get('result') or result.get('error')}")
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for XEB task {task_id}")
            time.sleep(self.query_interval)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
