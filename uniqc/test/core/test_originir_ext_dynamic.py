"""End-to-end tests for the CREG-based dynamic OriginIR-ext feature: the
Circuit builder API (creg / measure_to / reset / classical instructions /
QIF-QELSE / QWHILE), OriginIR-ext round-trip, export rejection, the
``OriginIR_ext_Simulator`` (per-shot sampling, CREG endianness, watchdog,
blocked exact paths), and local-execution routing (Dummy backend + CLI).
"""

from __future__ import annotations

import pytest

from uniqc import Circuit, get_backend
from uniqc.circuit_builder.classical_program import imm
from uniqc.exceptions import CircuitTranslationError
from uniqc.simulator import LoopWatchdogError, OriginIR_ext_Simulator

# ─── Circuit builder API ──────────────────────────────────────────────


class TestCircuitDynamicAPI:
    def test_creg_size_floor_and_autogrow(self):
        c = Circuit(3)
        c.creg(2)
        assert c.cbit_num == 2
        c.measure_to(0, 4)  # auto-grow to include c[4]
        assert c.cbit_num == 5

    def test_creg_rejects_negative(self):
        c = Circuit(1)
        with pytest.raises(ValueError):
            c.creg(-1)

    def test_measure_to_switches_to_dynamic(self):
        c = Circuit(1)
        assert c.dynamic_program is None
        c.h(0)
        c.measure_to(0, 0)
        assert c.dynamic_program is not None

    def test_measure_to_single_qubit_only(self):
        c = Circuit(2)
        with pytest.raises(ValueError):
            c.measure_to([0, 1], 0)

    def test_classical_instruction_operand_forms(self):
        c = Circuit(1)
        c.creg(4)
        c.c_mov(0, imm(1))  # explicit immediate
        c.c_mov(1, "c[0]")  # string bit ref
        c.c_and(2, 0, 1)  # int cbit indices (c[0], c[1])
        c.c_not(3, "1")  # string immediate
        ir = c.originir
        assert "MOV c[0], 1" in ir
        assert "MOV c[1], c[0]" in ir
        assert "AND c[2], c[0], c[1]" in ir
        assert "NOT c[3], 1" in ir

    def test_bare_int_operand_is_cbit_index(self):
        # A bare int denotes a CREG bit index, not an immediate.
        c = Circuit(1)
        c.creg(2)
        c.c_mov(0, 1)  # c[0] = c[1]
        assert "MOV c[0], c[1]" in c.originir

    def test_qelse_without_qif_raises(self):
        c = Circuit(1)
        with pytest.raises(ValueError, match="matching open qif"):
            c.qelse()

    def test_endqif_without_qif_raises(self):
        c = Circuit(1)
        with pytest.raises(ValueError, match="matching open qif"):
            c.endqif()

    def test_endqwhile_without_qwhile_raises(self):
        c = Circuit(1)
        with pytest.raises(ValueError, match="matching open qwhile"):
            c.endqwhile()

    def test_unclosed_block_raises_on_serialize(self):
        c = Circuit(1)
        c.creg(1)
        c.qif("c[0]")
        c.x(0)
        with pytest.raises(ValueError, match="unclosed"):
            _ = c.originir

    def test_measure_terminal_forbidden_inside_block(self):
        c = Circuit(1)
        c.creg(1)
        c.qif("c[0]")
        with pytest.raises(ValueError, match="QIF/QWHILE"):
            c.measure(0)
        c.endqif()

    def test_qwhile_bad_max_iterations(self):
        c = Circuit(1)
        with pytest.raises(ValueError):
            c.qwhile("c[0]", max_iterations=0)

    def test_copy_is_independent(self):
        c = Circuit(2)
        c.creg(2)
        c.h(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        d = c.copy()
        d.qif("c[0]")
        d.x(0)
        d.endqif()
        assert c.originir != d.originir


# ─── OriginIR-ext round-trip + export rejection ───────────────────────


def _build_reference_circuit() -> Circuit:
    c = Circuit(3)
    c.creg(3)
    c.h(0)
    c.measure_to(0, 0)
    c.qif("c[0] and ~c[1]")
    c.x(1)
    c.measure_to(1, 1)
    c.qelse()
    c.h(1)
    c.endqif()
    c.qwhile("c[2] | c[1]")
    c.measure_to(2, 2)
    c.endqwhile()
    c.c_xor(2, 0, 1)
    return c


class TestOriginIRRoundTrip:
    def test_round_trip_idempotent(self):
        c = _build_reference_circuit()
        ir1 = c.originir
        ir2 = Circuit.from_originir(ir1).originir
        assert ir1 == ir2

    def test_serialized_keywords_present(self):
        ir = _build_reference_circuit().originir
        for token in ("QIF", "QELSE", "ENDQIF", "QWHILE", "ENDQWHILE", "MEASURE q[0], c[0]", "XOR c[2], c[0], c[1]"):
            assert token in ir, token

    def test_symbol_and_keyword_conditions_equivalent(self):
        a = Circuit(2)
        a.creg(2)
        a.measure_to(0, 0)
        a.qif("c[0] and ~c[1]")
        a.x(1)
        a.endqif()
        b = Circuit(2)
        b.creg(2)
        b.measure_to(0, 0)
        b.qif("c[0] & ~c[1]")
        b.x(1)
        b.endqif()
        assert a.originir == b.originir

    def test_qasm_export_rejected(self):
        c = _build_reference_circuit()
        with pytest.raises(CircuitTranslationError):
            _ = c.qasm

    def test_official_originir_export_rejected(self):
        c = _build_reference_circuit()
        with pytest.raises(CircuitTranslationError):
            _ = c.originir_official


# ─── Simulator: per-shot sampling & semantics ─────────────────────────


class TestDynamicSimulator:
    def test_deterministic_feedback(self):
        c = Circuit(2)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        counts = OriginIR_ext_Simulator("statevector", seed=7).simulate_shots(c, 300)
        assert counts == {3: 300}  # c0=1, c1=1 -> value 0b11

    def test_feedback_correlation_statistics(self):
        c = Circuit(2)
        c.creg(2)
        c.h(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        counts = OriginIR_ext_Simulator("statevector", seed=123).simulate_shots(c, 4000)
        assert set(counts) <= {0, 3}  # c1 always mirrors c0
        assert 1500 < counts.get(0, 0) < 2500
        assert 1500 < counts.get(3, 0) < 2500

    def test_creg_endianness_c0_is_lsb(self):
        c = Circuit(2)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)
        c.measure_to(1, 1)
        v = OriginIR_ext_Simulator("statevector", seed=1).simulate_single_shot(c)
        assert v == 1  # c0=1 (LSB), c1=0

    def test_qelse_branch_taken(self):
        c = Circuit(2)
        c.creg(2)
        # c0 stays 0 -> QELSE runs: X q1 -> c1 = 1 -> value 0b10 = 2
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.qelse()
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        assert OriginIR_ext_Simulator("statevector", seed=2).simulate_single_shot(c) == 2

    def test_classical_instructions(self):
        c = Circuit(1)
        c.creg(3)
        c.c_mov(0, imm(1))  # c0 = 1
        c.c_xor(1, 0, imm(1))  # c1 = c[0] ^ 1 = 0
        c.c_not(2, 1)  # c2 = ~c[1] = 1   (bare int 1 = CREG bit c[1])
        # value = c0*1 + c1*2 + c2*4 = 1 + 0 + 4 = 5
        assert OriginIR_ext_Simulator("statevector").simulate_single_shot(c) == 5

    def test_qwhile_terminates(self):
        c = Circuit(1)
        c.creg(1)
        c.qwhile("~c[0]")
        c.h(0)
        c.measure_to(0, 0)
        c.endqwhile()
        assert OriginIR_ext_Simulator("statevector", seed=5).simulate_single_shot(c) == 1

    def test_qwhile_watchdog_fires(self):
        c = Circuit(1)
        c.creg(1)
        c.qwhile("~c[0]", max_iterations=25)  # c0 never set -> infinite
        c.x(0)
        c.endqwhile()
        with pytest.raises(LoopWatchdogError):
            OriginIR_ext_Simulator("statevector").simulate_single_shot(c)

    def test_global_watchdog_override(self):
        c = Circuit(1)
        c.creg(1)
        c.qwhile("~c[0]")  # default huge cap
        c.x(0)
        c.endqwhile()
        sim = OriginIR_ext_Simulator("statevector", max_while_iterations=10)
        with pytest.raises(LoopWatchdogError):
            sim.simulate_single_shot(c)

    def test_pmeasure_blocked(self):
        c = _build_reference_circuit()
        with pytest.raises(NotImplementedError):
            OriginIR_ext_Simulator().simulate_pmeasure(c)

    def test_stateprob_blocked(self):
        c = _build_reference_circuit()
        with pytest.raises(NotImplementedError):
            OriginIR_ext_Simulator().simulate_stateprob(c)

    def test_density_backend(self):
        c = Circuit(2)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        counts = OriginIR_ext_Simulator("density_matrix", seed=7).simulate_shots(c, 200)
        assert counts == {3: 200}

    def test_accepts_originir_text(self):
        c = Circuit(2)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        ir = c.originir
        counts = OriginIR_ext_Simulator("statevector", seed=9).simulate_shots(ir, 100)
        assert counts == {3: 100}

    def test_reset_clears_qubit(self):
        c = Circuit(1)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)  # c0 = 1
        c.reset(0)
        c.measure_to(0, 1)  # c1 = 0 after reset
        v = OriginIR_ext_Simulator("statevector", seed=3).simulate_single_shot(c)
        assert v == 1  # c0=1, c1=0


# ─── Local-execution routing (Dummy backend + CLI) ────────────────────


class TestDynamicRouting:
    def test_dummy_backend_runs_dynamic(self):
        c = Circuit(2)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        be = get_backend("dummy")
        result = be.query(be.submit(c.originir, shots=250))["result"]
        assert result == {"11": 250}

    def test_cli_run_simulation_dynamic(self):
        from uniqc.cli.simulate import _run_simulation

        c = Circuit(2)
        c.creg(2)
        c.x(0)
        c.measure_to(0, 0)
        c.qif("c[0]")
        c.x(1)
        c.endqif()
        c.measure_to(1, 1)
        probs = _run_simulation(c.originir, "statevector", 200)
        assert probs == {"11": 1.0}

    def test_dummy_dry_run_dynamic(self):
        from uniqc.backend_adapter.task.adapters.dummy_adapter import DummyAdapter

        c = _build_reference_circuit()
        assert DummyAdapter().dry_run(c.originir, shots=10).success
        # malformed (missing ENDQIF) fails dry-run
        assert not DummyAdapter().dry_run("QINIT 1\nCREG 1\nQIF c[0]\nX q[0]\n", shots=10).success
