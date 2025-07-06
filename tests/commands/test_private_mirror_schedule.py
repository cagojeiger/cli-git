"""Tests for private mirror command with custom schedule behavior."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestPrivateMirrorSchedule:
    """Test private mirror command schedule functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        # Mock create_mirrorkeep_file for all tests to avoid file system errors
        with patch("cli_git.commands.private_mirror.create_mirrorkeep_file") as mock_create:
            mock_create.return_value = None
            yield

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_private_mirror_with_explicit_schedule(
        self,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test private mirror with explicitly provided schedule."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/repo-mirror"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        # Run command with explicit schedule
        result = runner.invoke(
            app,
            ["private-mirror", "https://github.com/owner/repo", "--schedule", "0 12 * * 1"],
        )

        # Verify success
        assert result.exit_code == 0
        assert "✅ Success! Your private mirror is ready:" in result.stdout
        # Should not show random schedule message
        assert "🎲 Random sync schedule:" not in result.stdout
        # Should show regular schedule message
        assert "Sync schedule:" in result.stdout

        # Verify mirror operation was called with explicit schedule
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/repo",
            target_name="mirror-repo",
            username="testuser",
            org=None,
            schedule="0 12 * * 1",  # Explicit schedule
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    @patch("cli_git.commands.private_mirror.generate_random_biweekly_schedule")
    def test_private_mirror_validates_random_schedule(
        self,
        mock_generate_schedule,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test that generated random schedule is used correctly."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/repo-mirror"
        # Return a specific random schedule
        mock_generate_schedule.return_value = "42 15 8,22 * *"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        # Run command without schedule
        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        # Verify the random schedule was generated
        mock_generate_schedule.assert_called_once()

        # Verify the output contains the random schedule
        assert "🎲 Random sync schedule: 42 15 8,22 * *" in result.stdout
        assert "(매월 8일, 22일 15:42 UTC)" in result.stdout

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    def test_private_mirror_invalid_schedule(
        self,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test private mirror with invalid cron schedule."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        # Run command with invalid schedule
        result = runner.invoke(
            app,
            ["private-mirror", "https://github.com/owner/repo", "--schedule", "invalid"],
        )

        # Should fail with validation error
        assert result.exit_code == 1
        assert "❌ Invalid cron schedule:" in result.stdout
