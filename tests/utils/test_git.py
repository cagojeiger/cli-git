"""Tests for git utilities."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli_git.utils.git import (
    extract_repo_info,
    get_default_branch,
    run_git_command,
)


class TestGitUtils:
    """Test cases for git utilities."""

    @patch("subprocess.run")
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Success output\n", stderr="")

        result = run_git_command("status")
        assert result == "Success output"
        mock_run.assert_called_once_with(
            ["git", "status"], capture_output=True, text=True, cwd=None
        )

    @patch("subprocess.run")
    def test_run_git_command_with_cwd(self, mock_run):
        """Test git command execution with custom working directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Output\n", stderr="")
        test_path = Path("/test/path")

        result = run_git_command("status", cwd=test_path)
        assert result == "Output"
        mock_run.assert_called_once_with(
            ["git", "status"], capture_output=True, text=True, cwd=test_path
        )

    @patch("subprocess.run")
    def test_run_git_command_failure(self, mock_run):
        """Test git command execution failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error message")

        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            run_git_command("invalid-command")
        assert exc_info.value.stderr == "Error message"

    def test_extract_repo_info_https_url(self):
        """Test extracting repo info from HTTPS URL."""
        url = "https://github.com/owner/repo-name.git"
        owner, repo = extract_repo_info(url)
        assert owner == "owner"
        assert repo == "repo-name"

    def test_extract_repo_info_https_url_no_git(self):
        """Test extracting repo info from HTTPS URL without .git."""
        url = "https://github.com/owner/repo-name"
        owner, repo = extract_repo_info(url)
        assert owner == "owner"
        assert repo == "repo-name"

    def test_extract_repo_info_ssh_url(self):
        """Test extracting repo info from SSH URL."""
        url = "git@github.com:owner/repo-name.git"
        owner, repo = extract_repo_info(url)
        assert owner == "owner"
        assert repo == "repo-name"

    def test_extract_repo_info_with_subdomain(self):
        """Test extracting repo info from URL with subdomain."""
        url = "https://git.company.com/owner/repo-name.git"
        owner, repo = extract_repo_info(url)
        assert owner == "owner"
        assert repo == "repo-name"

    def test_extract_repo_info_invalid_url(self):
        """Test extracting repo info from invalid URL."""
        with pytest.raises(ValueError, match="Invalid repository URL"):
            extract_repo_info("not-a-valid-url")

    def test_extract_repo_info_no_owner(self):
        """Test extracting repo info from URL without owner."""
        with pytest.raises(ValueError, match="Invalid repository URL"):
            extract_repo_info("https://github.com/repo-name")

    @patch("subprocess.run")
    def test_run_git_command_with_quotes(self, mock_run):
        """Test git command with quoted arguments."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[main abcd123] Test message\n")

        result = run_git_command('commit -m "This is a test message with spaces"')

        # Verify the command was split correctly
        expected_cmd = ["git", "commit", "-m", "This is a test message with spaces"]
        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True, cwd=None)
        assert result == "[main abcd123] Test message"

    @patch("subprocess.run")
    def test_run_git_command_with_complex_message(self, mock_run):
        """Test git command with complex commit message."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[main abcd123] Complex message\n")

        # Test the exact message that was failing
        result = run_git_command('commit -m "Disable original workflows and add mirror sync"')

        # Verify the command was split correctly
        expected_cmd = ["git", "commit", "-m", "Disable original workflows and add mirror sync"]
        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True, cwd=None)
        assert result == "[main abcd123] Complex message"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_from_upstream_head(self, mock_run_git):
        """Test getting default branch from upstream HEAD."""
        mock_run_git.return_value = "refs/remotes/upstream/main"

        result = get_default_branch()

        mock_run_git.assert_called_with("symbolic-ref refs/remotes/upstream/HEAD", cwd=None)
        assert result == "main"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_from_upstream_head_master(self, mock_run_git):
        """Test getting default branch from upstream HEAD (master)."""
        mock_run_git.return_value = "refs/remotes/upstream/master"

        result = get_default_branch()

        assert result == "master"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_fallback_to_remote_branches(self, mock_run_git):
        """Test fallback to parsing remote branches."""
        # First call fails (no upstream HEAD)
        # Second call returns remote branches
        mock_run_git.side_effect = [
            subprocess.CalledProcessError(1, "git"),
            "  upstream/master\n  upstream/develop\n  origin/main",
        ]

        result = get_default_branch()

        assert result == "master"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_fallback_to_origin(self, mock_run_git):
        """Test fallback to origin branches when no upstream."""
        # First call fails (no upstream HEAD)
        # Second call returns only origin branches
        mock_run_git.side_effect = [
            subprocess.CalledProcessError(1, "git"),
            "  origin/main\n  origin/develop",
        ]

        result = get_default_branch()

        assert result == "main"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_fallback_to_local_branches(self, mock_run_git):
        """Test final fallback to local branches."""

        # First call fails (no upstream HEAD)
        # Second call fails (no remote branches)
        # Third call succeeds for main branch check
        def side_effect_func(cmd, cwd=None):
            if "symbolic-ref" in cmd:
                raise subprocess.CalledProcessError(1, "git")
            elif "branch -r" in cmd:
                raise subprocess.CalledProcessError(1, "git")
            elif "show-ref" in cmd and "main" in cmd:
                return ""  # show-ref for main succeeds
            else:
                raise subprocess.CalledProcessError(1, "git")

        mock_run_git.side_effect = side_effect_func

        result = get_default_branch()

        assert result == "main"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_fallback_to_master(self, mock_run_git):
        """Test fallback to master when main doesn't exist."""

        # First call fails (no upstream HEAD)
        # Second call fails (no remote branches)
        # Third call fails (no main branch)
        # Fourth call succeeds (master exists)
        def side_effect_func(cmd, cwd=None):
            if "symbolic-ref" in cmd:
                raise subprocess.CalledProcessError(1, "git")
            elif "branch -r" in cmd:
                raise subprocess.CalledProcessError(1, "git")
            elif "show-ref" in cmd and "main" in cmd:
                raise subprocess.CalledProcessError(1, "git")  # main check fails
            elif "show-ref" in cmd and "master" in cmd:
                return ""  # show-ref for master succeeds
            else:
                raise subprocess.CalledProcessError(1, "git")

        mock_run_git.side_effect = side_effect_func

        result = get_default_branch()

        assert result == "master"

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_all_methods_fail(self, mock_run_git):
        """Test when all detection methods fail."""
        # All calls fail
        mock_run_git.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(subprocess.CalledProcessError):
            get_default_branch()

    @patch("cli_git.utils.git.run_git_command")
    def test_get_default_branch_with_cwd(self, mock_run_git):
        """Test get_default_branch with custom working directory."""
        mock_run_git.return_value = "refs/remotes/upstream/develop"
        cwd = Path("/test/repo")

        result = get_default_branch(cwd=cwd)

        mock_run_git.assert_called_with("symbolic-ref refs/remotes/upstream/HEAD", cwd=cwd)
        assert result == "develop"
