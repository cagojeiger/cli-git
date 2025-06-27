"""Tests for gh CLI utilities."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from cli_git.utils.gh import (
    GitHubError,
    add_repo_secret,
    check_gh_auth,
    create_private_repo,
    get_current_username,
)


class TestGhUtils:
    """Test cases for gh CLI utilities."""

    @patch("subprocess.run")
    def test_check_gh_auth_success(self, mock_run):
        """Test successful gh authentication check."""
        mock_run.return_value = MagicMock(returncode=0)

        result = check_gh_auth()
        assert result is True
        mock_run.assert_called_once_with(["gh", "auth", "status"], capture_output=True, text=True)

    @patch("subprocess.run")
    def test_check_gh_auth_failure(self, mock_run):
        """Test failed gh authentication check."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="You are not logged into any GitHub hosts"
        )

        result = check_gh_auth()
        assert result is False

    @patch("subprocess.run")
    def test_get_current_username_success(self, mock_run):
        """Test getting current GitHub username."""
        mock_run.return_value = MagicMock(returncode=0, stdout="testuser\n")

        username = get_current_username()
        assert username == "testuser"
        mock_run.assert_called_once_with(
            ["gh", "api", "user", "-q", ".login"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_get_current_username_failure(self, mock_run):
        """Test handling error when getting username."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["gh", "api", "user"], stderr="Not authenticated"
        )

        with pytest.raises(GitHubError, match="Failed to get current user"):
            get_current_username()

    @patch("subprocess.run")
    def test_create_private_repo_success(self, mock_run):
        """Test creating private repository."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/testuser/test-repo\n"
        )

        url = create_private_repo("test-repo", "Test description")
        assert url == "https://github.com/testuser/test-repo"

        expected_cmd = [
            "gh",
            "repo",
            "create",
            "test-repo",
            "--private",
            "--description",
            "Test description",
        ]
        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True, check=True)

    @patch("subprocess.run")
    def test_create_private_repo_with_org(self, mock_run):
        """Test creating private repository in organization."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="https://github.com/testorg/test-repo\n"
        )

        url = create_private_repo("test-repo", org="testorg")
        assert url == "https://github.com/testorg/test-repo"

        expected_cmd = ["gh", "repo", "create", "testorg/test-repo", "--private"]
        mock_run.assert_called_once()
        actual_cmd = mock_run.call_args[0][0]
        assert actual_cmd[:5] == expected_cmd[:5]

    @patch("subprocess.run")
    def test_create_private_repo_already_exists(self, mock_run):
        """Test handling repository already exists error."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1,
            ["gh", "repo", "create"],
            stderr="failed to create repository: HTTP 422: Validation Failed",
        )

        with pytest.raises(GitHubError, match="Repository .* already exists"):
            create_private_repo("test-repo")

    @patch("subprocess.run")
    def test_add_repo_secret_success(self, mock_run):
        """Test adding repository secret."""
        mock_run.return_value = MagicMock(returncode=0)

        add_repo_secret("testuser/test-repo", "MY_SECRET", "secret-value")

        expected_cmd = ["gh", "secret", "set", "MY_SECRET", "--repo", "testuser/test-repo"]
        mock_run.assert_called_once()
        actual_cmd = mock_run.call_args[0][0]
        assert actual_cmd == expected_cmd

        # Check stdin was used for secret value
        assert mock_run.call_args.kwargs["input"] == "secret-value"

    @patch("subprocess.run")
    def test_add_repo_secret_failure(self, mock_run):
        """Test handling error when adding secret."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["gh", "secret", "set"], stderr="failed to set secret"
        )

        with pytest.raises(GitHubError, match="Failed to set secret"):
            add_repo_secret("testuser/test-repo", "MY_SECRET", "value")
