"""Tests for completion command."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app
from cli_git.commands.completion import detect_shell


class TestDetectShell:
    """Test shell detection function."""

    def test_detect_bash(self):
        """Test detecting bash shell."""
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            assert detect_shell() == "bash"

    def test_detect_zsh(self):
        """Test detecting zsh shell."""
        with patch.dict(os.environ, {"SHELL": "/usr/bin/zsh"}):
            assert detect_shell() == "zsh"

    def test_detect_fish(self):
        """Test detecting fish shell."""
        with patch.dict(os.environ, {"SHELL": "/usr/local/bin/fish"}):
            assert detect_shell() == "fish"

    def test_detect_unknown(self):
        """Test detecting unknown shell."""
        with patch.dict(os.environ, {"SHELL": "/bin/sh"}):
            assert detect_shell() == "unknown"

    def test_no_shell_env(self):
        """Test when SHELL environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert detect_shell() == "unknown"


class TestCompletionCommand:
    """Test completion installation command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.completion.detect_shell")
    def test_completion_unknown_shell(self, mock_detect_shell, runner):
        """Test completion with unknown shell."""
        mock_detect_shell.return_value = "unknown"

        result = runner.invoke(app, ["completion"])

        assert result.exit_code == 1
        assert "❌ Could not detect shell type" in result.stdout
        assert "cli-git --install-completion" in result.stdout

    @patch("cli_git.commands.completion.detect_shell")
    @patch("subprocess.run")
    def test_completion_bash_new_install(self, mock_run, mock_detect_shell, runner):
        """Test bash completion installation."""
        mock_detect_shell.return_value = "bash"

        # Mock subprocess to return completion script
        mock_run.return_value = MagicMock(
            stdout="# bash completion script\ncomplete -F _cli_git cli-git", returncode=0
        )

        with runner.isolated_filesystem():
            # Create a mock bashrc in the current directory
            home = Path.cwd()
            bashrc = home / ".bashrc"
            bashrc.write_text("# existing bashrc content\n")

            with patch("pathlib.Path.home", return_value=home):
                result = runner.invoke(app, ["completion"])

            assert result.exit_code == 0
            assert "🔍 Detected shell: bash" in result.stdout
            assert "✅ Completion installed to" in result.stdout
            assert f"source {bashrc}" in result.stdout

            # Check that completion was added
            content = bashrc.read_text()
            assert "# cli-git completion" in content

    @patch("cli_git.commands.completion.detect_shell")
    @patch("subprocess.run")
    def test_completion_bash_already_installed(self, mock_run, mock_detect_shell, runner):
        """Test bash completion when already installed."""
        mock_detect_shell.return_value = "bash"

        # Mock subprocess even though it won't be called
        mock_run.return_value = MagicMock(stdout="# bash completion script", returncode=0)

        with runner.isolated_filesystem():
            home = Path.cwd()
            bashrc = home / ".bashrc"
            bashrc.write_text("# existing content\n# cli-git completion\n# completion script")

            with patch("pathlib.Path.home", return_value=home):
                result = runner.invoke(app, ["completion"])

        assert result.exit_code == 0
        assert "✅ Completion already installed" in result.stdout

    @patch("cli_git.commands.completion.detect_shell")
    @patch("subprocess.run")
    def test_completion_zsh(self, mock_run, mock_detect_shell, runner):
        """Test zsh completion installation."""
        mock_detect_shell.return_value = "zsh"

        # Mock subprocess to return completion script
        mock_run.return_value = MagicMock(
            stdout="# zsh completion script\ncompdef _cli_git cli-git", returncode=0
        )

        with runner.isolated_filesystem():
            home = Path.cwd()
            zshrc = home / ".zshrc"
            zshrc.write_text("# existing zshrc content\n")

            with patch("pathlib.Path.home", return_value=home):
                result = runner.invoke(app, ["completion"])

            assert result.exit_code == 0
            assert "🔍 Detected shell: zsh" in result.stdout
            assert "✅ Completion installed to" in result.stdout

            # Check that completion was added
            content = zshrc.read_text()
            assert "# cli-git completion" in content

    @patch("cli_git.commands.completion.detect_shell")
    @patch("subprocess.run")
    def test_completion_fish(self, mock_run, mock_detect_shell, runner):
        """Test fish completion installation."""
        mock_detect_shell.return_value = "fish"

        # Mock subprocess to return completion script
        mock_run.return_value = MagicMock(
            stdout="# fish completion script\ncomplete -c cli-git", returncode=0
        )

        with runner.isolated_filesystem():
            home = Path.cwd()
            fish_dir = home / ".config" / "fish" / "completions"
            fish_dir.mkdir(parents=True, exist_ok=True)

            with patch("pathlib.Path.home", return_value=home):
                result = runner.invoke(app, ["completion"])

            assert result.exit_code == 0
            assert "🔍 Detected shell: fish" in result.stdout
            assert "✅ Completion installed to" in result.stdout
            assert "Completion will be available in new shell sessions" in result.stdout

            # Check that completion file was created
            completion_file = fish_dir / "cli-git.fish"
            assert completion_file.exists()
            assert "# fish completion script" in completion_file.read_text()

    @patch("cli_git.commands.completion.detect_shell")
    @patch("subprocess.run")
    def test_completion_subprocess_error(self, mock_run, mock_detect_shell, runner):
        """Test completion when subprocess fails."""
        mock_detect_shell.return_value = "bash"
        mock_run.side_effect = subprocess.CalledProcessError(1, "cli-git")

        result = runner.invoke(app, ["completion"])

        assert result.exit_code == 1
        assert "❌ Failed to generate completion" in result.stdout
        assert "cli-git --install-completion" in result.stdout

    @patch("cli_git.commands.completion.detect_shell")
    @patch("subprocess.run")
    @patch("builtins.open")
    def test_completion_file_write_error(self, mock_open, mock_run, mock_detect_shell, runner):
        """Test completion when file write fails."""
        mock_detect_shell.return_value = "bash"
        mock_run.return_value = MagicMock(stdout="# completion script", returncode=0)
        mock_open.side_effect = PermissionError("Permission denied")

        result = runner.invoke(app, ["completion"])

        assert result.exit_code == 1
        assert "❌ Error installing completion" in result.stdout
