"""Tests for gh CLI utilities."""

import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from cli_git.utils.gh import (
    GitHubError,
    add_repo_secret,
    check_gh_auth,
    create_private_repo,
    get_current_username,
    get_user_organizations,
    mask_token,
    run_gh_auth_login,
    validate_github_token,
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

    @patch("subprocess.run")
    def test_run_gh_auth_login_success(self, mock_run):
        """Test successful gh auth login."""
        mock_run.return_value = MagicMock(returncode=0)

        result = run_gh_auth_login()
        assert result is True
        mock_run.assert_called_once_with(["gh", "auth", "login"], check=False)

    @patch("subprocess.run")
    def test_run_gh_auth_login_failure(self, mock_run):
        """Test failed gh auth login."""
        mock_run.return_value = MagicMock(returncode=1)

        result = run_gh_auth_login()
        assert result is False

    @patch("subprocess.run")
    def test_run_gh_auth_login_file_not_found(self, mock_run):
        """Test gh auth login when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = run_gh_auth_login()
        assert result is False

    @patch("subprocess.run")
    def test_get_user_organizations_success(self, mock_run):
        """Test getting user organizations."""
        mock_run.return_value = MagicMock(returncode=0, stdout="org1\norg2\n")

        orgs = get_user_organizations()
        assert orgs == ["org1", "org2"]
        mock_run.assert_called_once_with(
            ["gh", "api", "user/orgs", "-q", ".[].login"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_user_organizations_empty(self, mock_run):
        """Test getting empty organizations list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        orgs = get_user_organizations()
        assert orgs == []

    @patch("subprocess.run")
    def test_get_user_organizations_failure(self, mock_run):
        """Test handling error when getting organizations."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["gh", "api", "user/orgs"], stderr="Not authenticated"
        )

        with pytest.raises(GitHubError, match="Failed to get organizations"):
            get_user_organizations()

    @patch("subprocess.run")
    def test_get_upstream_default_branch_success(self, mock_run):
        """Test successfully getting upstream default branch."""
        from cli_git.utils.gh import get_upstream_default_branch

        mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="", check=True)

        branch = get_upstream_default_branch("https://github.com/owner/repo")

        assert branch == "main"
        mock_run.assert_called_once_with(
            ["gh", "api", "repos/owner/repo", "-q", ".default_branch"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_upstream_default_branch_master(self, mock_run):
        """Test getting upstream default branch that is master."""
        from cli_git.utils.gh import get_upstream_default_branch

        mock_run.return_value = Mock(returncode=0, stdout="master\n", stderr="", check=True)

        branch = get_upstream_default_branch("https://github.com/owner/repo")

        assert branch == "master"

    @patch("subprocess.run")
    def test_get_upstream_default_branch_failure(self, mock_run):
        """Test handling error when getting default branch."""
        from cli_git.utils.gh import get_upstream_default_branch

        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["gh", "api"], stderr="Repository not found"
        )

        with pytest.raises(GitHubError, match="Failed to get default branch"):
            get_upstream_default_branch("https://github.com/owner/repo")

    def test_get_upstream_default_branch_invalid_url(self):
        """Test handling invalid repository URL."""
        from cli_git.utils.gh import get_upstream_default_branch

        with pytest.raises(GitHubError, match="Invalid repository URL"):
            get_upstream_default_branch("not-a-valid-url")

    @patch("subprocess.run")
    def test_validate_github_token_valid(self, mock_run):
        """Test validating a valid GitHub token."""
        mock_run.return_value = MagicMock(returncode=0)

        result = validate_github_token("ghp_test123token")
        assert result is True
        mock_run.assert_called_once_with(
            ["gh", "api", "user", "-H", "Authorization: token ghp_test123token"],
            capture_output=True,
            text=True,
        )

    @patch("subprocess.run")
    def test_validate_github_token_invalid(self, mock_run):
        """Test validating an invalid GitHub token."""
        mock_run.return_value = MagicMock(returncode=1)

        result = validate_github_token("invalid_token")
        assert result is False

    def test_validate_github_token_empty(self):
        """Test validating empty token."""
        result = validate_github_token("")
        assert result is False

    @patch("subprocess.run")
    def test_validate_github_token_exception(self, mock_run):
        """Test handling exception during token validation."""
        mock_run.side_effect = Exception("Unexpected error")

        result = validate_github_token("token")
        assert result is False

    def test_mask_token_standard(self):
        """Test masking standard GitHub token."""
        token = "ghp_1234567890abcdef"
        masked = mask_token(token)
        assert masked == "ghp_...cdef"

    def test_mask_token_pat(self):
        """Test masking GitHub PAT token."""
        token = "github_pat_1234567890abcdef"
        masked = mask_token(token)
        assert masked == "gith...cdef"

    def test_mask_token_short(self):
        """Test masking short token."""
        token = "short"
        masked = mask_token(token)
        assert masked == "***"

    def test_mask_token_empty(self):
        """Test masking empty token."""
        masked = mask_token("")
        assert masked == ""
