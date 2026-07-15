"""Tests for QRAM (Quantum RAM) feature."""

from __future__ import annotations

import numpy as np
import pytest

from uniqc.circuit_builder import QRAM, Circuit
from uniqc.circuit_builder.qcircuit import Circuit
from uniqc.compile.originir.originir_base_parser import OriginIR_BaseParser
from uniqc.compile.originir.originir_line_parser import OriginIR_LineParser
from uniqc.simulator import Simulator

# ─── QRAM class unit tests ────────────────────────────────────────────


class TestQRAMClass:
    """Unit tests for the QRAM data structure."""

    def test_basic_construction(self):
        ram = QRAM("test", 3, 6)
        assert ram.name == "test"
        assert ram.addr_size == 3
        assert ram.data_size == 6
        assert ram.total_qubits == 9
        assert ram.num_entries == 8
        assert ram.max_value == 63

    def test_default_all_zeros(self):
        ram = QRAM("r", 2, 4)
        for i in range(4):
            assert ram.read(i) == 0

    def test_write_and_read(self):
        ram = QRAM("r", 2, 4)
        ram.write(0, 15)
        ram.write(3, 7)
        assert ram.read(0) == 15
        assert ram.read(3) == 7
        assert ram.read(1) == 0

    def test_write_max_value(self):
        ram = QRAM("r", 1, 8)
        ram.write(0, 255)
        assert ram.read(0) == 255

    def test_write_exceeds_capacity(self):
        ram = QRAM("r", 1, 4)  # max_value = 15
        with pytest.raises(ValueError, match="exceeds data capacity"):
            ram.write(0, 16)

    def test_negative_value(self):
        ram = QRAM("r", 1, 4)
        with pytest.raises(ValueError, match="exceeds data capacity"):
            ram.write(0, -1)

    def test_address_out_of_range(self):
        ram = QRAM("r", 2, 4)  # 4 entries: 0-3
        with pytest.raises(IndexError, match="out of range"):
            ram.read(4)
        with pytest.raises(IndexError, match="out of range"):
            ram.write(4, 0)

    def test_reset(self):
        ram = QRAM("r", 2, 4)
        ram.write(0, 15)
        ram.write(1, 10)
        ram.reset()
        assert all(ram.read(i) == 0 for i in range(4))

    def test_reset_to_value(self):
        ram = QRAM("r", 2, 4)
        ram.reset(5)
        assert all(ram.read(i) == 5 for i in range(4))

    def test_invalid_sizes(self):
        with pytest.raises(ValueError, match="positive"):
            QRAM("r", 0, 4)
        with pytest.raises(ValueError, match="positive"):
            QRAM("r", 3, 0)

    def test_repr(self):
        ram = QRAM("my_ram", 3, 6)
        r = repr(ram)
        assert "my_ram" in r
        assert "addr_size=3" in r
        assert "data_size=6" in r

    def test_equality(self):
        r1 = QRAM("r", 2, 4)
        r2 = QRAM("r", 2, 4)
        assert r1 == r2
        r1.write(0, 5)
        assert r1 != r2


# ─── QRAMDECL parsing tests ──────────────────────────────────────────


class TestQRAMDECLParsing:
    """Test QRAMDECL line parsing."""

    def setup_method(self):
        OriginIR_LineParser._declared_qram_names = set()

    def test_parse_qramdecl_line(self):
        op, q, c, param, dagger, ctrl = OriginIR_LineParser.parse_line("QRAMDECL my_ram 3,6")
        assert op == "QRAMDECL"
        assert q == ("my_ram", 3, 6)
        assert dagger is False
        assert ctrl == []

    def test_parse_qramdecl_with_spaces(self):
        op, q, c, param, dagger, ctrl = OriginIR_LineParser.parse_line("QRAMDECL ram1 2 , 4")
        assert op == "QRAMDECL"
        assert q == ("ram1", 2, 4)

    def test_qramdecl_then_call(self):
        # Register name first (as the base parser would do)
        OriginIR_LineParser._declared_qram_names.add("my_ram")
        op, q, c, param, dagger, ctrl = OriginIR_LineParser.parse_line(
            "my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]"
        )
        assert op == "my_ram"
        assert q == [0, 1, 2, 3, 4, 5, 6, 7, 8]
        assert dagger is False
        assert ctrl == []

    def test_unregistered_qram_name_raises(self):
        with pytest.raises(NotImplementedError, match="invalid line"):
            OriginIR_LineParser.parse_line("unknown_ram q[0],q[1]")


# ─── Full parser integration tests ────────────────────────────────────


class TestQRAMParserIntegration:
    """Test full OriginIR parsing with QRAM."""

    def setup_method(self):
        OriginIR_LineParser._declared_qram_names = set()

    def test_parse_originir_with_qramdecl(self):
        originir = """\
QRAMDECL my_ram 3,6
QINIT 9
CREG 0
H q[0]
my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]
"""
        parser = OriginIR_BaseParser()
        parser.parse(originir)
        assert "my_ram" in parser.qram_declarations
        assert parser.qram_declarations["my_ram"] == (3, 6)
        assert parser.n_qubit == 9
        assert len(parser.program_body) == 2  # H + my_ram call

    def test_parse_multiple_qram_declarations(self):
        originir = """\
QRAMDECL ram_a 2,4
QRAMDECL ram_b 3,8
QINIT 11
CREG 0
ram_a q[0],q[1],q[2],q[3],q[4],q[5]
ram_b q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8],q[9],q[10]
"""
        parser = OriginIR_BaseParser()
        parser.parse(originir)
        assert len(parser.qram_declarations) == 2
        assert parser.qram_declarations["ram_a"] == (2, 4)
        assert parser.qram_declarations["ram_b"] == (3, 8)

    def test_roundtrip_originir(self):
        originir = """\
QRAMDECL my_ram 3,6
QINIT 9
CREG 0
H q[0]
my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]
"""
        parser = OriginIR_BaseParser()
        parser.parse(originir)
        output = parser.to_extended_originir()
        assert "QRAMDECL my_ram 3,6" in output
        assert "my_ram q[0], q[1], q[2], q[3], q[4], q[5], q[6], q[7], q[8]" in output


# ─── Circuit class QRAM tests ─────────────────────────────────────────


class TestCircuitQRAM:
    """Test Circuit class QRAM support."""

    def test_qram_declare_and_call(self):
        c = Circuit()
        c.qram_declare("my_ram", 3, 6)
        c.h(0)
        c.qram_call("my_ram", 0, 1, 2, 3, 4, 5, 6, 7, 8)
        assert "my_ram" in c.qram_declarations
        assert len(c.opcode_list) == 2

    def test_qram_declare_duplicate_raises(self):
        c = Circuit()
        c.qram_declare("r", 2, 4)
        with pytest.raises(ValueError, match="already declared"):
            c.qram_declare("r", 2, 4)

    def test_qram_call_without_declare_raises(self):
        c = Circuit()
        with pytest.raises(ValueError, match="not been declared"):
            c.qram_call("r", 0, 1, 2, 3, 4, 5)

    def test_qram_call_wrong_qubit_count_raises(self):
        c = Circuit()
        c.qram_declare("r", 2, 4)  # expects 6 qubits
        with pytest.raises(ValueError, match="expects 6 qubits"):
            c.qram_call("r", 0, 1, 2, 3, 4)

    def test_qram_in_originir_output(self):
        c = Circuit()
        c.qram_declare("my_ram", 3, 6)
        c.h(0)
        c.qram_call("my_ram", 0, 1, 2, 3, 4, 5, 6, 7, 8)
        c.measure(0)
        originir = c.originir
        assert "QRAMDECL my_ram 3,6" in originir
        assert "my_ram q[0], q[1]" in originir

    def test_qram_from_originir(self):
        originir = """\
QRAMDECL my_ram 3,6
QINIT 9
CREG 0
H q[0]
my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]
"""
        c = Circuit.from_originir(originir)
        assert "my_ram" in c.qram_declarations
        assert c.qram_declarations["my_ram"] == (3, 6)

    def test_qram_roundtrip(self):
        originir = """\
QRAMDECL my_ram 3,6
QINIT 9
CREG 0
H q[0]
my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]
"""
        c = Circuit.from_originir(originir)
        output = c.originir
        assert "QRAMDECL my_ram 3,6" in output
        c2 = Circuit.from_originir(output)
        assert c2.qram_declarations == c.qram_declarations


# ─── Simulator tests ──────────────────────────────────────────────────


class TestQRAMSimulator:
    """Test QRAM in the simulator pipeline."""

    def test_qram_zero_data_is_identity(self):
        """With all-zero QRAM data, XOR is identity — state unchanged."""
        originir = """\
QRAMDECL my_ram 3,6
QINIT 9
CREG 0
H q[0]
my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]
"""
        sim = Simulator()
        sv = sim.simulate_statevector(originir)
        import numpy as np

        sv = np.array(sv)
        assert abs(abs(sv[0]) ** 2 - 0.5) < 1e-10
        assert abs(abs(sv[1]) ** 2 - 0.5) < 1e-10

    def test_qram_xor_data(self):
        """QRAM XORs data register with stored value at the address."""
        import numpy as np

        # 1-bit addr, 3-bit data → 4 qubits total
        c = Circuit()
        c.qram_declare("r", 1, 3)
        # Set addr=|1⟩, data=|000⟩
        c.x(0)  # q[0]=1 (addr bit)
        # data qubits q[1],q[2],q[3] all |0⟩
        c.qram_call("r", 0, 1, 2, 3)

        sim = Simulator()
        sim.simulate_preprocess(c)
        # Store value 5 (= 101 binary) at address 1
        sim.qram_objects["r"].write(1, 5)
        sv = np.array(sim.simulate_statevector(c))

        # addr=1, data was 0 → data becomes 0 XOR 5 = 5 (binary 101)
        # q[0]=1, q[1]=1 (bit0 of 5), q[2]=0 (bit1), q[3]=1 (bit2)
        # state index = 1 + 2 + 8 = 11 (q[0]=1, q[1]=1, q[2]=0, q[3]=1)
        assert abs(abs(sv[11]) ** 2 - 1.0) < 1e-10

    def test_qram_involution(self):
        """Applying QRAM twice restores original state (self-inverse)."""
        import numpy as np

        c = Circuit()
        c.qram_declare("r", 2, 4)
        c.h(0)  # superposition on addr bit 0
        c.qram_call("r", 0, 1, 2, 3, 4, 5)
        c.qram_call("r", 0, 1, 2, 3, 4, 5)  # second application

        sim = Simulator()
        sim.simulate_preprocess(c)
        sim.qram_objects["r"].write(0, 7)
        sim.qram_objects["r"].write(1, 3)
        sv = np.array(sim.simulate_statevector(c))

        # After two QRAM calls, should be back to H|0⟩ on q[0]
        # State: 1/√2 (|000000⟩ + |000001⟩)
        assert abs(abs(sv[0]) ** 2 - 0.5) < 1e-10
        assert abs(abs(sv[1]) ** 2 - 0.5) < 1e-10

    def test_qram_with_prepopulated_data(self):
        """QRAM with data written before simulation."""
        import numpy as np

        originir = """\
QRAMDECL r 2,3
QINIT 5
CREG 0
X q[0]
r q[0],q[1],q[2],q[3],q[4]
"""
        sim = Simulator()
        sim.simulate_preprocess(originir)
        # addr bits: q[0],q[1]; data bits: q[2],q[3],q[4]
        # Set addr=01 → store 6 at addr 1
        sim.qram_objects["r"].write(1, 6)
        sv = np.array(sim.simulate_statevector(originir))

        # Initial: X on q[0] → |00001⟩ (index 1, addr=01=1)
        # QRAM: data(0 XOR 6=6=110) → q[2]=0, q[3]=1, q[4]=1
        # Final state: q[0]=1, q[1]=0, q[2]=0, q[3]=1, q[4]=1
        # index = 1 + 8 + 16 = 25
        assert abs(abs(sv[25]) ** 2 - 1.0) < 1e-10

    def test_qram_simulation_from_circuit(self):
        """Full pipeline: Circuit → Simulator → QRAM data → simulate."""
        import numpy as np

        c = Circuit()
        c.qram_declare("my_ram", 1, 2)
        c.x(0)  # addr = 1
        c.qram_call("my_ram", 0, 1, 2)
        c.measure(0)

        sim = Simulator()
        sim.simulate_preprocess(c)
        sim.qram_objects["my_ram"].write(1, 3)  # store 3 at addr 1
        sv = np.array(sim.simulate_statevector(c))

        # addr=1, data was 0 → 0 XOR 3 = 3 (binary 11)
        # q[0]=1, q[1]=1, q[2]=1 → index = 7
        assert abs(abs(sv[7]) ** 2 - 1.0) < 1e-10


# ─── QRAM runtime object tests ───────────────────────────────────────


class TestQRAMRuntime:
    """Test QRAM used as a runtime data container alongside simulation."""

    def test_qram_basic_runtime_usage(self):
        """Demonstrate QRAM as a runtime data container."""
        ram = QRAM("my_ram", 3, 6)
        # Pre-populate some data
        ram.write(0, 42)
        ram.write(5, 63)
        assert ram.read(0) == 42
        assert ram.read(5) == 63
        assert ram.read(1) == 0  # uninitialized


# ─── Controlled QRAM tests ────────────────────────────────────────────


class TestControlledQRAM:
    """Test controlled QRAM: disjoint controls, self-inverse, superposition."""

    def test_control_disjoint_validation_raises(self):
        """Control qubits overlapping addr/data must be rejected."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        with pytest.raises(ValueError, match="overlap"):
            c.qram_call("r", 0, 1, 2, control_qubits=1)

    def test_qram_call_accepts_control_qubits(self):
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.qram_call("r", 0, 1, 2, control_qubits=3)
        op = c.opcode_list[-1]
        assert op[0] == "r"
        assert op[5] == [3]

    def test_control_merges_with_control_context(self):
        """qram_call() participates in the with-control() context, like ordinary gates."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        with c.control(5):
            c.qram_call("r", 0, 1, 2)
        op = c.opcode_list[-1]
        assert op[5] == [5]

    def test_control_identity_when_control_zero(self):
        """Controlled QRAM is the identity when the control qubit is |0>."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.x(0)  # addr = 1 (nonzero address)
        # control qubit 3 left at |0>
        c.qram_call("r", 0, 1, 2, control_qubits=3)

        sim = Simulator(least_qubit_remapping=False)
        sim.simulate_preprocess(c)
        sim.qram_objects["r"].write(1, 3)  # nonzero data value at addr=1
        sv = np.array(sim.simulate_statevector(c))
        idx = np.nonzero(np.abs(sv) > 1e-9)[0]
        # addr bit (q0=1) unaffected; data untouched since control=0.
        assert list(idx) == [1]
        assert abs(abs(sv[1]) ** 2 - 1.0) < 1e-10

    def test_control_xor_load_when_control_one_nonzero_target(self):
        """Controlled QRAM XOR-loads onto an arbitrary nonzero data target when control=1."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.x(0)  # addr = 1
        c.x(2)  # data starts as a nonzero target: binary 10 (=2)
        c.x(3)  # control = 1
        c.qram_call("r", 0, 1, 2, control_qubits=3)

        sim = Simulator(least_qubit_remapping=False)
        sim.simulate_preprocess(c)
        sim.qram_objects["r"].write(1, 3)  # 3 = 0b11
        sv = np.array(sim.simulate_statevector(c))
        idx = np.nonzero(np.abs(sv) > 1e-9)[0]
        # data XOR: 2 (0b10) ^ 3 (0b11) = 1 (0b01) -> q1=1,q2=0.
        # q0=1(addr), q1=1, q2=0, q3=1(control) -> index = 1+2+8 = 11
        assert list(idx) == [11]

    def test_control_superposition_addr_and_control(self):
        """Controlled QRAM on a superposed address, with the control also set,
        applies the XOR-load coherently across every basis branch."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.h(0)  # superposed address
        c.x(3)  # control = 1 (applies to every branch)
        c.qram_call("r", 0, 1, 2, control_qubits=3)

        sim = Simulator(least_qubit_remapping=False)
        sim.simulate_preprocess(c)
        sim.qram_objects["r"].write(0, 0)
        sim.qram_objects["r"].write(1, 3)
        sv = np.array(sim.simulate_statevector(c))
        idx = np.nonzero(np.abs(sv) > 1e-9)[0]
        # addr=0 branch: data unaffected (0 XOR 0) -> q0=0,q3=1 -> index 8
        # addr=1 branch: data 0 XOR 3=3(0b11) -> q1=1,q2=1 -> q0=1,q1=1,q2=1,q3=1 -> index 15
        assert sorted(idx) == [8, 15]
        for i in idx:
            assert abs(abs(sv[i]) ** 2 - 0.5) < 1e-10

    def test_control_self_inverse_double_apply_restores_state(self):
        """Applying controlled QRAM twice (same controls) is the identity,
        even with a superposed address and a nonzero, non-basis data target."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.h(0)  # superposed address
        c.x(2)  # nonzero starting data target
        c.x(3)  # control = 1
        c.qram_call("r", 0, 1, 2, control_qubits=3)
        c.qram_call("r", 0, 1, 2, control_qubits=3)

        sim = Simulator(least_qubit_remapping=False)
        sim.simulate_preprocess(c)
        sim.qram_objects["r"].write(0, 1)
        sim.qram_objects["r"].write(1, 3)
        sv = np.array(sim.simulate_statevector(c))
        # After two applications, state must equal H(q0) X(q2) X(q3) applied alone
        # (i.e. q2=1 (=0b10 -> index contribution 4), q3=1 (=8), q0 in superposition).
        idx = np.nonzero(np.abs(sv) > 1e-9)[0]
        assert sorted(idx) == [12, 13]
        for i in idx:
            assert abs(abs(sv[i]) ** 2 - 0.5) < 1e-10

    def test_control_originir_roundtrip(self):
        """Controlled QRAM must round-trip through OriginIR-ext text exactly."""
        c = Circuit()
        c.qram_declare("r", 1, 2)
        c.h(0)
        c.x(3)
        c.qram_call("r", 0, 1, 2, control_qubits=3)
        c.measure(1)
        text = c.originir
        assert "controlled_by (q[3])" in text

        c2 = Circuit.from_originir(text)
        assert c2.originir == text
        op = c2.opcode_list[-1]
        assert op[0] == "r"
        assert op[5] == [3]

    def test_copy_preserves_qram_declarations(self):
        """Circuit.copy() must preserve qram_declarations (previous gap)."""
        c = Circuit()
        c.qram_declare("r", 2, 3)
        c.h(0)
        c.qram_call("r", 0, 1, 2, 3, 4)

        c2 = c.copy()
        assert c2.qram_declarations == c.qram_declarations
        assert c2.qram_declarations is not c.qram_declarations
        # Mutating the copy's declarations must not affect the original.
        c2.qram_declarations["extra"] = (1, 1)
        assert "extra" not in c.qram_declarations


# ─── QRAM qubit-list validation: duplicates and overlaps ──────────────


class TestQRAMQubitListValidation:
    """Reject duplicate addr/data qubits, addr/data overlap, and duplicate
    control qubits — both at the Python Circuit layer and directly at the
    C++ simulator layer (uniqc_cpp)."""

    # --- Python (Circuit.qram_call) ---

    def test_duplicate_addr_qubit_rejected(self):
        c = Circuit()
        c.qram_declare("r", 2, 2)
        with pytest.raises(ValueError, match="duplicated in the address"):
            c.qram_call("r", 0, 0, 2, 3)

    def test_duplicate_data_qubit_rejected(self):
        c = Circuit()
        c.qram_declare("r", 2, 2)
        with pytest.raises(ValueError, match="duplicated in the data"):
            c.qram_call("r", 0, 1, 2, 2)

    def test_addr_data_overlap_rejected(self):
        c = Circuit()
        c.qram_declare("r", 2, 2)
        with pytest.raises(ValueError, match="overlaps with an address qubit"):
            c.qram_call("r", 0, 1, 1, 3)

    def test_duplicate_control_qubit_rejected(self):
        c = Circuit()
        c.qram_declare("r", 2, 2)
        with pytest.raises(ValueError, match="duplicated in the control"):
            c.qram_call("r", 0, 1, 2, 3, control_qubits=[4, 4])

    def test_control_overlap_still_rejected(self):
        c = Circuit()
        c.qram_declare("r", 2, 2)
        with pytest.raises(ValueError, match="overlap"):
            c.qram_call("r", 0, 1, 2, 3, control_qubits=1)

    def test_valid_addr_data_control_all_disjoint_accepted(self):
        c = Circuit()
        c.qram_declare("r", 2, 2)
        c.qram_call("r", 0, 1, 2, 3, control_qubits=[4, 5])
        assert c.opcode_list[-1] == ("r", [0, 1, 2, 3], None, None, False, [4, 5])

    # --- Direct C++ (uniqc_cpp) ---

    def test_cpp_duplicate_addr_qubit_rejected(self):
        import uniqc_cpp

        sim = uniqc_cpp.StatevectorSimulator()
        sim.init_n_qubit(6)
        with pytest.raises(ValueError, match="duplicated in the address"):
            sim.qram([0, 0, 1], [2, 3], [0] * 8)

    def test_cpp_duplicate_data_qubit_rejected(self):
        import uniqc_cpp

        sim = uniqc_cpp.StatevectorSimulator()
        sim.init_n_qubit(6)
        with pytest.raises(ValueError, match="duplicated in the data"):
            sim.qram([0, 1], [2, 2, 3], [0] * 8)

    def test_cpp_addr_data_overlap_rejected(self):
        import uniqc_cpp

        sim = uniqc_cpp.StatevectorSimulator()
        sim.init_n_qubit(6)
        with pytest.raises(ValueError, match="overlaps with an address qubit"):
            sim.qram([0, 1], [1, 3], [0] * 4)

    def test_cpp_duplicate_control_qubit_rejected(self):
        import uniqc_cpp

        sim = uniqc_cpp.StatevectorSimulator()
        sim.init_n_qubit(6)
        with pytest.raises(ValueError, match="duplicated in the control"):
            sim.qram([0, 1], [2, 3], [0] * 4, [4, 4])

    def test_cpp_control_overlap_rejected(self):
        import uniqc_cpp

        sim = uniqc_cpp.StatevectorSimulator()
        sim.init_n_qubit(6)
        with pytest.raises(ValueError, match="overlaps with an address/data qubit"):
            sim.qram([0, 1], [2, 3], [0] * 4, [1])

    def test_cpp_valid_call_succeeds_on_both_backends(self):
        import uniqc_cpp

        sv = uniqc_cpp.StatevectorSimulator()
        sv.init_n_qubit(6)
        sv.qram([0, 1], [2, 3], [0] * 4, [4, 5])

        dm = uniqc_cpp.DensityOperatorSimulator()
        dm.init_n_qubit(6)
        dm.qram([0, 1], [2, 3], [0] * 4, [4, 5])
