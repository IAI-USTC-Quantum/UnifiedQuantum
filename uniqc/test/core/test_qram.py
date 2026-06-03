"""Tests for QRAM (Quantum RAM) feature."""

from __future__ import annotations

import pytest

from uniqc.circuit_builder import Circuit, QRAM
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
