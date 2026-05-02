"""Tests for readout calibrator."""

import pytest


class TestReadoutCalibrator1Q:
    def test_perfect_readout_identity_matrix(self, tmp_path):
        """With a noiseless DummyAdapter, confusion matrix should be identity."""
        from uniqc.calibration.readout import ReadoutCalibrator
        from uniqc.task.adapters import DummyAdapter

        adapter = DummyAdapter()  # noiseless
        cal = ReadoutCalibrator(adapter=adapter, shots=1000, cache_dir=tmp_path)
        result = cal.calibrate_1q(qubit=0)

        assert result["type"] == "readout_1q"
        assert result["qubit"] == 0
        cm = result["confusion_matrix"]
        # Noiseless → [[1, 0], [0, 1]]
        assert cm[0][0] == pytest.approx(1.0)
        assert cm[1][1] == pytest.approx(1.0)
        assert result["assignment_fidelity"] == pytest.approx(1.0)
        assert "calibrated_at" in result

    def test_cache_file_created(self, tmp_path):
        """Calibration should create a file in the cache directory."""
        from uniqc.calibration.readout import ReadoutCalibrator
        from uniqc.task.adapters import DummyAdapter

        adapter = DummyAdapter()
        cal = ReadoutCalibrator(adapter=adapter, shots=100, cache_dir=tmp_path)
        cal.calibrate_1q(qubit=5)

        files = list(tmp_path.glob("readout_1q_*.json"))
        assert len(files) == 1, f"Expected 1 file, got: {files}"
        assert "q5" in files[0].name

    def test_calibrate_multiple_qubits(self, tmp_path):
        """calibrate_qubits should calibrate each qubit."""
        from uniqc.calibration.readout import ReadoutCalibrator
        from uniqc.task.adapters import DummyAdapter

        adapter = DummyAdapter()
        cal = ReadoutCalibrator(adapter=adapter, shots=100, cache_dir=tmp_path)
        results = cal.calibrate_qubits([0, 1, 2])

        assert len(results) == 3
        for q in [0, 1, 2]:
            assert results[q]["qubit"] == q
            assert results[q]["assignment_fidelity"] == pytest.approx(1.0)

    def test_confusion_matrix_shape(self, tmp_path):
        """Confusion matrix should be 2x2 for single-qubit."""
        from uniqc.calibration.readout import ReadoutCalibrator
        from uniqc.task.adapters import DummyAdapter

        adapter = DummyAdapter()
        cal = ReadoutCalibrator(adapter=adapter, shots=100, cache_dir=tmp_path)
        result = cal.calibrate_1q(qubit=0)
        cm = result["confusion_matrix"]

        assert len(cm) == 2
        assert all(len(row) == 2 for row in cm)

    def test_calibrate_2q_identity(self, tmp_path):
        """Noiseless 2q adapter should give near-identity confusion matrix."""
        from uniqc.calibration.readout import ReadoutCalibrator
        from uniqc.task.adapters import DummyAdapter

        adapter = DummyAdapter()
        cal = ReadoutCalibrator(adapter=adapter, shots=200, cache_dir=tmp_path)
        result = cal.calibrate_2q(qubit_u=0, qubit_v=1)

        assert result["type"] == "readout_2q"
        assert result["qubit"] == (0, 1)
        cm = result["confusion_matrix"]
        assert len(cm) == 4
        # Diagonal should be ~1.0 (noiseless)
        for i in range(4):
            assert cm[i][i] == pytest.approx(1.0, abs=0.05)
        assert result["assignment_fidelity"] == pytest.approx(1.0, abs=0.05)
