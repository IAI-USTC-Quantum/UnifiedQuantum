"""Pytest tests for test module itself."""


class TestTestRunner:
    """Tests for test runner functionality."""

    def test_run_test_importable(self):
        """Test that run_test function is importable."""
        from uniqc.test import run_test

        assert callable(run_test)

    def test_run_test_docstring(self):
        """Test that run_test has proper docstring."""
        from uniqc.test import run_test

        assert run_test.__doc__ is not None
        assert "Imports are placed inside" in run_test.__doc__
