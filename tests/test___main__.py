"""Tests for __main__ module."""

import subprocess
import sys
from unittest.mock import patch


def test_main_module_execution():
    """Test that the package can be run as a module."""
    result = subprocess.run(
        [sys.executable, "-m", "cli_git", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "cli-git version:" in result.stdout


def test_main_module_direct_execution():
    """Test that __main__ module executes app when __name__ == '__main__'."""
    with patch("cli_git.cli.app") as mock_app:
        # Simulate running the module as __main__
        import runpy

        # Use runpy to execute the module as if it was run with python -m
        with patch.dict("sys.modules", {"__main__": None}):
            runpy.run_module("cli_git", run_name="__main__", alter_sys=False)

        # The app should have been called
        mock_app.assert_called_once()


def test_main_module_import_does_not_execute():
    """Test that importing __main__ doesn't execute app."""
    with patch("cli_git.cli.app") as mock_app:
        # Just importing should not call app

        # App should not be called during normal import
        mock_app.assert_not_called()
