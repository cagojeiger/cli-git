"""Tests for version command."""

import re

import pytest

from cli_git import __version__


def test_version_format():
    """Test that version follows semantic versioning format."""
    pattern = r"^\d+\.\d+\.\d+$|^dev$"
    assert re.match(pattern, __version__), f"Version {__version__} doesn't match expected format"


def test_cli_version_command(runner):
    """Test that --version flag works correctly."""
    from cli_git.cli import app

    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "cli-git version:" in result.stdout
    assert __version__ in result.stdout


def test_cli_version_short_flag(runner):
    """Test that -v flag works as short version."""
    from cli_git.cli import app

    result = runner.invoke(app, ["-v"])
    assert result.exit_code == 0
    assert "cli-git version:" in result.stdout
    assert __version__ in result.stdout


def test_version_callback_exit():
    """Test that version callback exits the program."""
    from cli_git.cli import version_callback

    with pytest.raises(SystemExit) as exc_info:
        version_callback(True)
    assert exc_info.value.code == 0


def test_version_callback_no_exit():
    """Test that version callback doesn't exit when value is False."""
    from cli_git.cli import version_callback

    result = version_callback(False)
    assert result is None
