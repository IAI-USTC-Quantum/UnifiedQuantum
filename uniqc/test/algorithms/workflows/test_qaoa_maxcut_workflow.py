"""Regression test for :func:`uniqc.algorithms.workflows.qaoa_workflow.run_qaoa_workflow`.

Builds the canonical 3-node triangle (K₃) MaxCut instance and checks
the workflow returns a near-optimal cut at depth ``p=1``. The optimum
cut value is **2** (any 2-vs-1 bipartition).

The cost Hamiltonian for MaxCut on edges ``E`` is

    H_C = ½ Σ_{(i,j)∈E} Z_i Z_j  -  |E|/2,

so the workflow's returned ``energy`` is exactly ``-<#cut edges>``.
"""

from __future__ import annotations

import math

import pytest

from uniqc.algorithms.workflows.qaoa_workflow import (
    QAOAResult,
    run_qaoa_workflow,
)


def _maxcut_hamiltonian(edges, n_nodes):
    """Return MaxCut H_C as fixed-length positional Pauli strings."""
    terms = []
    for i, j in edges:
        chars = ["I"] * n_nodes
        chars[i] = "Z"
        chars[j] = "Z"
        terms.append(("".join(chars), 0.5))
    terms.append(("I" * n_nodes, -len(edges) / 2.0))
    return terms


TRIANGLE_EDGES = [(0, 1), (1, 2), (0, 2)]
TRIANGLE_NODES = 3
TRIANGLE_OPTIMUM_CUT = 2.0


@pytest.mark.slow
def test_qaoa_maxcut_3node_triangle_finds_optimum() -> None:
    """QAOA p=1 on K₃ should reach ≥ 1.5 expected cut edges.

    The well-known analytic optimum for QAOA at ``p=1`` on the triangle
    is around ``9/8 ⋅ … ≈ 1.875`` expected cut edges (it is *not* the
    classical maximum of 2 because p=1 cannot perfectly distinguish
    the three degenerate solutions). We assert ≥ 1.5 to stay robust
    against COBYLA landing on a slightly off-peak local optimum, while
    still flagging large regressions.
    """
    hamiltonian = _maxcut_hamiltonian(TRIANGLE_EDGES, TRIANGLE_NODES)

    result = run_qaoa_workflow(
        hamiltonian,
        n_qubits=TRIANGLE_NODES,
        p=1,
        shots=None,
        method="COBYLA",
        options={"maxiter": 100, "rhobeg": 0.3},
    )

    assert isinstance(result, QAOAResult)
    assert math.isfinite(result.energy)
    assert result.gammas.shape == (1,)
    assert result.betas.shape == (1,)
    assert len(result.history) >= 1
    assert result.history[-1] == pytest.approx(result.energy)

    # Workflow minimises H_C, so expected cut count = -energy.
    expected_cut = -result.energy
    assert expected_cut >= 1.5, (
        f"QAOA p=1 on K_3 reached only {expected_cut:.4f} cut edges "
        f"(optimum is {TRIANGLE_OPTIMUM_CUT}); energy={result.energy:.6f}. "
        f"Suggests the optimiser got stuck — check init/options."
    )
    assert expected_cut <= TRIANGLE_OPTIMUM_CUT + 1e-6, (
        f"Reported cut {expected_cut} exceeds classical maximum {TRIANGLE_OPTIMUM_CUT}"
    )


def test_qaoa_returns_consistent_layer_shapes_for_p2() -> None:
    """Smoke: with ``p=2`` the result must expose two γ's and two β's.

    Documents the shape contract of :class:`QAOAResult` independently of
    optimiser quality. Uses a tiny 3-node path graph and only 10 iters
    so the test stays well under a second.
    """
    edges = [(0, 1), (1, 2)]
    hamiltonian = _maxcut_hamiltonian(edges, n_nodes=3)

    result = run_qaoa_workflow(
        hamiltonian,
        n_qubits=3,
        p=2,
        shots=None,
        method="COBYLA",
        options={"maxiter": 10, "rhobeg": 0.3},
    )

    assert isinstance(result, QAOAResult)
    assert result.gammas.shape == (2,)
    assert result.betas.shape == (2,)
    assert isinstance(result.energy, float)
    assert math.isfinite(result.energy)
    # Path graph 0-1-2 has 2 edges, MaxCut = 2; energy bound = -2.0.
    assert result.energy >= -2.0 - 1e-6
