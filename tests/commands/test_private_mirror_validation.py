"""Tests for private-mirror command with validation."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestPrivateMirrorValidation:
    """Test validation in private-mirror command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_auth_and_config(self):
        """Mock authentication and basic configuration."""
        with patch("cli_git.commands.private_mirror.check_gh_auth") as mock_auth:
            with patch("cli_git.commands.private_mirror.ConfigManager") as mock_config_manager:
                mock_auth.return_value = True
                mock_manager = MagicMock()
                mock_config_manager.return_value = mock_manager
                mock_manager.get_config.return_value = {
                    "github": {
                        "username": "testuser",
                        "default_org": "",
                        "slack_webhook_url": "",
                    },
                    "preferences": {"default_prefix": "mirror-"},
                }
                yield mock_auth, mock_manager

    def test_invalid_github_url(self, runner, mock_auth_and_config):
        """Test with invalid GitHub URL."""
        result = runner.invoke(app, ["private-mirror", "https://gitlab.com/owner/repo"])

        assert result.exit_code == 1
        assert "❌ Invalid GitHub repository URL" in result.stdout
        assert "Expected format:" in result.stdout

    def test_invalid_organization(self, runner, mock_auth_and_config):
        """Test with organization user doesn't have access to."""
        with patch("cli_git.utils.validators.get_user_organizations") as mock_get_orgs:
            mock_get_orgs.return_value = ["myorg", "anotherorg"]

            result = runner.invoke(
                app, ["private-mirror", "https://github.com/owner/repo", "--org", "invalidorg"]
            )

            assert result.exit_code == 1
            assert "❌ Organization 'invalidorg' not found" in result.stdout
            assert "Available organizations: myorg, anotherorg" in result.stdout

    def test_invalid_cron_schedule(self, runner, mock_auth_and_config):
        """Test with invalid cron schedule."""
        result = runner.invoke(
            app, ["private-mirror", "https://github.com/owner/repo", "--schedule", "invalid cron"]
        )

        assert result.exit_code == 1
        assert "❌ Invalid cron schedule" in result.stdout
        assert "Expected 5 fields" in result.stdout

    def test_invalid_cron_minute(self, runner, mock_auth_and_config):
        """Test with invalid minute in cron schedule."""
        result = runner.invoke(
            app, ["private-mirror", "https://github.com/owner/repo", "--schedule", "60 * * * *"]
        )

        assert result.exit_code == 1
        assert "❌ Invalid minute field: '60'" in result.stdout

    def test_invalid_prefix(self, runner, mock_auth_and_config):
        """Test with invalid prefix characters."""
        result = runner.invoke(
            app, ["private-mirror", "https://github.com/owner/repo", "--prefix", "my prefix"]
        )

        assert result.exit_code == 1
        assert "❌ Prefix contains invalid characters" in result.stdout

    def test_invalid_repository_name(self, runner, mock_auth_and_config):
        """Test when combined prefix and repo name creates invalid name."""
        # Create a repo name that when combined with prefix becomes invalid
        with patch("cli_git.commands.private_mirror.extract_repo_info") as mock_extract:
            mock_extract.return_value = ("owner", ".git")  # Invalid repo name

            result = runner.invoke(
                app, ["private-mirror", "https://github.com/owner/.git", "--prefix", "mirror-"]
            )

            assert result.exit_code == 1
            assert "❌ Repository name cannot end with '.git'" in result.stdout

    def test_reserved_repository_name(self, runner, mock_auth_and_config):
        """Test with reserved repository name."""
        with patch("cli_git.commands.private_mirror.extract_repo_info") as mock_extract:
            mock_extract.return_value = ("owner", "con")  # Reserved name

            result = runner.invoke(
                app, ["private-mirror", "https://github.com/owner/con", "--prefix", ""]
            )

            assert result.exit_code == 1
            assert "❌ Repository name is reserved: 'con'" in result.stdout

    def test_valid_inputs_pass_validation(self, runner, mock_auth_and_config):
        """Test that valid inputs pass validation."""
        with patch("cli_git.commands.private_mirror.extract_repo_info") as mock_extract:
            with patch("cli_git.commands.private_mirror.get_current_username") as mock_username:
                with patch("cli_git.commands.private_mirror.private_mirror_operation") as mock_op:
                    mock_extract.return_value = ("owner", "repo")
                    mock_username.return_value = "testuser"
                    mock_op.return_value = "https://github.com/testuser/mirror-repo"

                    result = runner.invoke(
                        app,
                        [
                            "private-mirror",
                            "https://github.com/owner/repo",
                            "--schedule",
                            "0 */6 * * *",
                            "--prefix",
                            "backup-",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "✅ Success!" in result.stdout

                    # Verify the operation was called with validated inputs
                    mock_op.assert_called_once()
                    call_args = mock_op.call_args[1]
                    assert call_args["schedule"] == "0 */6 * * *"
                    assert call_args["target_name"] == "backup-repo"

    def test_custom_repo_name_validation(self, runner, mock_auth_and_config):
        """Test validation with custom repository name."""
        result = runner.invoke(
            app,
            ["private-mirror", "https://github.com/owner/repo", "--repo", "my-invalid-repo.git"],
        )

        assert result.exit_code == 1
        assert "❌ Repository name cannot end with '.git'" in result.stdout

    def test_organization_api_failure_allows_proceed(self, runner, mock_auth_and_config):
        """Test that organization validation failure (API issue) doesn't block."""
        with patch("cli_git.utils.validators.get_user_organizations") as mock_get_orgs:
            with patch("cli_git.commands.private_mirror.extract_repo_info") as mock_extract:
                with patch("cli_git.commands.private_mirror.get_current_username") as mock_username:
                    with patch(
                        "cli_git.commands.private_mirror.private_mirror_operation"
                    ) as mock_op:
                        # Simulate API failure
                        from cli_git.utils.gh import GitHubError

                        mock_get_orgs.side_effect = GitHubError("API error")
                        mock_extract.return_value = ("owner", "repo")
                        mock_username.return_value = "testuser"
                        mock_op.return_value = "https://github.com/someorg/mirror-repo"

                        # Should still work even if org validation fails
                        result = runner.invoke(
                            app,
                            ["private-mirror", "https://github.com/owner/repo", "--org", "someorg"],
                        )

                        assert result.exit_code == 0
                        assert "✅ Success!" in result.stdout
