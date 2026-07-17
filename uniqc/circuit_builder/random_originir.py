"""Random OriginIR circuit generator.

This module provides functions for generating random quantum circuits in OriginIR
format. It supports random gate selection, error channel insertion, and full
measurement generation for testing and simulation purposes.

Key exports:
    build_originir_gate: Build a single OriginIR gate string.
    build_originir_error_channel: Build an error channel instruction.
    build_full_measurements: Generate measurement instructions for all qubits.
    random_originir: Generate a complete random OriginIR program.
"""

import random
import re

from .opcode import opcode_to_line_originir
from .originir_spec import angular_gates, available_originir_error_channels, available_originir_gates

__all__ = [
    "build_originir_gate",
    "build_originir_error_channel",
    "build_full_measurements",
    "random_originir",
]


def _build_phys_to_ref(named_qregs):
    """Map each physical qubit index to a ``regname[local]`` reference string."""
    phys_to_ref: dict[int, str] = {}
    offset = 0
    for name, size in named_qregs:
        for local in range(size):
            phys_to_ref[offset + local] = f"{name}[{local}]"
        offset += size
    return phys_to_ref, offset


def _rewrite_qrefs(line: str, phys_to_ref: dict[int, str]) -> str:
    """Rewrite physical ``q[i]`` references in *line* to named-register refs."""
    return re.sub(
        r"q *\[ *(\d+) *\]",
        lambda m: phys_to_ref.get(int(m.group(1)), m.group(0)),
        line,
    )


def build_originir_gate(gate, qubits, params, dagger_flag=False, control_qubit_set=None):
    """
    Build a line of OriginIR code for a given gate, qubits, and parameters.

    Args:
        gate (str): The name of the gate.
        qubits (list): A list of qubits the gate acts on.
        params (list): A list of parameters for the gate.

    Returns:
        str: A line of OriginIR code
    """

    if not qubits:
        raise ValueError("No qubits specified for gate")

    if gate not in available_originir_gates:
        raise ValueError(f"Gate {gate} not available in OriginIR")

    if gate != "BARRIER" and len(qubits) != available_originir_gates[gate]["qubit"]:
        raise ValueError(f"Gate {gate} requires {available_originir_gates[gate]['qubit']} qubits")

    if len(params) != available_originir_gates[gate]["param"]:
        raise ValueError(f"Gate {gate} requires {available_originir_gates[gate]['param']} parameters")

    # qubit_str = ",".join([f"q[{qubit}]" for qubit in qubits])

    # dagger_str = " dagger" if dagger_flag else ""

    # if params:

    #     param_str = [f"{param}" for param in params]
    #     param_str = ",".join(param_str)

    #     return f"{gate} {qubit_str}, ({param_str})"

    # else:
    #     return f"{gate} {qubit_str}"

    opcode = (gate, qubits, None, params, dagger_flag, control_qubit_set)
    # print(opcode)
    return opcode_to_line_originir(opcode)


def build_originir_error_channel(channel, qubits, params):
    """
    Build a line of OriginIR code for a given error channel, qubits, and parameters.

    Args:
        channel (str): The name of the error channel.
        qubits (list): A list of qubits the error channel acts on.

    Returns:
        str: A line of OriginIR code
    """

    if not qubits:
        raise ValueError("No qubits specified for error channel")

    if channel not in available_originir_error_channels:
        raise ValueError(f"Error channel {channel} not available in OriginIR")

    if len(qubits) != available_originir_error_channels[channel]["qubit"]:
        raise ValueError(
            f"Error channel {channel} requires {available_originir_error_channels[channel]['qubit']} qubits"
        )

    qubit_str = ",".join([f"q[{qubit}]" for qubit in qubits])

    param_str = [f"{param}" for param in params]
    param_str = ",".join(param_str)

    return f"{channel} {qubit_str}, ({param_str})"


def build_full_measurements(n_qubits):
    """
    Build a line of OriginIR code for a full measurement on a set of qubits.

    Args:
        n_qubits (list): Number of qubits to measure.

    Returns:
        str: A line of OriginIR code
    """

    measure_instructions = []
    for qubit in range(n_qubits):
        measure_instructions.append(f"MEASURE q[{qubit}], c[{qubit}]")

    return measure_instructions


def random_originir(
    n_qubits,
    n_gates,
    instruction_set=available_originir_gates,
    channel_set=None,
    allow_control=False,
    allow_dagger=False,
    named_qregs=None,
):
    """
    Generate a random OriginIR program with a given number of qubits and gates.

    Args:
        n_qubits (int): The number of qubits in the program.
        n_gates (int): The number of gates in the program.
        instruction_set (dict): A dictionary of available gates and their properties.
        channel_set (dict | None): Optional error channels to include.
        allow_control (bool): Whether to emit random ``controlled_by`` clauses.
        allow_dagger (bool): Whether to emit random inline ``dagger`` suffixes.
        named_qregs (list[tuple[str, int]] | None): Optional named-register
            layout as ``(name, size)`` pairs. When provided, the program is
            emitted with named ``QINIT name[size]`` declarations and
            register-qualified qubit references (``name[local]``) instead of the
            default bare-integer ``QINIT n`` header with physical ``q[i]``
            operands. The register sizes must sum to *n_qubits*. This exercises
            the named-register grammar and round-trips to the same circuit as
            the bare-integer form.

    Returns:
        str: A string of OriginIR code.
    """

    program = [f"QINIT {n_qubits}", f"CREG {n_qubits}"]

    instructions = list(instruction_set.keys())
    if channel_set is not None:
        instructions.extend(channel_set.keys())

    for i in range(n_gates):
        gate_name = random.choice(list(instructions))

        if gate_name in instruction_set:
            nqubit = instruction_set[gate_name]["qubit"]
            nparam = instruction_set[gate_name]["param"]
            if gate_name == "BARRIER":
                qubits_to_act = random.sample(range(n_qubits), random.randint(1, n_qubits))
            else:
                qubits_to_act = random.sample(range(n_qubits), nqubit)
            params = []
            if gate_name in angular_gates:
                params = [random.uniform(0, 2 * 3.14159) for _ in range(nparam)]
            elif nparam > 0:
                raise NotImplementedError(f"Gate {gate_name} not implemented")

            if allow_control:
                remaining_qubits = set(range(n_qubits)) - set(qubits_to_act)
                # control_qubits = random.sample(remaining_qubits, random.randint(0, len(remaining_qubits)))
                control_qubits = random.sample(sorted(remaining_qubits), random.randint(0, 1))
            else:
                control_qubits = None

            if allow_dagger:
                dagger_flag = random.choice([True, False])
            else:
                dagger_flag = False

            program.append(build_originir_gate(gate_name, qubits_to_act, params, dagger_flag, control_qubits))

        elif gate_name in channel_set:
            nqubit = channel_set[gate_name]["qubit"]
            nparam = channel_set[gate_name]["param"]
            qubits_to_act = random.sample(range(n_qubits), nqubit)
            params = [random.uniform(0, 1 / 15) for _ in range(nparam)]
            program.append(build_originir_error_channel(gate_name, qubits_to_act, params))

        else:
            raise ValueError(f"Instruction {gate_name} not available in OriginIR")

    program.extend(build_full_measurements(n_qubits))

    if named_qregs is not None:
        phys_to_ref, total = _build_phys_to_ref(named_qregs)
        if total != n_qubits:
            raise ValueError(f"named_qregs sizes sum to {total}, expected {n_qubits}.")
        # Replace the bare-integer QINIT header with named declarations and
        # rewrite every physical qubit reference to its named-register form.
        header = [f"QINIT {name}[{size}]" for name, size in named_qregs]
        header.append(program[1])  # CREG line unchanged
        body = [_rewrite_qrefs(line, phys_to_ref) for line in program[2:]]
        program = header + body

    originir = "\n".join(program)

    # print(originir)
    return originir
