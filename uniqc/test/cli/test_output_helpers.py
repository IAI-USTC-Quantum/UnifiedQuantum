"""Regression tests for CLI output helpers.

These tests lock the contract of ``extract_counts_and_probs`` so the CLI
``task show`` / ``uniqc result`` displays stay compatible with the result
shapes each cloud adapter actually produces:

- dummy / quafu: ``{"counts": {...}, "probabilities": {...}}``
- originq      : ``[{"key": "0x..", "value": prob}, ...]``
- ibm          : ``[{"0x..": int, ...}, ...]`` (list of count dicts)
- legacy flat  : ``{"state": int}``
"""

from __future__ import annotations

import pytest

from uniqc.cli.output import extract_counts_and_probs


class TestExtractCountsAndProbs:
    def test_nested_counts_probabilities(self):
        """dummy / quafu shape: pass counts through, keep probabilities."""
        result = {
            "counts": {"00": 512, "11": 488},
            "probabilities": {"00": 0.512, "11": 0.488},
        }
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 512, "11": 488}
        assert probs == pytest.approx({"00": 0.512, "11": 0.488})

    def test_nested_counts_only_reconstructs_probs(self):
        result = {"counts": {"00": 8, "11": 8}}
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 8, "11": 8}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_nested_probabilities_only_with_shots(self):
        """probabilities-only + shots -> reconstruct integer counts."""
        result = {"probabilities": {"00": 0.5, "11": 0.5}}
        counts, probs = extract_counts_and_probs(result, shots=1000)

        assert counts == {"00": 500, "11": 500}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_nested_probabilities_only_without_shots(self):
        """probabilities-only + no shots -> empty counts, keep probs."""
        result = {"probabilities": {"00": 0.5, "11": 0.5}}
        counts, probs = extract_counts_and_probs(result)

        assert counts == {}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_originq_key_value_list(self):
        """originq single-task shape: [{'key': '0x..', 'value': prob}, ...]."""
        result = [
            {"key": "0x0", "value": 0.5},
            {"key": "0x3", "value": 0.5},
        ]
        counts, probs = extract_counts_and_probs(result, shots=1000)

        assert counts == {"00": 500, "11": 500}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_originq_key_value_list_without_shots(self):
        """Without shots, we still expose probabilities."""
        result = [
            {"key": "0x0", "value": 0.5},
            {"key": "0x3", "value": 0.5},
        ]
        counts, probs = extract_counts_and_probs(result)

        assert counts == {}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_ibm_list_of_count_dicts(self):
        """IBM single-task shape: [{'0x..': int, ...}, ...]. Hex keys are normalized."""
        result = [{"0x0": 512, "0x3": 488}]
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 512, "11": 488}
        assert probs == pytest.approx({"00": 0.512, "11": 0.488})

    def test_ibm_batch_merges_counts(self):
        """For a batch-style list, we merge per-circuit counts."""
        result = [{"00": 400, "11": 100}, {"00": 100, "11": 400}]
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 500, "11": 500}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_legacy_flat_counts(self):
        """Legacy flat counts shape still works."""
        result = {"00": 512, "11": 488}
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 512, "11": 488}
        assert probs == pytest.approx({"00": 0.512, "11": 0.488})

    def test_flat_probabilities(self):
        """Flat probability dict (floats) is treated as probabilities."""
        result = {"00": 0.5, "11": 0.5}
        counts, probs = extract_counts_and_probs(result, shots=16)

        assert counts == {"00": 8, "11": 8}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_empty_or_none(self):
        assert extract_counts_and_probs(None) == ({}, {})
        assert extract_counts_and_probs({}) == ({}, {})
        assert extract_counts_and_probs([]) == ({}, {})

    def test_unified_result_single(self):
        """``UnifiedResult`` (e.g. from ``wait_for_result``) is unwrapped."""
        from uniqc.backend_adapter.task.result_types import UnifiedResult

        result = UnifiedResult.from_counts({"00": 512, "11": 488}, "dummy", "task-x")
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 512, "11": 488}
        assert probs == pytest.approx({"00": 0.512, "11": 0.488})

    def test_unified_result_probs_only_uses_internal_shots(self):
        """``from_probabilities`` populates ``shots``; reconstructed counts use it."""
        from uniqc.backend_adapter.task.result_types import UnifiedResult

        # Build a UnifiedResult that exposes probabilities (and shots) but
        # whose counts dict has been cleared to mimic an adapter that
        # only normalised probabilities.
        result = UnifiedResult.from_probabilities({"00": 0.5, "11": 0.5}, 1000, "originq", "task-y")
        result.counts = {}
        counts, probs = extract_counts_and_probs(result)

        assert counts == {"00": 500, "11": 500}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})

    def test_unified_result_batch_merges(self):
        """``list[UnifiedResult]`` (native batch) merges counts across circuits."""
        from uniqc.backend_adapter.task.result_types import UnifiedResult

        results = [
            UnifiedResult.from_counts({"00": 400, "11": 100}, "ibm", "t-1"),
            UnifiedResult.from_counts({"00": 100, "11": 400}, "ibm", "t-2"),
        ]
        counts, probs = extract_counts_and_probs(results)

        assert counts == {"00": 500, "11": 500}
        assert probs == pytest.approx({"00": 0.5, "11": 0.5})
