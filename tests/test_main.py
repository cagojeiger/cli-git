"""Tests for __main__ module."""

import subprocess
import sys


def test_main_module_execution():
    """Test that the package can be run as a module."""
    result = subprocess.run(
        [sys.executable, "-m", "cli_git", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "cli-git version:" in result.stdout
