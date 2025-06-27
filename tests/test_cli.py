"""Tests for main CLI functionality."""


def test_cli_help(runner):
    """Test that help command works."""
    from cli_git.cli import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "cli-git" in result.stdout
    assert "Show the version and exit" in result.stdout


def test_cli_no_args(runner):
    """Test CLI behavior with no arguments."""
    from cli_git.cli import app

    result = runner.invoke(app)
    assert result.exit_code == 0
