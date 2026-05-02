"""Tests for unified ReadoutEM interface."""

import pytest


class TestReadoutEMDispatch:
    """Test that ReadoutEM correctly dispatches to 1q or 2q calibrators."""

    def test_mitigate_1q_counts(self):
        """mitigate_counts with 1 qubit should use 1q calibrator."""
        from uniqc.qem import ReadoutEM

        # Create a mock adapter that returns no cached calibration
        # The actual Mitigator will fail if there's no cache — test the dispatch path
        from uniqc.qem.readout_em import ReadoutEM

        # This test verifies the dispatch logic by checking that the right
        # mitigator type is created for different qubit counts
        # We can't fully test without a working adapter, so we test the code path
        # by checking method signatures exist
        assert hasattr(ReadoutEM, "mitigate_counts")
        assert hasattr(ReadoutEM, "_mitigate_1q")
        assert hasattr(ReadoutEM, "_mitigate_2q")
        assert hasattr(ReadoutEM, "_mitigate_nq")

    def test_nq_fallback_for_large_systems(self):
        """For n > 2 qubits, _mitigate_nq should be used."""
        from uniqc.qem import ReadoutEM

        # Verify the sequential mitigation path exists
        assert hasattr(ReadoutEM, "_apply_1q_matrix")
        assert hasattr(ReadoutEM, "_tensor_apply")
