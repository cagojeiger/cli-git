"""Pytest configuration and fixtures."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner():
    """Provide a CLI runner for testing."""
    return CliRunner()
