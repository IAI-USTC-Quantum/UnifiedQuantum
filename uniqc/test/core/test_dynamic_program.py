"""Tests for the structured dynamic-program extension (mid-circuit MEASURE,
RESET, classical assignment/expressions, QIF/ELSE/ENDQIF, QWHILE/ENDQWHILE).
"""

from __future__ import annotations

import numpy as np
import pytest

from uniqc.circuit_builder import Circuit
from uniqc.circuit_builder.dynamic_program import (
    BinExpr,
    ConstExpr,
    MemExpr,
    parse_expr,
)
from uniqc.exceptions import CircuitTranslationError
from uniqc.simulator import (
    DynamicProgramExecutor,
    LoopWatchdogError,
    simulate_dynamic,
)

# ─── Classical expression parser ──────────────────────────────────────


class TestExprParser:
    def test_parse_arithmetic_precedence(self):
        e = parse_expr("a + b * 2")
        assert e.evaluate({"a": 1, "b": 3}) == 7

    def test_parse_comparison_and_logical(self):
        e = parse_expr("a == 1 && b != 0")
        assert e.evaluate({"a": 1, "b": 5}) == 1
        assert e.evaluate({"a": 0, "b": 5}) == 0

    def test_parse_unary_minus_and_not(self):
        assert parse_expr("-x").evaluate({"x": 5}) == -5
        assert parse_expr("!x").evaluate({"x": 0}) == 1
        assert parse_expr("!x").evaluate({"x": 3}) == 0

    def test_parse_parentheses(self):
        assert parse_expr("(1 + 2) * 3").evaluate({}) == 9

    def test_to_str_round_trip(self):
        e = parse_expr("a + b * 2 == 10 && !c")
        e2 = parse_expr(e.to_str())
        assert e2.to_str() == e.to_str()

    def test_unknown_memory_raises(self):
        with pytest.raises(KeyError):
            MemExpr("nope").evaluate({})

    def test_division_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            parse_expr("a / b").evaluate({"a": 1, "b": 0})

    def test_const_expr(self):
        assert ConstExpr(42).evaluate({}) == 42

    def test_bin_expr_direct(self):
        e = BinExpr("+", ConstExpr(1), ConstExpr(2))
        assert e.evaluate({}) == 3


# ─── Circuit builder API for dynamic programs ─────────────────────────


class TestCircuitDynamicBuilders:
    def test_declare_memory_duplicate_raises(self):
        c = Circuit()
        c.declare_memory("m", 0)
        with pytest.raises(ValueError, match="already declared"):
            c.declare_memory("m", 1)

    def test_cmeasure_requires_declared_memory(self):
        c = Circuit()
        c.h(0)
        with pytest.raises(ValueError, match="not declared"):
            c.cmeasure(0, "m")

    def test_cassign_requires_declared_memory(self):
        c = Circuit()
        with pytest.raises(ValueError, match="not declared"):
            c.cassign("m", "1")

    def test_qelse_without_qif_raises(self):
        c = Circuit()
        c.declare_memory("m", 0)
        with pytest.raises(ValueError, match="matching open qif"):
            c.qelse()

    def test_endqif_without_qif_raises(self):
        c = Circuit()
        with pytest.raises(ValueError, match="matching open qif"):
            c.endqif()

    def test_endqwhile_without_qwhile_raises(self):
        c = Circuit()
        with pytest.raises(ValueError, match="matching open qwhile"):
            c.endqwhile()

    def test_measure_inside_qif_block_raises(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.qif("m == 0")
        with pytest.raises(ValueError, match="QIF/QWHILE"):
            c.measure(0)

    def test_gate_mirrors_into_dynamic_body(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)  # ordinary gate before any dynamic construct
        c.cmeasure(0, "m")
        c.x(1)  # ordinary gate after dynamic mode is active
        assert c.dynamic_program is not None
        # First two nodes: GateNode(H), CMeasureNode; third: GateNode(X).
        from uniqc.circuit_builder.dynamic_program import CMeasureNode, GateNode

        assert isinstance(c.dynamic_program[0], GateNode)
        assert c.dynamic_program[0].opcode[0] == "H"
        assert isinstance(c.dynamic_program[1], CMeasureNode)
        assert isinstance(c.dynamic_program[2], GateNode)
        assert c.dynamic_program[2].opcode[0] == "X"


# ─── Serialization / parsing round trip ───────────────────────────────


class TestDynamicSerializationRoundTrip:
    def test_qif_else_round_trip(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        c.qelse()
        c.z(1)
        c.endqif()
        c.measure(1)

        text = c.originir
        c2 = Circuit.from_originir(text)
        assert c2.originir == text

    def test_qwhile_round_trip(self):
        c = Circuit()
        c.declare_memory("i", 0)
        c.qwhile("i < 3", max_iterations=50)
        c.x(0)
        c.cassign("i", "i + 1")
        c.endqwhile()

        text = c.originir
        assert "QWHILE (i < 3), 50" in text
        c2 = Circuit.from_originir(text)
        assert c2.originir == text

    def test_nested_qif_inside_qwhile_round_trip(self):
        c = Circuit()
        c.declare_memory("i", 0)
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        c.qwhile("i < 3")
        c.x(1)
        c.cassign("i", "i + 1")
        c.qif("m == 1")
        c.z(2)
        c.endqif()
        c.endqwhile()
        c.measure(1)

        text = c.originir
        c2 = Circuit.from_originir(text)
        assert c2.originir == text
        # Structural sanity: nested IfNode inside WhileNode body.
        from uniqc.circuit_builder.dynamic_program import IfNode, WhileNode

        while_node = next(n for n in c2.dynamic_program if isinstance(n, WhileNode))
        assert any(isinstance(n, IfNode) for n in while_node.body)

    def test_controlled_qram_inside_dynamic_program_round_trip(self):
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.declare_memory("m", 0)
        c.h(0)
        c.x(3)
        c.qram_call("r", 0, 1, 2, control_qubits=3)
        c.cmeasure(3, "m")

        text = c.originir
        assert "controlled_by (q[3])" in text
        c2 = Circuit.from_originir(text)
        assert c2.originir == text

    def test_qasm_export_rejects_dynamic_program(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        with pytest.raises(CircuitTranslationError):
            _ = c.qasm

    def test_official_originir_rejects_dynamic_program(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        with pytest.raises(CircuitTranslationError):
            _ = c.originir_official

    def test_qasm_export_rejects_declared_memory_even_without_control_flow(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        with pytest.raises(CircuitTranslationError):
            _ = c.qasm


# ─── Circuit.copy() preserves dynamic program ─────────────────────────


class TestCopyPreservesDynamicProgram:
    def test_copy_preserves_classical_memory_and_dynamic_program(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        c.endqif()

        c2 = c.copy()
        assert c2.classical_memory == c.classical_memory
        assert c2.classical_memory is not c.classical_memory
        assert c2.originir == c.originir

    def test_copy_is_structurally_independent(self):
        """Mutating a copy's dynamic-program branches must not affect the original."""
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        c.endqif()

        c2 = c.copy()
        from uniqc.circuit_builder.dynamic_program import GateNode, IfNode

        if_node_copy = next(n for n in c2.dynamic_program if isinstance(n, IfNode))
        if_node_copy.then_body.append(GateNode(("Z", 2, None, None, False, None)))

        if_node_orig = next(n for n in c.dynamic_program if isinstance(n, IfNode))
        assert len(if_node_orig.then_body) == 1  # unaffected by the copy's mutation

    def test_copy_preserves_qram_and_classical_together(self):
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.declare_memory("m", 0)
        c.h(0)
        c.x(3)
        c.qram_call("r", 0, 1, 2, control_qubits=3)
        c.cmeasure(3, "m")

        c2 = c.copy()
        assert c2.qram_declarations == c.qram_declarations
        assert c2.classical_memory == c.classical_memory
        assert c2.originir == c.originir


# ─── Dynamic program execution ─────────────────────────────────────────


class TestDynamicExecution:
    def test_deterministic_cmeasure_drives_qif(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.x(0)  # deterministic |1>
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        c.endqif()
        c.measure(1)

        result = simulate_dynamic(c, seed=123)
        assert result.memory["m"] == 1
        assert result.trace.measurements == [(0, 1)]
        idx = np.nonzero(np.abs(result.statevector) > 1e-9)[0]
        assert list(idx) == [3]  # q0=1, q1=1

    def test_qif_else_takes_else_branch(self):
        c = Circuit()
        c.declare_memory("m", 0)
        # q0 stays |0>, so cmeasure -> m=0 -> ELSE branch executes.
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        c.qelse()
        c.x(2)
        c.endqif()

        result = simulate_dynamic(c)
        assert result.memory["m"] == 0
        assert result.trace.if_false_count == 1
        assert result.trace.if_true_count == 0
        idx = np.nonzero(np.abs(result.statevector) > 1e-9)[0]
        assert list(idx) == [4]  # q2=1 only

    def test_qwhile_counts_iterations_deterministically(self):
        c = Circuit()
        c.declare_memory("i", 0)
        c.qwhile("i < 5", max_iterations=100)
        c.cassign("i", "i + 1")
        c.endqwhile()

        result = simulate_dynamic(c)
        assert result.memory["i"] == 5
        assert result.trace.while_iterations == 5

    def test_qwhile_watchdog_raises(self):
        c = Circuit()
        c.declare_memory("i", 0)
        c.qwhile("i < 5", max_iterations=2)
        c.cassign("i", "i + 1")
        c.endqwhile()

        with pytest.raises(LoopWatchdogError):
            simulate_dynamic(c)

    def test_nested_qif_inside_qwhile_execution(self):
        """A QIF nested inside a QWHILE only flips the target qubit on
        iterations where the classical condition holds."""
        c = Circuit()
        c.declare_memory("i", 0)
        c.declare_memory("flips", 0)
        c.qwhile("i < 4", max_iterations=20)
        c.qif("(i == 1) || (i == 3)")
        c.cassign("flips", "flips + 1")
        c.endqif()
        c.cassign("i", "i + 1")
        c.endqwhile()

        result = simulate_dynamic(c)
        assert result.memory["i"] == 4
        assert result.memory["flips"] == 2  # i==1 and i==3
        assert result.trace.if_true_count == 2
        assert result.trace.if_false_count == 2

    def test_reset_mid_circuit(self):
        c = Circuit()
        c.x(0)
        c.reset_qubit(0)
        c.h(0)
        c.measure(0)

        result = simulate_dynamic(c, seed=1)
        assert result.trace.resets == [0]
        idx = np.nonzero(np.abs(result.statevector) > 1e-9)[0]
        assert sorted(idx) == [0, 1]
        for i in idx:
            assert abs(abs(result.statevector[i]) ** 2 - 0.5) < 1e-10

    def test_reset_density_backend(self):
        c = Circuit()
        c.x(0)
        c.reset_qubit(0)
        c.h(0)

        result = simulate_dynamic(c, backend_type="density_matrix", seed=2)
        diag = np.real(np.diag(result.density_matrix))
        assert abs(diag[0] - 0.5) < 1e-10
        assert abs(diag[1] - 0.5) < 1e-10

    def test_controlled_qram_with_cmeasure_and_qif_density_backend(self):
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.declare_memory("m", 0)
        c.h(0)
        c.x(3)
        c.qram_call("r", 0, 1, 2, control_qubits=3)
        c.cmeasure(3, "m")
        c.qif("m == 1")
        c.z(1)
        c.endqif()

        result = simulate_dynamic(c, backend_type="density_matrix", seed=5, qram_data={"r": {1: 3}})
        assert result.memory["m"] == 1  # control qubit q3 deterministically |1>
        diag = np.real(np.diag(result.density_matrix))
        idx = np.nonzero(diag > 1e-9)[0]
        assert sorted(idx) == [8, 15]

    def test_restart_until_success(self):
        """Bounded restart loop: re-run from |0...0> until a measured outcome
        satisfies a success predicate, mirroring streaming-filter restarts."""
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")

        executor = DynamicProgramExecutor()
        result = executor.run_with_restarts(c, max_restarts=200, success=lambda mem: mem["m"] == 1, seed=7)
        assert result.status == "completed"
        assert result.memory["m"] == 1
        assert result.trace.restarts >= 1

    def test_restart_exhausted_status(self):
        """An impossible success predicate must exhaust every restart attempt
        and report status='restart_exhausted' rather than raising."""
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")

        executor = DynamicProgramExecutor()
        result = executor.run_with_restarts(c, max_restarts=5, success=lambda mem: mem["m"] == 2, seed=11)
        assert result.status == "restart_exhausted"
        assert result.trace.restarts == 5

    def test_seeded_execution_is_reproducible(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")

        r1 = simulate_dynamic(c, seed=999)
        r2 = simulate_dynamic(c, seed=999)
        assert r1.memory == r2.memory

    def test_ordinary_flat_circuit_still_executes_via_executor(self):
        """A circuit with no dynamic_program (dynamic_program is None) must
        still run correctly through the same executor, for compatibility."""
        c = Circuit()
        c.h(0)
        c.x(1)
        assert c.dynamic_program is None

        result = simulate_dynamic(c)
        idx = np.nonzero(np.abs(result.statevector) > 1e-9)[0]
        assert sorted(idx) == [2, 3]


# ─── Density-backend measurement correctness (get_prob bit-test fix) ──


class TestDensityMeasurementCorrectness:
    """Regression tests for the DensityOperatorSimulator::get_prob /
    get_prob_map bit-test bug: probability of qubit qn must depend only on
    bit qn of the basis index ((i >> qn) & 1), not on (i >> qn) as a whole
    (which conflated qn with every higher qubit). Also covers a related
    StatevectorSimulator::get_prob(measure_map) double-counting bug (see
    test_get_prob_map_joint_statevector_no_double_counting)."""

    def test_get_prob_q1_of_nontrivial_three_qubit_state(self):
        import uniqc_cpp

        sim = uniqc_cpp.DensityOperatorSimulator()
        sim.init_n_qubit(3)
        sim.hadamard(0)
        sim.hadamard(1)  # q1 in superposition; q0 also in superposition
        sim.x(2)  # q2 deterministically |1>

        p0_q1 = sim.get_prob(1, 0)
        p1_q1 = sim.get_prob(1, 1)
        assert abs(p0_q1 - 0.5) < 1e-9
        assert abs(p1_q1 - 0.5) < 1e-9
        # q2 is deterministically |1> regardless of q0/q1 superposition.
        assert abs(sim.get_prob(2, 1) - 1.0) < 1e-9
        assert abs(sim.get_prob(2, 0) - 0.0) < 1e-9

    def test_get_prob_map_q1_and_q2_joint(self):
        import uniqc_cpp

        sim = uniqc_cpp.DensityOperatorSimulator()
        sim.init_n_qubit(3)
        sim.hadamard(0)
        sim.hadamard(1)
        sim.x(2)

        assert abs(sim.get_prob({1: 1, 2: 1}) - 0.5) < 1e-9
        assert abs(sim.get_prob({1: 0, 2: 1}) - 0.5) < 1e-9
        assert abs(sim.get_prob({1: 1, 2: 0}) - 0.0) < 1e-9

    def test_get_prob_map_joint_statevector_no_double_counting(self):
        """Regression test for a StatevectorSimulator::get_prob(measure_map)
        bug: the joint-probability accumulation looped over every entry in
        measure_map and re-added abs_sqr(state[i]) once per entry whenever
        the mask matched, inflating an N-qubit joint probability by a factor
        of N instead of counting each matching basis state exactly once.
        Must match the (already-correct) DensityOperatorSimulator behavior."""
        import uniqc_cpp

        sim = uniqc_cpp.StatevectorSimulator()
        sim.init_n_qubit(3)
        sim.hadamard(0, [], False)
        sim.hadamard(1, [], False)
        sim.x(2, [], False)

        # Single-qubit map probability must match the two-arg get_prob.
        assert abs(sim.get_prob({1: 0}) - sim.get_prob(1, 0)) < 1e-9
        assert abs(sim.get_prob({1: 0}) - 0.5) < 1e-9

        # Joint probability over 2 qubits must not be inflated by a factor
        # of len(measure_map) — each matching basis state counts once.
        assert abs(sim.get_prob({1: 1, 2: 1}) - 0.5) < 1e-9
        assert abs(sim.get_prob({1: 0, 2: 1}) - 0.5) < 1e-9
        assert abs(sim.get_prob({1: 1, 2: 0}) - 0.0) < 1e-9

        # Joint probability over all 3 qubits sums to 1 across all outcomes
        # (would sum to 3x too much under the old bug).
        total = sum(
            sim.get_prob({0: a, 1: b, 2: c}) for a in (0, 1) for b in (0, 1) for c in (0, 1)
        )
        assert abs(total - 1.0) < 1e-9

    def test_measure_qubit_q1_collapses_only_q1_density(self):
        """measure_qubit(1) on a 3-qubit state must yield both outcomes over
        many seeded trials, and post-measurement q2 (deterministically |1>)
        and q0 (untouched superposition) must remain unaffected — i.e. the
        collapse must act on bit 1 specifically, not on (i >> 1) as a whole."""
        import uniqc_cpp

        outcomes = []
        for seed in range(30):
            uniqc_cpp.seed(seed)
            sim = uniqc_cpp.DensityOperatorSimulator()
            sim.init_n_qubit(3)
            sim.hadamard(0)
            sim.hadamard(1)
            sim.x(2)
            outcome = sim.measure_qubit(1)
            outcomes.append(outcome)
            # q2 must remain deterministically |1> after collapsing q1.
            assert abs(sim.get_prob(2, 1) - 1.0) < 1e-9
            # q0 must remain in superposition (unaffected by measuring q1).
            assert abs(sim.get_prob(0, 0) - 0.5) < 1e-6
            assert abs(sim.get_prob(0, 1) - 0.5) < 1e-6
            # q1 itself must now be deterministic, matching the outcome.
            assert abs(sim.get_prob(1, outcome) - 1.0) < 1e-9

        assert 0 in outcomes and 1 in outcomes

    def test_measure_qubit_clamps_p0_to_valid_range(self):
        """A state whose q0 probability is numerically exactly 0 or 1 must
        not raise from sqrt-of-negative or similar out-of-range issues after
        clamping (statevector and density backends)."""
        import uniqc_cpp

        uniqc_cpp.seed(1)
        sv = uniqc_cpp.StatevectorSimulator()
        sv.init_n_qubit(1)
        sv.x(0)  # deterministically |1>, p0 should clamp cleanly to 0
        assert sv.measure_qubit(0) == 1

        uniqc_cpp.seed(1)
        dm = uniqc_cpp.DensityOperatorSimulator()
        dm.init_n_qubit(1)
        dm.x(0)
        assert dm.measure_qubit(0) == 1


# ─── QWHILE max_iterations validation (builder / node / parser) ───────


class TestQWhileMaxIterationsValidation:
    def test_builder_rejects_zero(self):
        c = Circuit()
        c.declare_memory("i", 0)
        with pytest.raises(ValueError, match="positive integer"):
            c.qwhile("i < 3", max_iterations=0)

    def test_builder_rejects_negative(self):
        c = Circuit()
        c.declare_memory("i", 0)
        with pytest.raises(ValueError, match="positive integer"):
            c.qwhile("i < 3", max_iterations=-5)

    def test_while_node_rejects_zero(self):
        from uniqc.circuit_builder.dynamic_program import ConstExpr, WhileNode

        with pytest.raises(ValueError, match="positive integer"):
            WhileNode(ConstExpr(1), [], 0)

    def test_while_node_rejects_negative(self):
        from uniqc.circuit_builder.dynamic_program import ConstExpr, WhileNode

        with pytest.raises(ValueError, match="positive integer"):
            WhileNode(ConstExpr(1), [], -1)

    def test_parser_rejects_zero_max_iterations(self):
        text = "CDECL i, 0\nQINIT 1\nCREG 0\nQWHILE (i < 3), 0\nX q[0]\nENDQWHILE\n"
        with pytest.raises(ValueError, match="positive integer"):
            Circuit.from_originir(text)

    def test_parser_rejects_negative_max_iterations(self):
        text = "CDECL i, 0\nQINIT 1\nCREG 0\nQWHILE (i < 3), -2\nX q[0]\nENDQWHILE\n"
        with pytest.raises(ValueError, match="positive integer"):
            Circuit.from_originir(text)

    def test_positive_max_iterations_still_works(self):
        c = Circuit()
        c.declare_memory("i", 0)
        c.qwhile("i < 3", max_iterations=1)
        c.cassign("i", "i + 1")
        c.endqwhile()
        assert "QWHILE (i < 3), 1" in c.originir


# ─── Non-canonical terminal cbit mapping rejection ─────────────────────


class TestNonCanonicalCbitRejection:
    def test_gap_in_cbit_mapping_rejected(self):
        text = "CDECL m, 0\nQINIT 5\nCREG 5\nH q[0]\nCMEASURE q[0], m\nMEASURE q[2], c[4]\n"
        with pytest.raises(ValueError, match="canonical"):
            Circuit.from_originir(text)

    def test_duplicate_cbit_mapping_rejected(self):
        text = "CDECL m, 0\nQINIT 3\nCREG 2\nCMEASURE q[0], m\nMEASURE q[1], c[0]\nMEASURE q[2], c[0]\n"
        with pytest.raises(ValueError, match="canonical"):
            Circuit.from_originir(text)

    def test_canonical_contiguous_mapping_round_trips(self):
        text = "CDECL m, 0\nQINIT 3\nCREG 2\nCMEASURE q[0], m\nMEASURE q[1], c[0]\nMEASURE q[2], c[1]\n"
        c = Circuit.from_originir(text)
        assert c.originir == text

    def test_canonical_mapping_reordered_in_text_still_accepted(self):
        """c[1] appearing before c[0] textually is fine — canonicality is
        about the *set* of cbit indices used, not their line order."""
        text = "CDECL m, 0\nQINIT 3\nCREG 2\nCMEASURE q[0], m\nMEASURE q[2], c[1]\nMEASURE q[1], c[0]\n"
        c = Circuit.from_originir(text)
        assert c.cbit_num == 2


# ─── Unclosed QIF/QWHILE block validation ──────────────────────────────


class TestUnclosedBlockValidation:
    def test_unclosed_qif_rejected_on_serialization(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        # missing endqif()
        with pytest.raises(ValueError, match="unclosed"):
            _ = c.originir

    def test_unclosed_qwhile_rejected_on_execution(self):
        c = Circuit()
        c.declare_memory("i", 0)
        c.qwhile("i < 3")
        c.cassign("i", "i + 1")
        # missing endqwhile()
        with pytest.raises(ValueError, match="unclosed"):
            simulate_dynamic(c)

    def test_nested_unclosed_outer_while_rejected(self):
        """Inner QIF properly closed, but outer QWHILE left open."""
        c = Circuit()
        c.declare_memory("i", 0)
        c.qwhile("i < 3")
        c.qif("i == 0")
        c.x(0)
        c.endqif()
        # missing endqwhile()
        with pytest.raises(ValueError, match="unclosed"):
            _ = c.originir

    def test_properly_closed_blocks_serialize_and_execute(self):
        c = Circuit()
        c.declare_memory("m", 0)
        c.h(0)
        c.cmeasure(0, "m")
        c.qif("m == 1")
        c.x(1)
        c.endqif()
        assert c.originir is not None
        result = simulate_dynamic(c)
        assert result.status == "completed"
