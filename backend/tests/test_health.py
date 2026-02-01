"""Basic sanity tests for the Briefly backend."""

import pytest


class TestBasic:
    """Basic tests that don't require app import."""

    def test_true(self) -> None:
        """Placeholder test so pytest doesn't exit with code 5."""
        assert True

    def test_python_version(self) -> None:
        """Verify Python version is 3.11+."""
        import sys

        assert sys.version_info >= (3, 11)
