"""Platform-specific result normalizers.

This module provides functions to convert platform-specific result formats
into the unified UnifiedResult format. Each platform (OriginQ, Quafu, IBM)
has its own normalizer that handles the unique output format of that platform.

The normalizers are used by the adapter classes to ensure consistent
result handling across all platforms.

Usage::

    from uniqc.backend_adapter.task.normalizers import normalize_quafu
    from uniqc.backend_adapter.task.result_types import UnifiedResult

    # Convert Quafu result to unified format
    unified = normalize_quafu(quafu_result, task_id="abc123")
"""

from __future__ import annotations

__all__ = ["normalize_originq", "normalize_quafu", "normalize_ibm", "normalize_dummy"]

import warnings
from typing import Any

from .result_types import UnifiedResult


def normalize_originq(
    raw: dict[str, Any],
    task_id: str,
    shots: int = 1000,
    n_qubits: int | None = None,
) -> UnifiedResult:
    """Normalize OriginQ Cloud result format.

    OriginQ returns results either in the legacy probability format::

        {'key': ['0x0', '0x1', ...], 'value': [0.5, 0.3, ...]}

    where keys are hexadecimal bitstrings and values are probabilities, or
    as a plain counts dict::

        {0: 100, 1: 200, 7: 50}   # int outcome -> shot count
        {'0x0': 100, '0x1': 200}  # hex string outcome -> shot count

    Args:
        raw: Raw result dict from OriginQ Cloud API. Either the
            ``{"key": [...], "value": [...]}`` probability form or a flat
            counts dict mapping integer/hex/binary outcomes to shot counts.
        task_id: Task identifier.
        shots: Number of shots (default 1000). Ignored when ``raw`` is a
            counts dict (in which case the sum of counts is used).
        n_qubits: Number of qubits in the source circuit. If ``None`` the
            width is inferred from the highest observed integer outcome via
            :meth:`int.bit_length`, which is unsafe for sparse distributions
            where the most-significant qubits happen to read ``0`` (the
            resulting bitstrings will be shorter than the true register
            width). Passing the explicit ``n_qubits`` from
            ``circuit.qubit_num`` is strongly preferred and a
            :class:`UserWarning` is emitted when it is omitted.

    Returns:
        UnifiedResult with normalized probabilities and counts.

    Example:
        >>> raw = {'key': ['0x0', '0x3'], 'value': [0.5, 0.5]}
        >>> result = normalize_originq(raw, "task-1", n_qubits=2)
        >>> print(result.probabilities)
        {'00': 0.5, '11': 0.5}
    """
    is_probability_form = isinstance(raw, dict) and "key" in raw and "value" in raw

    if is_probability_form:
        keys = list(raw.get("key", []))
        values = list(raw.get("value", []))
    elif isinstance(raw, dict):
        # Plain counts dict: {outcome: count}
        keys = list(raw.keys())
        values = list(raw.values())
    else:
        keys = []
        values = []

    if not keys:
        return UnifiedResult.from_probabilities(
            probabilities={},
            shots=shots,
            platform="originq",
            task_id=task_id,
            raw_result=raw,
        )

    def _to_int(outcome: Any) -> int:
        if isinstance(outcome, int):
            return outcome
        text = str(outcome).strip()
        if text.startswith(("0x", "0X")):
            return int(text, 16)
        if text.startswith(("0b", "0B")):
            return int(text, 2)
        # Bare binary string (only 0/1 chars and at least one char)
        if text and set(text) <= {"0", "1"}:
            return int(text, 2)
        # Decimal fallback
        return int(text)

    # Determine number of qubits if not provided
    if n_qubits is None:
        warnings.warn(
            "normalize_originq called without explicit n_qubits; "
            "inferring width from max(outcome).bit_length() loses high-order "
            "zero qubits for sparse distributions. Pass n_qubits=circuit.qubit_num.",
            UserWarning,
            stacklevel=2,
        )
        max_val = 0
        for k in keys:
            try:
                max_val = max(max_val, _to_int(k))
            except (ValueError, TypeError):
                continue
        n_qubits = max(1, max_val.bit_length())

    if is_probability_form:
        probs: dict[str, float] = {}
        for outcome, prob in zip(keys, values, strict=False):
            try:
                int_val = _to_int(outcome)
                bin_key = bin(int_val)[2:].zfill(n_qubits)
                probs[bin_key] = float(prob)
            except (ValueError, TypeError):
                continue

        return UnifiedResult.from_probabilities(
            probabilities=probs,
            shots=shots,
            platform="originq",
            task_id=task_id,
            raw_result=raw,
        )

    # Counts form
    counts: dict[str, int] = {}
    for outcome, count in zip(keys, values, strict=False):
        try:
            int_val = _to_int(outcome)
            bin_key = bin(int_val)[2:].zfill(n_qubits)
            counts[bin_key] = counts.get(bin_key, 0) + int(count)
        except (ValueError, TypeError):
            continue

    return UnifiedResult.from_counts(
        counts=counts,
        platform="originq",
        task_id=task_id,
        raw_result=raw,
    )


def normalize_quafu(
    result_obj: Any,
    task_id: str,
    backend_name: str | None = None,
) -> UnifiedResult:
    """Normalize Quafu ExecResult format.

    Quafu returns an ExecResult object with attributes:
        - counts: Dict[str, int] measurement counts
        - probabilities: Dict[str, float] measurement probabilities
        - task_status: Status string

    Args:
        result_obj: Quafu ExecResult object.
        task_id: Task identifier.
        backend_name: Optional backend name override.

    Returns:
        UnifiedResult with counts and probabilities.

    Example:
        >>> # result_obj is a quafu ExecResult
        >>> unified = normalize_quafu(result_obj, "task-2")
        >>> print(unified.counts)
        {'00': 512, '11': 488}
    """
    # Extract counts from ExecResult
    counts: dict[str, int] = {}
    if hasattr(result_obj, "counts") and result_obj.counts is not None:
        # Quafu uses q[0]/c[0] as the LEFTMOST bitstring character. uniqc
        # convention (docs/source/guide/platform_conventions.md §2.6) puts
        # c[0] on the RIGHT. Reverse each key here.
        counts = {str(k)[::-1]: int(v) for k, v in dict(result_obj.counts).items()}

    # Try to get backend name from result object
    if backend_name is None and hasattr(result_obj, "task"):
        task_info = getattr(result_obj, "task", {})
        if isinstance(task_info, dict):
            backend_name = task_info.get("backend")

    return UnifiedResult.from_counts(
        counts=counts,
        platform="quafu",
        task_id=task_id,
        backend_name=backend_name,
        raw_result=result_obj,
    )


def normalize_ibm(
    result_obj: Any,
    task_id: str,
) -> UnifiedResult:
    """Normalize IBM Quantum (Qiskit) Result format.

    IBM returns a Qiskit Result object with:
        - get_counts(): Returns dict or list of dicts for measurement counts
        - to_dict(): Returns full result as dict with metadata

    Args:
        result_obj: Qiskit Result object.
        task_id: Task identifier (Qiskit job ID).

    Returns:
        UnifiedResult with counts and probabilities.

    Note:
        For batch jobs, this normalizes the first circuit result only.
        Use result_obj.get_counts() directly for batch results.

    Example:
        >>> # result_obj is a qiskit Result
        >>> unified = normalize_ibm(result_obj, "job-123")
        >>> print(unified.counts)
        {'0x0': 512, '0x3': 488}
    """
    # Get counts from Result object
    counts: dict[str, int] = {}

    try:
        raw_counts = result_obj.get_counts()
        if isinstance(raw_counts, dict):
            counts = raw_counts
        elif isinstance(raw_counts, list) and len(raw_counts) > 0:
            counts = raw_counts[0] if isinstance(raw_counts[0], dict) else {}
    except (AttributeError, TypeError):
        pass

    # Extract backend name
    backend_name: str | None = None
    try:
        result_dict = result_obj.to_dict()
        backend_name = result_dict.get("backend_name")
    except (AttributeError, TypeError):
        pass

    # Convert counts keys to canonical binary form. Qiskit's
    # ``Result.get_counts()`` already follows the c[N-1]…c[0] (c[0]=rightmost)
    # convention which matches uniqc — see docs/source/guide/
    # platform_conventions.md §2.6. We only normalise hex keys (legacy
    # output) into plain binary strings, without changing bit order.
    normalized_counts: dict[str, int] = {}
    for key, value in counts.items():
        if isinstance(key, str):
            stripped = key.replace(" ", "")
            if stripped.startswith("0x"):
                # Width is unknown from a bare hex key; fall back to the
                # minimum number of bits needed. Callers that need a fixed
                # width should pad on their side.
                try:
                    int_val = int(stripped, 16)
                    width = max(1, int_val.bit_length())
                    bin_key = format(int_val, f"0{width}b")
                    normalized_counts[bin_key] = normalized_counts.get(bin_key, 0) + int(value)
                except ValueError:
                    normalized_counts[stripped] = int(value)
            else:
                normalized_counts[stripped] = normalized_counts.get(stripped, 0) + int(value)
        else:
            normalized_counts[str(key)] = int(value)

    return UnifiedResult.from_counts(
        counts=normalized_counts,
        platform="ibm",
        task_id=task_id,
        backend_name=backend_name,
        raw_result=result_obj,
    )


def normalize_dummy(
    probs_list: list[float],
    task_id: str,
    shots: int = 1000,
) -> UnifiedResult:
    """Normalize local simulator probability output.

    The local OriginIR simulator returns a list of probabilities
    indexed by computational basis state (little-endian).

    Args:
        probs_list: List of probabilities indexed by basis state.
        task_id: Task identifier.
        shots: Number of shots.

    Returns:
        UnifiedResult with probabilities converted to bitstrings.

    Example:
        >>> probs = [0.5, 0.0, 0.0, 0.5]  # |00> and |11> each 50%
        >>> result = normalize_dummy(probs, "task-3")
        >>> print(result.probabilities)
        {'00': 0.5, '11': 0.5}
    """
    n_qubits = len(probs_list).bit_length() - 1
    if n_qubits == 0:
        n_qubits = 1

    probs: dict[str, float] = {}
    for i, prob in enumerate(probs_list):
        if prob > 0:
            bin_key = bin(i)[2:].zfill(n_qubits)
            probs[bin_key] = prob

    return UnifiedResult.from_probabilities(
        probabilities=probs,
        shots=shots,
        platform="dummy",
        task_id=task_id,
    )
