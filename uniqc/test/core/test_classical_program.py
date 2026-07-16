"""Unit tests for the CREG-based classical / control-flow program tree
(``uniqc.circuit_builder.classical_program``): condition AST + parser,
classical-instruction operands, program-tree nodes, serialization,
round-trip parsing, and structural cloning.
"""

from __future__ import annotations

import pytest

from uniqc.circuit_builder.classical_program import (
    ClassicalOp,
    GateOp,
    IfBlock,
    MeasureOp,
    Operand,
    ResetOp,
    WhileBlock,
    clone_program,
    contains_dynamic_keywords,
    parse_cond,
    parse_operand,
    parse_program_body,
    serialize_program,
)

# ─── Condition parser ─────────────────────────────────────────────────


class TestCondParser:
    def test_bare_bit_is_truthy(self):
        assert parse_cond("c[0]").evaluate([1]) == 1
        assert parse_cond("c[0]").evaluate([0]) == 0

    def test_const_bits(self):
        assert parse_cond("1").evaluate([]) == 1
        assert parse_cond("0").evaluate([]) == 0

    def test_keyword_and_symbol_equivalent(self):
        creg = [1, 0, 1]
        for text in ("c[0] and c[2]", "c[0] & c[2]"):
            assert parse_cond(text).evaluate(creg) == 1
        for text in ("c[0] and c[1]", "c[0] & c[1]"):
            assert parse_cond(text).evaluate(creg) == 0

    def test_or_xor_not(self):
        creg = [1, 0]
        assert parse_cond("c[0] or c[1]").evaluate(creg) == 1
        assert parse_cond("c[0] | c[1]").evaluate(creg) == 1
        assert parse_cond("c[0] xor c[0]").evaluate(creg) == 0
        assert parse_cond("c[0] ^ c[1]").evaluate(creg) == 1
        assert parse_cond("not c[1]").evaluate(creg) == 1
        assert parse_cond("~c[0]").evaluate(creg) == 0

    def test_precedence_not_gt_and_gt_xor_gt_or(self):
        # not binds tighter than and: (not c0) and c1
        assert parse_cond("not c[0] and c[1]").evaluate([1, 1]) == 0
        assert parse_cond("not c[0] and c[1]").evaluate([0, 1]) == 1
        # and binds tighter than or: c0 or (c1 and c2)
        assert parse_cond("c[0] or c[1] and c[2]").evaluate([0, 1, 0]) == 0
        assert parse_cond("c[0] or c[1] and c[2]").evaluate([1, 0, 0]) == 1
        # and binds tighter than xor: (c0 and c1) xor c2
        assert parse_cond("c[0] and c[1] xor c[2]").evaluate([1, 1, 0]) == 1

    def test_parentheses_override(self):
        assert parse_cond("(c[0] or c[1]) and c[2]").evaluate([1, 0, 0]) == 0
        assert parse_cond("(c[0] or c[1]) and c[2]").evaluate([1, 0, 1]) == 1

    def test_idempotent_on_cond(self):
        c = parse_cond("c[0] & c[1]")
        assert parse_cond(c) is c

    def test_round_trip_symbol_canonical(self):
        c = parse_cond("c[0] and not c[1] or c[2] xor 1")
        s = c.to_str()
        assert parse_cond(s).to_str() == s
        # canonical form uses symbols
        assert "&" in s and "~" in s and "|" in s and "^" in s

    def test_bit_out_of_range_raises(self):
        with pytest.raises(IndexError):
            parse_cond("c[5]").evaluate([0, 1])

    @pytest.mark.parametrize("bad", ["", "c[0] and", "c[0] c[1]", "(c[0]", "c[0] & )", "2"])
    def test_malformed_raises(self, bad):
        with pytest.raises(ValueError):
            parse_cond(bad)


# ─── Operands ─────────────────────────────────────────────────────────


class TestOperands:
    def test_parse_bit_and_immediate(self):
        assert parse_operand("c[3]") == Operand(is_imm=False, value=3)
        assert parse_operand("1") == Operand(is_imm=True, value=1)
        assert parse_operand(" 0 ") == Operand(is_imm=True, value=0)

    def test_read(self):
        assert Operand(is_imm=True, value=1).read([]) == 1
        assert Operand(is_imm=False, value=2).read([0, 0, 1]) == 1

    def test_bad_immediate_rejected(self):
        with pytest.raises(ValueError):
            Operand(is_imm=True, value=2)

    @pytest.mark.parametrize("bad", ["c[]", "2", "q[0]", "x"])
    def test_parse_operand_bad(self, bad):
        with pytest.raises(ValueError):
            parse_operand(bad)


# ─── Classical instruction semantics ──────────────────────────────────


class TestClassicalOp:
    def test_binary_ops(self):
        assert ClassicalOp("AND", 0, (parse_operand("c[1]"), parse_operand("c[2]"))).execute([0, 1, 1]) == 1
        assert ClassicalOp("OR", 0, (parse_operand("c[1]"), parse_operand("0"))).execute([0, 1, 0]) == 1
        assert ClassicalOp("XOR", 0, (parse_operand("c[1]"), parse_operand("1"))).execute([0, 1]) == 0

    def test_unary_ops(self):
        assert ClassicalOp("NOT", 0, (parse_operand("c[1]"),)).execute([0, 0]) == 1
        assert ClassicalOp("MOV", 0, (parse_operand("1"),)).execute([0]) == 1

    def test_arity_validation(self):
        with pytest.raises(ValueError):
            ClassicalOp("AND", 0, (parse_operand("c[1]"),))
        with pytest.raises(ValueError):
            ClassicalOp("NOT", 0, (parse_operand("c[1]"), parse_operand("c[2]")))

    def test_unknown_instruction(self):
        with pytest.raises(ValueError):
            ClassicalOp("NAND", 0, (parse_operand("c[0]"), parse_operand("c[1]")))


# ─── Serialization + round-trip parsing ───────────────────────────────


class TestSerializeParse:
    def test_serialize_leaf_ops(self):
        body = [
            MeasureOp(0, 0),
            ResetOp(1),
            ClassicalOp("AND", 2, (parse_operand("c[0]"), parse_operand("c[1]"))),
            ClassicalOp("NOT", 0, (parse_operand("c[0]"),)),
            ClassicalOp("MOV", 1, (parse_operand("1"),)),
        ]
        lines = serialize_program(body)
        assert lines == [
            "MEASURE q[0], c[0]",
            "RESET q[1]",
            "AND c[2], c[0], c[1]",
            "NOT c[0], c[0]",
            "MOV c[1], 1",
        ]

    def test_round_trip_control_flow(self):
        text = """
        H q[0]
        MEASURE q[0], c[0]
        QIF c[0] and ~c[1]
        X q[1]
        MEASURE q[1], c[1]
        QELSE
        H q[1]
        ENDQIF
        QWHILE c[2] | c[1]
        MEASURE q[2], c[2]
        ENDQWHILE
        XOR c[2], c[0], c[1]
        """.strip().splitlines()
        body, idx = parse_program_body([ln.strip() for ln in text])
        assert idx == len(text)
        # Structure checks.
        kinds = [type(n).__name__ for n in body]
        assert kinds == ["GateOp", "MeasureOp", "IfBlock", "WhileBlock", "ClassicalOp"]
        if_node = body[2]
        assert isinstance(if_node, IfBlock)
        assert if_node.else_body is not None
        assert [type(n).__name__ for n in if_node.then_body] == ["GateOp", "MeasureOp"]
        # Serialize→parse idempotence.
        lines2 = serialize_program(body)
        body2, _ = parse_program_body(lines2)
        assert serialize_program(body2) == lines2

    def test_qif_without_qelse(self):
        body, _ = parse_program_body(["QIF c[0]", "X q[0]", "ENDQIF"])
        assert isinstance(body[0], IfBlock)
        assert body[0].else_body is None

    def test_missing_endqif_raises(self):
        with pytest.raises(ValueError, match="ENDQIF"):
            parse_program_body(["QIF c[0]", "X q[0]"])

    def test_missing_endqwhile_raises(self):
        with pytest.raises(ValueError, match="ENDQWHILE"):
            parse_program_body(["QWHILE c[0]", "X q[0]"])

    def test_block_form_control_rejected(self):
        with pytest.raises(ValueError, match="Block-form"):
            parse_program_body(["CONTROL q[0]", "X q[1]", "ENDCONTROL"])


# ─── Clone ────────────────────────────────────────────────────────────


class TestClone:
    def test_clone_is_deep_and_independent(self):
        body = [
            IfBlock(parse_cond("c[0]"), [GateOp(("X", 1, None, None, False, []))], [ResetOp(2)]),
            WhileBlock(parse_cond("c[1]"), [MeasureOp(0, 1)]),
        ]
        new_top, list_map, node_map = clone_program(body)
        assert new_top is not body
        assert new_top[0] is not body[0]
        # Mutating the clone must not touch the original.
        new_top[0].then_body.append(ResetOp(9))
        assert len(body[0].then_body) == 1
        # Maps expose the nested-body correspondence.
        assert list_map[id(body[0].then_body)] is new_top[0].then_body
        assert node_map[id(body[0])] is new_top[0]


# ─── Dynamic-keyword detection ────────────────────────────────────────


class TestContainsDynamicKeywords:
    def test_flat_terminal_measure_not_dynamic(self):
        assert not contains_dynamic_keywords("QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]\nMEASURE q[1], c[1]")

    def test_control_flow_is_dynamic(self):
        assert contains_dynamic_keywords("QINIT 1\nCREG 1\nQIF c[0]\nX q[0]\nENDQIF")

    def test_classical_instruction_is_dynamic(self):
        assert contains_dynamic_keywords("QINIT 1\nCREG 2\nXOR c[0], c[1], 1")

    def test_reset_is_dynamic(self):
        assert contains_dynamic_keywords("QINIT 1\nCREG 1\nRESET q[0]")

    def test_midcircuit_measure_is_dynamic(self):
        assert contains_dynamic_keywords("QINIT 2\nCREG 2\nH q[0]\nMEASURE q[0], c[0]\nX q[1]\nMEASURE q[1], c[1]")
