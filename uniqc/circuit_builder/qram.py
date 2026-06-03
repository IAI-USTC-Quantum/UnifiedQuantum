"""Quantum RAM (QRAM) data structure.

Provides a simple binary-addressed classical memory used by quantum circuits.
A QRAM is declared with an address size and data size; at runtime it stores
integers (0 <= value < 2^data_size) indexed by addresses (0 <= addr < 2^addr_size).

Example usage in OriginIR-ext::

    QRAMDECL my_ram 3,6
    QINIT 9
    CREG 0
    my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]

The above declares ``my_ram`` as a QRAM with 3-bit address and 6-bit data
(9 qubits total).  Callers index it as
``my_ram q[0],q[1],q[2],q[3],q[4],q[5],q[6],q[7],q[8]`` where q[0..2] are
the address bits (q[0] = LSB) and q[3..8] are the data bits (q[3] = LSB).
"""

__all__ = ["QRAM"]

MAX_QUBITS = 30


class QRAM:
    """A simple binary-addressed quantum RAM.

    Args:
        name: Identifier for this QRAM instance.
        addr_size: Number of address qubits (determines number of entries).
        data_size: Number of data qubits (determines max storable value).
    """

    def __init__(self, name: str, addr_size: int, data_size: int):
        if addr_size <= 0 or data_size <= 0:
            raise ValueError(
                f"QRAM '{name}': addr_size and data_size must be positive integers, "
                f"got addr_size={addr_size}, data_size={data_size}."
            )
        if addr_size + data_size > MAX_QUBITS:
            raise ValueError(
                f"QRAM '{name}': total qubits ({addr_size}+{data_size}={addr_size + data_size}) "
                f"exceeds maximum ({MAX_QUBITS})."
            )

        self.name = name
        self.addr_size = addr_size
        self.data_size = data_size
        self._data = [0] * (1 << addr_size)

    @property
    def total_qubits(self) -> int:
        """Total number of qubits required: address + data."""
        return self.addr_size + self.data_size

    @property
    def num_entries(self) -> int:
        """Number of addressable entries: 2^addr_size."""
        return len(self._data)

    @property
    def max_value(self) -> int:
        """Maximum storable value: 2^data_size - 1."""
        return (1 << self.data_size) - 1

    def read(self, addr: int) -> int:
        """Read the value stored at *addr*.

        Args:
            addr: Address index (0 <= addr < 2^addr_size).

        Returns:
            The stored integer.

        Raises:
            IndexError: If *addr* is out of range.
        """
        if not (0 <= addr < len(self._data)):
            raise IndexError(
                f"QRAM '{self.name}': address {addr} out of range "
                f"[0, {len(self._data) - 1}]."
            )
        return self._data[addr]

    def write(self, addr: int, value: int) -> None:
        """Write *value* at address *addr*.

        Args:
            addr: Address index (0 <= addr < 2^addr_size).
            value: Integer to store (0 <= value < 2^data_size).

        Raises:
            IndexError: If *addr* is out of range.
            ValueError: If *value* exceeds the data capacity.
        """
        if not (0 <= addr < len(self._data)):
            raise IndexError(
                f"QRAM '{self.name}': address {addr} out of range "
                f"[0, {len(self._data) - 1}]."
            )
        if not (0 <= value <= self.max_value):
            raise ValueError(
                f"QRAM '{self.name}': value {value} exceeds data capacity "
                f"[0, {self.max_value}] (data_size={self.data_size})."
            )
        self._data[addr] = value

    def reset(self, value: int = 0) -> None:
        """Reset all entries to *value* (default 0).

        Args:
            value: Value to fill every address with.

        Raises:
            ValueError: If *value* exceeds the data capacity.
        """
        if not (0 <= value <= self.max_value):
            raise ValueError(
                f"QRAM '{self.name}': value {value} exceeds data capacity "
                f"[0, {self.max_value}] (data_size={self.data_size})."
            )
        self._data = [value] * len(self._data)

    def __repr__(self) -> str:
        return (
            f"QRAM(name={self.name!r}, addr_size={self.addr_size}, "
            f"data_size={self.data_size}, num_entries={self.num_entries})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, QRAM):
            return NotImplemented
        return (
            self.name == other.name
            and self.addr_size == other.addr_size
            and self.data_size == other.data_size
            and self._data == other._data
        )
