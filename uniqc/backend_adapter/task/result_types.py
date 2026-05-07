"""Unified result types for all quantum backends.

This module defines a standardized result format that all platform adapters
must convert their outputs to. This ensures consistent handling of results
regardless of which quantum cloud platform was used.

The UnifiedResult dataclass provides:
- Measurement counts and probabilities in a consistent format
- Platform identification and task metadata
- Optional advanced results (expectation values, statevector)
- Raw platform result for debugging

Usage::

    # Create from counts
    result = UnifiedResult.from_counts(
        counts={"00": 512, "11": 488},
        platform="quafu",
        task_id="abc123"
    )

    # Create from probabilities
    result = UnifiedResult.from_probabilities(
        probabilities={"00": 0.512, "11": 0.488},
        shots=1000,
        platform="originq",
        task_id="xyz789"
    )
"""

from __future__ import annotations

__all__ = ["UnifiedResult", "DryRunResult"]

from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class UnifiedResult:
    """Unified quantum execution result format.

    All platform adapters must normalize their output to this format,
    ensuring consistent result handling across different quantum backends.

    Attributes:
        counts: Measurement counts as dict mapping bitstrings to counts.
            Example: {"00": 512, "11": 488}
        probabilities: Measurement probabilities as dict mapping bitstrings to probs.
            Example: {"00": 0.512, "11": 0.488}
        shots: Total number of shots executed.
        platform: Platform identifier ('originq', 'quafu', 'ibm', 'dummy').
        task_id: Unique task identifier from the platform.
        backend_name: Name of the quantum backend/hardware used (optional).
        execution_time: Execution time in seconds (optional).
        raw_result: Original platform result object for debugging (optional).
        error_message: Error message if execution failed (optional).

    Example:
        >>> result = UnifiedResult.from_counts(
        ...     counts={"00": 512, "11": 488},
        ...     platform="quafu",
        ...     task_id="task-123"
        ... )
        >>> print(result.probabilities)
        {'00': 0.512, '11': 0.488}
    """

    counts: dict[str, int]
    probabilities: dict[str, float]
    shots: int
    platform: str
    task_id: str
    backend_name: str | None = None
    execution_time: float | None = None
    raw_result: Any = field(default=None, repr=False)
    error_message: str | None = None

    @classmethod
    def from_counts(
        cls,
        counts: dict[str, int],
        platform: str,
        task_id: str,
        **kwargs: Any,
    ) -> UnifiedResult:
        """Create UnifiedResult from measurement counts.

        Probabilities are automatically computed from counts.

        Args:
            counts: Dict mapping bitstrings to measurement counts.
            platform: Platform identifier.
            task_id: Task identifier.
            **kwargs: Additional attributes (backend_name, execution_time, etc.).

        Returns:
            UnifiedResult instance with computed probabilities.

        Example:
            >>> result = UnifiedResult.from_counts(
            ...     {"00": 512, "11": 488}, "quafu", "task-1"
            ... )
        """
        total = sum(counts.values())
        probabilities = {} if total == 0 else {k: v / total for k, v in counts.items()}
        return cls(
            counts=counts,
            probabilities=probabilities,
            shots=total,
            platform=platform,
            task_id=task_id,
            **kwargs,
        )

    @classmethod
    def from_probabilities(
        cls,
        probabilities: dict[str, float],
        shots: int,
        platform: str,
        task_id: str,
        **kwargs: Any,
    ) -> UnifiedResult:
        """Create UnifiedResult from probability distribution.

        Counts are computed by multiplying probabilities by shots count.

        Args:
            probabilities: Dict mapping bitstrings to probabilities.
            shots: Number of shots used.
            platform: Platform identifier.
            task_id: Task identifier.
            **kwargs: Additional attributes.

        Returns:
            UnifiedResult instance with computed counts.

        Example:
            >>> result = UnifiedResult.from_probabilities(
            ...     {"00": 0.5, "11": 0.5}, 1000, "originq", "task-2"
            ... )
        """
        raw_counts = {k: v * shots for k, v in probabilities.items()}
        counts = {k: round(v) for k, v in raw_counts.items()}
        # Compensate rounding error so total exactly equals shots
        diff = shots - sum(counts.values())
        if diff != 0 and counts:
            key = sorted(counts)[0]
            counts[key] += diff
        return cls(
            counts=counts,
            probabilities=probabilities,
            shots=shots,
            platform=platform,
            task_id=task_id,
            **kwargs,
        )

    def to_dict(self) -> dict[str, int]:
        """Return flat counts dict for unified output.

        All platform adapters normalize their results to this format, ensuring
        consistent return types regardless of which quantum cloud backend was used.

        Returns:
            Flat dict mapping bitstrings to measurement counts.
            Example: {"00": 512, "1111": 488}
        """
        return self.counts

    def raw(self) -> Any:
        """Return the original platform-specific raw result.

        This is the unprocessed object/dict returned by the backend adapter
        before normalization. Use it for debugging, accessing platform-specific
        fields, or when you need the exact wire-format response.

        Returns:
            The raw_result attribute (may be ``None`` if not preserved).
        """
        return self.raw_result

    # ------------------------------------------------------------------
    # Dict-like behavior over ``counts``
    #
    # ``UnifiedResult`` quacks like a ``dict[str, int]`` of measurement
    # counts so existing code that did ``result["00"]``, ``len(result)``,
    # iteration, or ``result == {"00": 512}`` continues to work.
    # ------------------------------------------------------------------
    def __getitem__(self, key: str) -> int:
        return self.counts[key]

    def __iter__(self):
        return iter(self.counts)

    def __len__(self) -> int:
        return len(self.counts)

    def __contains__(self, key: object) -> bool:
        return key in self.counts

    def keys(self):
        return self.counts.keys()

    def values(self):
        return self.counts.values()

    def items(self):
        return self.counts.items()

    def get(self, key: str, default: Any = None) -> Any:
        return self.counts.get(key, default)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnifiedResult):
            return (
                self.counts == other.counts
                and self.shots == other.shots
                and self.platform == other.platform
                and self.task_id == other.task_id
            )
        if isinstance(other, dict):
            return self.counts == other
        return NotImplemented

    def __hash__(self) -> int:
        return id(self)

    def get_expectation(self, observable: str = "Z") -> float:
        """Compute expectation value for a simple observable.

        Currently only supports single-qubit Z expectation value
        computed from the first qubit's measurement results.

        Args:
            observable: Observable type (currently only 'Z' supported).

        Returns:
            Expectation value in range [-1, 1].

        Note:
            This is a simplified implementation. For complex observables,
            use uniqc.analyzer module.
        """
        if observable != "Z":
            raise NotImplementedError("Only Z observable is currently supported")

        if not self.probabilities:
            return 0.0

        # Compute <Z> for first qubit
        expectation = 0.0
        for bitstring, prob in self.probabilities.items():
            # First bit determines Z expectation for qubit 0
            first_bit = bitstring[-1] if bitstring else "0"
            sign = 1 if first_bit == "0" else -1
            expectation += sign * prob
        return expectation


@dataclass(frozen=True, slots=True)
class DryRunResult:
    """Result of a dry-run circuit validation.

    A dry-run validates circuit translatability and backend compatibility
    WITHOUT making any cloud API calls.

    Attributes:
        success: True if the circuit passed all validation checks.
        details: Human-readable description of what was checked and the outcome.
        warnings: Non-fatal warnings (e.g., no chip_id provided, partial validation).
        error: Error message if success is False.
        error_kind: Coarse classification of ``error`` so callers can branch on
            *why* the dry-run failed without parsing the message. One of:

            - ``"unknown_backend"``  — backend identifier not recognised
            - ``"sdk_missing"``      — required platform SDK / extra not installed
            - ``"credential_missing"`` — auth token / config missing
            - ``"circuit_invalid"``  — translation or basis-set check failed
            - ``"adapter_init"``     — adapter constructor itself raised
            - ``"unknown"``          — anything not yet classified

            ``None`` when ``success`` is True.
        backend_name: The backend/chip ID used for this dry-run.
        circuit_qubits: Number of qubits in the circuit (extracted from OriginIR
            QINIT line, without making any API call).
        supported_gates: Gates confirmed available on the target backend that are
            also used by this circuit.

    Note:
        Any dry-run success followed by actual submission failure is a
        critical bug. Please report it at the UnifiedQuantum issue tracker.
    """

    success: bool
    details: str
    warnings: tuple[str, ...] = ()
    error: str | None = None
    error_kind: str | None = None
    backend_name: str | None = None
    circuit_qubits: int | None = None
    supported_gates: tuple[str, ...] = ()
