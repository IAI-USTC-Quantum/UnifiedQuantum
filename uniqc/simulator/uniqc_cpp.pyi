"""
[Module uniqc_cpp]
"""

from __future__ import annotations
import collections.abc
import typing

__all__: list[str] = ["DensityOperatorSimulator", "StatevectorSimulator", "rand", "seed"]

class DensityOperatorSimulator:
    max_qubit_num: typing.ClassVar[int] = 10
    def __init__(self) -> None: ...
    def amplitude_damping(
        self, qn: typing.SupportsInt | typing.SupportsIndex, gamma: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    def bitflip(
        self, qn: typing.SupportsInt | typing.SupportsIndex, p: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    def cnot(
        self,
        controller: typing.SupportsInt | typing.SupportsIndex,
        target: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def cswap(
        self,
        controller: typing.SupportsInt | typing.SupportsIndex,
        target1: typing.SupportsInt | typing.SupportsIndex,
        target2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def cz(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def depolarizing(
        self, qn: typing.SupportsInt | typing.SupportsIndex, p: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    @typing.overload
    def get_prob(
        self, arg0: typing.SupportsInt | typing.SupportsIndex, arg1: typing.SupportsInt | typing.SupportsIndex
    ) -> float: ...
    @typing.overload
    def get_prob(
        self,
        arg0: collections.abc.Mapping[
            typing.SupportsInt | typing.SupportsIndex, typing.SupportsInt | typing.SupportsIndex
        ],
    ) -> float: ...
    def hadamard(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def init_n_qubit(self, arg0: typing.SupportsInt | typing.SupportsIndex) -> None: ...
    def iswap(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def kraus1q(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        kraus_ops: collections.abc.Sequence[
            typing.Annotated[
                collections.abc.Sequence[typing.SupportsComplex | typing.SupportsFloat | typing.SupportsIndex],
                "FixedSize(4)",
            ]
        ],
    ) -> None: ...
    def measure_qubit(self, qn: typing.SupportsInt | typing.SupportsIndex) -> int: ...
    def pauli_error_1q(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        px: typing.SupportsFloat | typing.SupportsIndex,
        py: typing.SupportsFloat | typing.SupportsIndex,
        pz: typing.SupportsFloat | typing.SupportsIndex,
    ) -> None: ...
    def pauli_error_2q(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        p: collections.abc.Sequence[typing.SupportsFloat | typing.SupportsIndex],
    ) -> None: ...
    def phase2q(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta1: typing.SupportsFloat | typing.SupportsIndex,
        theta2: typing.SupportsFloat | typing.SupportsIndex,
        thetazz: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def phaseflip(
        self, qn: typing.SupportsInt | typing.SupportsIndex, p: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    @typing.overload
    def pmeasure(self, arg0: typing.SupportsInt | typing.SupportsIndex) -> list[float]: ...
    @typing.overload
    def pmeasure(self, arg0: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex]) -> list[float]: ...
    def qram(
        self,
        addr_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex],
        data_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex],
        data_array: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex],
        control_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
    ) -> None: ...
    def reset_qubit(self, qn: typing.SupportsInt | typing.SupportsIndex) -> None: ...
    def rphi(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rphi180(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rphi90(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rx(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def ry(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rz(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def s(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def stateprob(self) -> list[float]: ...
    def swap(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def sx(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def t(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def toffoli(
        self,
        controller1: typing.SupportsInt | typing.SupportsIndex,
        controller2: typing.SupportsInt | typing.SupportsIndex,
        target: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def twoqubit_depolarizing(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        p: typing.SupportsFloat | typing.SupportsIndex,
    ) -> None: ...
    def u1(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def u2(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        lamda: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def u22(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        unitary: typing.Annotated[
            collections.abc.Sequence[typing.SupportsComplex | typing.SupportsFloat | typing.SupportsIndex],
            "FixedSize(4)",
        ],
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def u3(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        lamda: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def uu15(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        parameters: collections.abc.Sequence[typing.SupportsFloat | typing.SupportsIndex],
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def x(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def xx(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def xy(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def y(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def yy(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def z(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def zz(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    @property
    def state(self) -> list[complex]: ...
    @property
    def total_qubit(self) -> int: ...

class StatevectorSimulator:
    max_qubit_num: typing.ClassVar[int] = 30
    def __init__(self) -> None: ...
    def amplitude_damping(
        self, qn: typing.SupportsInt | typing.SupportsIndex, gamma: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    def bitflip(
        self, qn: typing.SupportsInt | typing.SupportsIndex, p: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    def cnot(
        self,
        controller: typing.SupportsInt | typing.SupportsIndex,
        target: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def cswap(
        self,
        controller: typing.SupportsInt | typing.SupportsIndex,
        target1: typing.SupportsInt | typing.SupportsIndex,
        target2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def cz(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def depolarizing(
        self, qn: typing.SupportsInt | typing.SupportsIndex, p: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    @typing.overload
    def get_prob(
        self, qn: typing.SupportsInt | typing.SupportsIndex, qstate: typing.SupportsInt | typing.SupportsIndex
    ) -> float: ...
    @typing.overload
    def get_prob(
        self,
        measure_map: collections.abc.Mapping[
            typing.SupportsInt | typing.SupportsIndex, typing.SupportsInt | typing.SupportsIndex
        ],
    ) -> float: ...
    def hadamard(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def init_n_qubit(self, arg0: typing.SupportsInt | typing.SupportsIndex) -> None: ...
    def iswap(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def kraus1q(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        kraus_ops: collections.abc.Sequence[
            typing.Annotated[
                collections.abc.Sequence[typing.SupportsComplex | typing.SupportsFloat | typing.SupportsIndex],
                "FixedSize(4)",
            ]
        ],
    ) -> None: ...
    def measure_qubit(self, qn: typing.SupportsInt | typing.SupportsIndex) -> int: ...
    @typing.overload
    def measure_single_shot(self, qubit: typing.SupportsInt | typing.SupportsIndex) -> int: ...
    @typing.overload
    def measure_single_shot(
        self, qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex]
    ) -> int: ...
    def pauli_error_1q(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        px: typing.SupportsFloat | typing.SupportsIndex,
        py: typing.SupportsFloat | typing.SupportsIndex,
        pz: typing.SupportsFloat | typing.SupportsIndex,
    ) -> None: ...
    def pauli_error_2q(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        p: collections.abc.Sequence[typing.SupportsFloat | typing.SupportsIndex],
    ) -> None: ...
    def phase2q(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta1: typing.SupportsFloat | typing.SupportsIndex,
        theta2: typing.SupportsFloat | typing.SupportsIndex,
        thetazz: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def phaseflip(
        self, qn: typing.SupportsInt | typing.SupportsIndex, p: typing.SupportsFloat | typing.SupportsIndex
    ) -> None: ...
    @typing.overload
    def pmeasure(self, qn: typing.SupportsInt | typing.SupportsIndex) -> list[float]: ...
    @typing.overload
    def pmeasure(
        self, measure_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex]
    ) -> list[float]: ...
    def qram(
        self,
        addr_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex],
        data_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex],
        data_array: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex],
        control_qubits: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
    ) -> None: ...
    def reset_qubit(self, qn: typing.SupportsInt | typing.SupportsIndex) -> None: ...
    def rphi(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rphi180(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rphi90(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rx(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def ry(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def rz(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def s(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def swap(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def sx(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def t(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def toffoli(
        self,
        controller1: typing.SupportsInt | typing.SupportsIndex,
        controller2: typing.SupportsInt | typing.SupportsIndex,
        target: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def twoqubit_depolarizing(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        p: typing.SupportsFloat | typing.SupportsIndex,
    ) -> None: ...
    def u1(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def u2(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        lamda: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def u22(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        unitary: typing.Annotated[
            collections.abc.Sequence[typing.SupportsComplex | typing.SupportsFloat | typing.SupportsIndex],
            "FixedSize(4)",
        ],
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def u3(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        phi: typing.SupportsFloat | typing.SupportsIndex,
        lamda: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def uu15(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        parameters: collections.abc.Sequence[typing.SupportsFloat | typing.SupportsIndex],
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def x(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def xx(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def xy(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def y(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def yy(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def z(
        self,
        qn: typing.SupportsInt | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    def zz(
        self,
        qn1: typing.SupportsInt | typing.SupportsIndex,
        qn2: typing.SupportsInt | typing.SupportsIndex,
        theta: typing.SupportsFloat | typing.SupportsIndex,
        global_controller: collections.abc.Sequence[typing.SupportsInt | typing.SupportsIndex] = [],
        dagger: bool = False,
    ) -> None: ...
    @property
    def state(self) -> list[complex]: ...
    @property
    def total_qubit(self) -> int: ...

def rand() -> float: ...
def seed(arg0: typing.SupportsInt | typing.SupportsIndex) -> None: ...
