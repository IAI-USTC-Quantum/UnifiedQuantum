from .classical_program import (
    BinCond,
    BitRef,
    ClassicalOp,
    Cond,
    ConstBit,
    GateOp,
    IfBlock,
    MeasureOp,
    NotCond,
    Operand,
    ResetOp,
    WhileBlock,
    parse_cond,
    parse_operand,
)
from .matrix import NotMatrixableError, get_matrix
from .named_circuit import NamedCircuit, circuit_def
from .normalize import (
    AnyQuantumCircuit,
    NormalizedCircuit,
    normalize_circuit_input,
    normalize_to_circuit,
    resolve_output_format,
)
from .opcode import (
    CbitType,
    OpcodeType,
    ParameterType,
    QubitType,
    make_header_originir,
    make_header_qasm,
    make_measure_originir,
    make_measure_qasm,
    opcode_to_line_originir,
    opcode_to_line_originir_official,
    opcode_to_line_qasm,
)
from .originir_spec import (
    OFFICIAL_ORIGINIR_GATES,
    angular_gates,
    available_originir_error_channels,
    available_originir_error_channels_without_kraus,
    available_originir_gates,
    available_originir_official_gates,
    generate_sub_error_channel_originir,
    generate_sub_gateset_originir,
)
from .originir_ext_spec import (
    EXTENDED_GATES_ONLY,
    available_originir_ext_gates,
)
from .parameter import Parameter, Parameters
from .qasm_spec import available_qasm_gates, generate_sub_gateset_qasm
from .qcircuit import Circuit
from .qram import QRAM
from .qubit import QReg, QRegSlice, Qubit
from .random_originir import (
    build_full_measurements as _build_full_measurements,
)
from .random_originir import (
    build_originir_error_channel,
    build_originir_gate,
    random_originir,
)
from .random_qasm import (
    build_full_measurements,
    build_measurements,
    build_qasm_from_opcodes,
    build_qasm_gate,
    random_qasm,
)
from .translate_qasm2_oir import (
    OriginIR_QASM2_dict,
    decompose_mcu_qasm_text,
    direct_mapping_qasm2_to_oir,
    get_opcode_from_QASM2,
    get_QASM2_from_opcode,
)
