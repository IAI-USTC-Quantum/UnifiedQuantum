"""Matrix-Product-State (MPS) simulator for nearest-neighbour 1D circuits.

This is a pure-NumPy MPS simulator suitable for circuits whose entanglement
stays bounded by a moderate bond dimension. Compared to the C++
``OriginIR_Simulator`` it trades off generality for *scale*: an open-boundary
qubit chain at ``chi_max=64`` and N=64 qubits is comfortably tractable here
while a dense statevector at the same N is not.

When to use this simulator
--------------------------
- 1D / line topology circuits where every two-qubit gate is between
  consecutive qubits (qubit ``q`` and qubit ``q+1``).
- Low-to-moderate entanglement growth (e.g. shallow brick-work, dynamical
  simulation of local Hamiltonians, single-excitation propagation).
- Sampling from a chip-shaped circuit that you have already compiled into a
  nearest-neighbour 1D chain.

When NOT to use this simulator
------------------------------
- Long-range two-qubit gates. They are *refused* (rather than swap-routed
  silently). Compile to NN first, or use the dense ``OriginIR_Simulator``.
- Circuits that need ``CONTROL ... ENDCONTROL`` blocks. Decompose to native
  gates first.
- Noise simulation. The MPS path is currently noiseless; route noisy work
  through ``OriginIR_NoisySimulator`` or ``dummy:<platform>:<chip>``.

Public API
----------
- :class:`MPSConfig` — bond / cutoff / seed configuration.
- :class:`MPSSimulator` — front-end with the ``simulate_pmeasure`` /
  ``simulate_shots`` / ``simulate_statevector`` surface used elsewhere in
  ``uniqc.simulator``.

The simulator does *not* inherit :class:`uniqc.simulator.base_simulator.BaseSimulator`
so as to avoid the eager C++ ``OpcodeSimulator`` import and to keep the
qubit indexing 1:1 with the parsed OriginIR (no encounter-order remapping).
"""

from __future__ import annotations

__all__ = ["MPSConfig", "MPSSimulator"]

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class MPSConfig:
    """Configuration for :class:`MPSSimulator`.

    Attributes:
        chi_max: Maximum bond dimension after each two-qubit SVD truncation.
            Larger ``chi_max`` is more accurate but quadratically more
            memory-intensive and cubically more compute-intensive per gate.
        svd_cutoff: Singular-value cutoff (relative to the spectrum norm)
            below which Schmidt values are dropped even if ``chi_max`` is
            not yet reached.
        seed: Optional RNG seed used by :meth:`MPSSimulator.simulate_shots`.
    """

    chi_max: int = 64
    svd_cutoff: float = 1e-12
    seed: int | None = None


# ---------------------------------------------------------------------------
# Gate matrices
# ---------------------------------------------------------------------------


def _u1(name: str, params: Sequence[float], dagger: bool = False) -> np.ndarray:
    """Return the 2x2 matrix of a 1-qubit gate, conjugate-transposed if ``dagger``."""
    name = name.upper()
    if name == "I":
        u = np.eye(2, dtype=complex)
    elif name == "H":
        u = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
    elif name == "X":
        u = np.array([[0, 1], [1, 0]], dtype=complex)
    elif name == "Y":
        u = np.array([[0, -1j], [1j, 0]], dtype=complex)
    elif name == "Z":
        u = np.array([[1, 0], [0, -1]], dtype=complex)
    elif name == "S":
        u = np.array([[1, 0], [0, 1j]], dtype=complex)
    elif name == "T":
        u = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
    elif name == "SX":
        # SX = sqrt(X) = (1/2) [[1+i, 1-i], [1-i, 1+i]]
        u = 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex)
    elif name == "RX":
        (a,) = _floats(params)
        c, s = math.cos(a / 2), math.sin(a / 2)
        u = np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)
    elif name == "RY":
        (a,) = _floats(params)
        c, s = math.cos(a / 2), math.sin(a / 2)
        u = np.array([[c, -s], [s, c]], dtype=complex)
    elif name == "RZ":
        (a,) = _floats(params)
        u = np.array([[np.exp(-1j * a / 2), 0], [0, np.exp(1j * a / 2)]], dtype=complex)
    elif name in ("U1", "P"):
        (a,) = _floats(params)
        u = np.array([[1, 0], [0, np.exp(1j * a)]], dtype=complex)
    elif name == "U2":
        phi, lam = _floats(params)
        u = (1 / np.sqrt(2)) * np.array(
            [[1, -np.exp(1j * lam)],
             [np.exp(1j * phi), np.exp(1j * (phi + lam))]],
            dtype=complex,
        )
    elif name == "U3":
        th, phi, lam = _floats(params)
        c, s = math.cos(th / 2), math.sin(th / 2)
        u = np.array(
            [[c, -np.exp(1j * lam) * s],
             [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]],
            dtype=complex,
        )
    elif name in ("RPHI", "RPhi"):
        # RPhi(theta, phi) = cos(theta/2) I - i sin(theta/2) (cos(phi) X + sin(phi) Y)
        theta, phi = _floats(params)
        c, s = math.cos(theta / 2), math.sin(theta / 2)
        u = np.array(
            [[c, -1j * s * (math.cos(phi) - 1j * math.sin(phi))],
             [-1j * s * (math.cos(phi) + 1j * math.sin(phi)), c]],
            dtype=complex,
        )
    elif name == "RPHI90":
        # 90-degree rotation about axis cos(phi) X + sin(phi) Y
        (phi,) = _floats(params)
        u = _u1("RPhi", [math.pi / 2, phi])
    elif name == "RPHI180":
        (phi,) = _floats(params)
        u = _u1("RPhi", [math.pi, phi])
    else:
        raise ValueError(f"MPSSimulator: unsupported 1-qubit gate '{name}'")
    return u.conj().T if dagger else u


def _u2(name: str, params: Sequence[float], dagger: bool = False) -> np.ndarray:
    """Return the 4x4 matrix of a NN 2-qubit gate (qubit-a is the high-order leg).

    The matrix is on the basis ``|s_a s_b>`` with ``s_a`` the leftmost bit.
    """
    name = name.upper()
    if name in ("CX", "CNOT"):
        u = np.eye(4, dtype=complex)
        u[2, 2], u[2, 3], u[3, 2], u[3, 3] = 0, 1, 1, 0
    elif name == "CZ":
        u = np.diag([1, 1, 1, -1]).astype(complex)
    elif name == "CY":
        u = np.eye(4, dtype=complex)
        u[2, 2] = u[3, 3] = 0
        u[2, 3] = -1j
        u[3, 2] = 1j
    elif name == "SWAP":
        u = np.eye(4, dtype=complex)
        u[1, 1] = u[2, 2] = 0
        u[1, 2] = u[2, 1] = 1
    elif name == "ISWAP":
        u = np.eye(4, dtype=complex)
        u[1, 1] = u[2, 2] = 0
        u[1, 2] = u[2, 1] = 1j
    elif name in ("CR", "CPHASE", "CRZ"):
        (a,) = _floats(params)
        u = np.diag([1, 1, 1, np.exp(1j * a)]).astype(complex)
    elif name in ("XX", "RXX"):
        # exp(-i theta/2 X⊗X)
        (a,) = _floats(params)
        c, s = math.cos(a / 2), math.sin(a / 2)
        u = np.array([
            [c, 0, 0, -1j * s],
            [0, c, -1j * s, 0],
            [0, -1j * s, c, 0],
            [-1j * s, 0, 0, c],
        ], dtype=complex)
    elif name in ("YY", "RYY"):
        # exp(-i theta/2 Y⊗Y)
        (a,) = _floats(params)
        c, s = math.cos(a / 2), math.sin(a / 2)
        u = np.array([
            [c, 0, 0, 1j * s],
            [0, c, -1j * s, 0],
            [0, -1j * s, c, 0],
            [1j * s, 0, 0, c],
        ], dtype=complex)
    elif name in ("ZZ", "RZZ"):
        # exp(-i theta/2 Z⊗Z)
        (a,) = _floats(params)
        e_p = np.exp(1j * a / 2)
        e_m = np.exp(-1j * a / 2)
        u = np.diag([e_m, e_p, e_p, e_m]).astype(complex)
    elif name == "XY":
        # exp(-i theta/2 (X⊗X + Y⊗Y) / 2)
        (a,) = _floats(params)
        c, s = math.cos(a / 2), math.sin(a / 2)
        u = np.array([
            [1, 0, 0, 0],
            [0, c, -1j * s, 0],
            [0, -1j * s, c, 0],
            [0, 0, 0, 1],
        ], dtype=complex)
    elif name == "ECR":
        # Echoed cross-resonance: (1/sqrt(2)) * (IX - iZX)
        # Matrix form per Qiskit convention.
        s = 1.0 / math.sqrt(2.0)
        u = s * np.array([
            [0, 0, 1, 1j],
            [0, 0, 1j, 1],
            [1, -1j, 0, 0],
            [-1j, 1, 0, 0],
        ], dtype=complex)
    elif name == "PHASE2Q":
        # 2-qubit phase gate with three diagonal phases (uniqc convention):
        # diag(1, e^{i p1}, e^{i p2}, e^{i p3})
        ps = _floats(params)
        if len(ps) != 3:
            raise ValueError(
                f"MPSSimulator: PHASE2Q requires 3 parameters, got {len(ps)}."
            )
        u = np.diag([1.0, np.exp(1j * ps[0]), np.exp(1j * ps[1]), np.exp(1j * ps[2])]).astype(complex)
    else:
        raise ValueError(
            f"MPSSimulator: unsupported 2-qubit gate '{name}'. Supported: "
            "CNOT/CX, CZ, CY, SWAP, ISWAP, ECR, CR/CPHASE/CRZ, XX, YY, ZZ, XY, PHASE2Q."
        )
    return u.conj().T if dagger else u


def _floats(params) -> list[float]:
    if params is None:
        return []
    if isinstance(params, (int, float)):
        return [float(params)]
    return [float(p) for p in params]


# Names that we never want to apply as gates. ``MEASURE`` is consumed
# elsewhere; the rest are circuit-level annotations.
_PASSTHROUGH_OPS = {"BARRIER", "I", "QINIT", "CREG", "MEASURE", "RESET"}


# ---------------------------------------------------------------------------
# MPS engine
# ---------------------------------------------------------------------------


@dataclass
class _MPSState:
    """Open-boundary, qubit-only (d=2) MPS state.

    Each ``tensors[i]`` has shape ``(chi_left, 2, chi_right)``; boundary
    bonds are 1.
    """

    n_qubits: int
    chi_max: int = 64
    svd_cutoff: float = 1e-12
    tensors: list[np.ndarray] = field(default_factory=list, init=False, repr=False)
    truncation_errors: list[float] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.n_qubits < 1:
            raise ValueError("n_qubits must be >= 1")
        self.tensors = []
        for _ in range(self.n_qubits):
            t = np.zeros((1, 2, 1), dtype=complex)
            t[0, 0, 0] = 1.0
            self.tensors.append(t)

    @property
    def max_bond(self) -> int:
        if self.n_qubits <= 1:
            return 1
        return max(t.shape[2] for t in self.tensors[:-1])

    # ---- gate application ----

    def apply_1q(self, U: np.ndarray, site: int) -> None:
        if U.shape != (2, 2):
            raise ValueError("1q gate must be 2x2")
        A = self.tensors[site]
        self.tensors[site] = np.einsum("ij,ajb->aib", U, A, optimize=True)

    def apply_2q(self, U: np.ndarray, left_site: int) -> None:
        """Apply 4x4 ``U`` on consecutive sites ``(left_site, left_site+1)``.

        ``U`` is on the basis ``|s_left s_right>`` with ``s_left`` the
        leftmost (high-order) bit, matching the convention of :func:`_u2`.
        """
        n = self.n_qubits
        if not (0 <= left_site < n - 1):
            raise ValueError(f"2q gate site {left_site} out of range [0, {n - 2}]")
        if U.shape != (4, 4):
            raise ValueError("2q gate must be 4x4")

        A, B = self.tensors[left_site], self.tensors[left_site + 1]
        chi_l = A.shape[0]
        chi_r = B.shape[2]

        # theta_{l, s1, s2, r}
        theta = np.einsum("lsm,mtr->lstr", A, B, optimize=True)
        # Reshape U → (s1', s2', s1, s2)
        Uten = U.reshape(2, 2, 2, 2)
        theta = np.einsum("xyst,lstr->lxyr", Uten, theta, optimize=True)

        mat = theta.reshape(chi_l * 2, 2 * chi_r)
        try:
            u, s, vh = np.linalg.svd(mat, full_matrices=False)
        except np.linalg.LinAlgError:
            # Tiny perturbation + retry — extremely rare on physically-meaningful states.
            u, s, vh = np.linalg.svd(
                mat + 1e-15 * np.random.default_rng(0).standard_normal(mat.shape),
                full_matrices=False,
            )

        norm = float(np.linalg.norm(s))
        if norm == 0:
            keep = 1
        else:
            keep = int(np.sum(s / norm > self.svd_cutoff))
            keep = max(1, min(keep, self.chi_max, len(s)))

        truncated = float(np.sum(s[keep:] ** 2)) if keep < len(s) else 0.0
        self.truncation_errors.append(truncated)

        u, s, vh = u[:, :keep], s[:keep], vh[:keep, :]
        if norm > 0:
            s = s * (norm / float(np.linalg.norm(s)))

        new_A = u.reshape(chi_l, 2, keep)
        new_B = (np.diag(s) @ vh).reshape(keep, 2, chi_r)
        self.tensors[left_site] = new_A
        self.tensors[left_site + 1] = new_B

    # ---- observables ----

    def amplitude(self, bits: Sequence[int]) -> complex:
        if len(bits) != self.n_qubits:
            raise ValueError("bits length must equal n_qubits")
        v = np.array([[1.0 + 0j]])
        for i, b in enumerate(bits):
            v = v @ self.tensors[i][:, int(b), :]
        return complex(v[0, 0])

    def probability(self, bits: Sequence[int]) -> float:
        return float(abs(self.amplitude(bits)) ** 2)

    def norm(self) -> float:
        E = np.array([[1.0 + 0j]])
        for A in self.tensors:
            E = np.einsum("ac,axb,cxd->bd", E, np.conj(A), A, optimize=True)
        return float(np.real(E[0, 0]))

    # ---- sampling ----

    def sample_one(self, rng: np.random.Generator) -> tuple[list[int], float]:
        bits: list[int] = []
        prob = 1.0
        E_left = np.array([[1.0 + 0j]])
        for i, A in enumerate(self.tensors):
            R = self._right_env(i + 1)
            margs = np.zeros(2)
            for b in (0, 1):
                Ab = A[:, b, :]
                tmp = np.einsum("ac,ax->cx", E_left, np.conj(Ab))
                m = np.einsum("cx,cy,xy->", tmp, Ab, R, optimize=True)
                margs[b] = float(np.real(m))
            tot = margs.sum()
            p0 = margs[0] / tot if tot > 0 else 0.5
            r = rng.random()
            b = 0 if r < p0 else 1
            p_b = margs[b] / tot if tot > 0 else 0.5
            prob *= p_b
            bits.append(b)
            Ab = A[:, b, :]
            E_left = np.einsum("ac,ax,cy->xy", E_left, np.conj(Ab), Ab, optimize=True)
            tr = float(np.real(np.trace(E_left)))
            if tr > 0:
                E_left = E_left / tr
        return bits, prob

    def _right_env(self, start: int) -> np.ndarray:
        n = self.n_qubits
        if start >= n:
            return np.array([[1.0 + 0j]])
        E = np.array([[1.0 + 0j]])
        for i in range(n - 1, start - 1, -1):
            A = self.tensors[i]
            E = np.einsum("axb,bd,cxd->ac", np.conj(A), E, A, optimize=True)
        return E

    # ---- materialisation (small N only) ----

    def to_statevector(self) -> np.ndarray:
        """Contract the MPS into a length-``2**n`` statevector.

        Index convention matches :class:`uniqc.simulator.OriginIR_Simulator`:
        the integer index ``i`` encodes bits with qubit 0 as the LSB.
        """
        # Build C[s_0, s_1, ..., s_{n-1}] by sequential contraction.
        block = self.tensors[0][0]  # (2, chi_1)
        for i in range(1, self.n_qubits):
            # block: (..., chi_left)  -- absorb tensor i: (chi_left, 2, chi_right)
            block = np.einsum("...l,lsr->...sr", block, self.tensors[i])
        # Now block has shape (2, 2, ..., 2, 1). Drop trailing 1 and flatten.
        block = block.reshape((2,) * self.n_qubits)
        # Convention: state index i has bit q at position q (LSB = q0).
        # Numpy reshape order means tensor axis 0 = qubit 0, axis n-1 = qubit n-1.
        # The default flatten with 'C' order makes axis 0 the *most significant*,
        # which is the opposite of our convention. Reverse axes to put qubit 0
        # as the slowest-varying (i.e. MSB) -> then 'C' flatten -> q0 = MSB.
        # We actually want q0 = LSB, so transpose to put qubit n-1 first.
        block = block.transpose(*reversed(range(self.n_qubits)))
        return block.reshape(-1).astype(complex)


# ---------------------------------------------------------------------------
# Front-end matching the BaseSimulator surface
# ---------------------------------------------------------------------------


# Hard cap so we never silently materialise an exponentially-large vector.
_PMEASURE_QUBIT_LIMIT = 24


class MPSSimulator:
    """OriginIR-driven MPS simulator with the same call surface as
    :class:`uniqc.simulator.OriginIR_Simulator`.

    Unlike that class, this simulator:

    - is pure NumPy (no C++ extension required);
    - operates on qubits ``[0..n-1]`` exactly as written in OriginIR (no
      least-qubit remapping); the qubit count comes from ``QINIT``;
    - refuses long-range two-qubit gates (use the dense simulator or
      compile to NN first);
    - refuses ``CONTROL ... ENDCONTROL`` blocks and ``DAGGER`` blocks
      around unsupported gates (the per-gate ``dagger`` flag *is* honoured);
    - has no noise model.

    Args:
        config: Bond / cutoff / seed configuration.
        chi_max: Convenience override for ``config.chi_max`` when ``config``
            is not supplied.
        svd_cutoff: Convenience override for ``config.svd_cutoff``.
        seed: Convenience override for ``config.seed``.
        available_qubits: Optional list of allowed qubit indices. If set,
            any opcode touching a qubit outside the list raises.
        available_topology: Optional list of allowed ``[u, v]`` edges. If
            set, NN gates that violate this list raise (this lets the same
            instance enforce a virtual-line / chip-shaped chain).
    """

    def __init__(
        self,
        config: MPSConfig | None = None,
        *,
        chi_max: int | None = None,
        svd_cutoff: float | None = None,
        seed: int | None = None,
        available_qubits: list[int] | None = None,
        available_topology: list[list[int]] | None = None,
    ) -> None:
        if config is None:
            config = MPSConfig()
        if chi_max is not None:
            config = MPSConfig(chi_max=chi_max, svd_cutoff=config.svd_cutoff, seed=config.seed)
        if svd_cutoff is not None:
            config = MPSConfig(chi_max=config.chi_max, svd_cutoff=svd_cutoff, seed=config.seed)
        if seed is not None:
            config = MPSConfig(chi_max=config.chi_max, svd_cutoff=config.svd_cutoff, seed=seed)
        self.config = config
        self.available_qubits = list(available_qubits) if available_qubits is not None else None
        self.available_topology = (
            [[int(e[0]), int(e[1])] for e in available_topology]
            if available_topology is not None
            else None
        )
        self.parser: OriginIR_BaseParser | None = None
        self._state: _MPSState | None = None
        self._measure_qubits: list[int] = []

    # ---- public surface ----

    @property
    def qubit_num(self) -> int:
        return self._state.n_qubits if self._state is not None else 0

    @property
    def truncation_errors(self) -> list[float]:
        return self._state.truncation_errors if self._state is not None else []

    @property
    def max_bond(self) -> int:
        return self._state.max_bond if self._state is not None else 1

    def simulate_pmeasure(self, originir: str) -> list[float]:
        """Return exact measurement probabilities, length ``2 ** k`` where
        ``k`` is the number of *measured* qubits (or all qubits if no
        ``MEASURE`` was issued).

        Index convention: bit ``j`` of the integer index corresponds to the
        ``j``-th measured qubit (in the order they appear in the result of
        :func:`_measure_order`), with qubit 0 being the LSB. This matches
        :meth:`uniqc.simulator.OriginIR_Simulator.simulate_pmeasure`.

        For circuits with > 24 measured qubits this method raises — the
        dense probability vector would be infeasibly large. Use
        :meth:`simulate_shots` instead.
        """
        self._run(originir)
        measured = self._measure_order()
        if len(measured) > _PMEASURE_QUBIT_LIMIT:
            raise ValueError(
                f"MPSSimulator.simulate_pmeasure refuses to materialise a "
                f"2**{len(measured)} probability vector. Use simulate_shots."
            )
        return self._dense_pmeasure(measured)

    def simulate_shots(self, originir: str, shots: int) -> dict[int, int]:
        """Sample ``shots`` measurement outcomes by per-site MPS sampling.

        Returns a ``{int: count}`` dict matching
        :meth:`uniqc.simulator.OriginIR_Simulator.simulate_shots`. The
        integer key encodes bits with the first measured qubit as the LSB.

        This routes through :meth:`_MPSState.sample_one` (cost
        ``O(N * chi^3)`` per shot) so it stays tractable for large ``N``.
        """
        self._run(originir)
        measured = self._measure_order()
        rng = np.random.default_rng(self.config.seed)
        counts: dict[int, int] = {}
        for _ in range(shots):
            bits, _ = self._state.sample_one(rng)
            value = 0
            for idx, q in enumerate(measured):
                if bits[q]:
                    value |= 1 << idx
            counts[value] = counts.get(value, 0) + 1
        return counts

    def simulate_statevector(self, originir: str) -> np.ndarray:
        """Materialise the full statevector. Only feasible for small ``n``."""
        self._run(originir)
        if self._state.n_qubits > _PMEASURE_QUBIT_LIMIT:
            raise ValueError(
                f"MPSSimulator.simulate_statevector refuses N={self._state.n_qubits}. "
                f"Use simulate_shots or read out local observables instead."
            )
        return self._state.to_statevector()

    # ---- internals ----

    def _run(self, originir: str) -> None:
        self.parser = OriginIR_BaseParser()
        self.parser.parse(originir)
        n = self.parser.n_qubit
        if n is None or n < 1:
            raise ValueError("OriginIR is missing a valid QINIT statement")

        if self.available_qubits is not None:
            allowed = set(self.available_qubits)
            for op in self.parser.program_body:
                _, qubit, _, _, _, _ = op
                qs = qubit if isinstance(qubit, list) else [qubit] if qubit is not None else []
                for q in qs:
                    if int(q) not in allowed:
                        raise ValueError(
                            f"MPSSimulator: qubit {q} not in available_qubits={sorted(allowed)}"
                        )

        self._state = _MPSState(
            n_qubits=n,
            chi_max=self.config.chi_max,
            svd_cutoff=self.config.svd_cutoff,
        )

        for op in self.parser.program_body:
            self._dispatch(op)

        self._measure_qubits = [q for q, _ in self.parser.measure_qubits]

    def _dispatch(self, opcode) -> None:
        operation, qubit, _cbit, parameter, dagger_flag, control_qubits_set = opcode
        op_name = (operation or "").upper()

        if op_name in _PASSTHROUGH_OPS:
            return

        if control_qubits_set:
            raise NotImplementedError(
                f"MPSSimulator does not support CONTROL blocks (gate '{operation}'). "
                "Decompose to native gates first."
            )

        if isinstance(qubit, list):
            if len(qubit) != 2:
                raise NotImplementedError(
                    f"MPSSimulator only supports 1q and NN 2q gates; got {operation} on {qubit}"
                )
            a, b = int(qubit[0]), int(qubit[1])
            if abs(a - b) != 1:
                raise ValueError(
                    f"MPSSimulator: long-range 2q gate '{operation}' on ({a},{b}) is not "
                    "supported. Compile to nearest-neighbour first or use OriginIR_Simulator."
                )
            if self.available_topology is not None:
                if [a, b] not in self.available_topology and [b, a] not in self.available_topology:
                    raise ValueError(
                        f"MPSSimulator: gate '{operation}' on ({a},{b}) violates available_topology"
                    )
            U = _u2(op_name, parameter, dagger=bool(dagger_flag))
            if a < b:
                left = a
            else:
                # Swap leg order in U so it acts on (left=b, right=a) = (smaller, larger).
                P = np.eye(4, dtype=complex)[[0, 2, 1, 3]]
                U = P @ U @ P
                left = b
            self._state.apply_2q(U, left)
        else:
            if qubit is None:
                return
            U = _u1(op_name, parameter, dagger=bool(dagger_flag))
            self._state.apply_1q(U, int(qubit))

    def _measure_order(self) -> list[int]:
        """Return the qubit indices in the order their cbit appears.

        If no ``MEASURE`` is issued, fall back to all qubits ``[0..n-1]``.
        Matches the BaseSimulator behaviour of sorting by cbit.
        """
        measure = self.parser.measure_qubits if self.parser is not None else []
        if measure:
            return [q for q, _c in sorted(measure, key=lambda kv: kv[1])]
        return list(range(self._state.n_qubits))

    def _dense_pmeasure(self, measured: list[int]) -> list[float]:
        """Compute exact marginal probabilities over ``measured`` qubits.

        For ``n - len(measured)`` traced-out qubits we sum ``|amp|^2`` over
        all configurations of the un-measured qubits. The total cost scales
        as ``2**n * O(n)`` worst-case, which is why the public method caps
        at ``len(measured) <= 24`` (and we additionally avoid this by
        materialising the dense statevector once).
        """
        n = self._state.n_qubits
        if len(measured) == n and sorted(measured) == list(range(n)):
            psi = self._state.to_statevector()
            return [float(abs(a) ** 2) for a in psi]

        # General case: contract once to dense, then marginalise.
        # We accept the 2**n cost because we already gated on
        # len(measured) <= 24 above.
        psi = self._state.to_statevector()
        probs_full = np.abs(psi) ** 2

        k = len(measured)
        out = np.zeros(1 << k, dtype=float)
        for state_int, p in enumerate(probs_full):
            value = 0
            for idx, q in enumerate(measured):
                if (state_int >> q) & 1:
                    value |= 1 << idx
            out[value] += p
        return [float(x) for x in out]
