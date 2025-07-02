"""Tests for info command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestInfoCommand:
    """Test cases for info command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.info.ConfigManager")
    @patch("cli_git.commands.info.check_gh_auth")
    def test_info_display_basic(self, mock_check_auth, mock_config_manager, runner):
        """Test basic info display."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "default_org": "",
                "github_token": "",
                "slack_webhook_url": "",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = []

        # Run command
        result = runner.invoke(app, ["info"])

        # Verify
        assert result.exit_code == 0
        assert "📋 CLI-Git Configuration" in result.stdout
        assert "Username: testuser" in result.stdout
        assert "Default organization: (not set)" in result.stdout
        assert "gh CLI status: ✅ Authenticated" in result.stdout

    @patch("cli_git.commands.info.ConfigManager")
    @patch("cli_git.commands.info.check_gh_auth")
    def test_info_with_organization(self, mock_check_auth, mock_config_manager, runner):
        """Test info display with organization."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "default_org": "myorg",
                "github_token": "",
                "slack_webhook_url": "",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = []

        # Run command
        result = runner.invoke(app, ["info"])

        # Verify
        assert result.exit_code == 0
        assert "Default organization: myorg" in result.stdout

    @patch("cli_git.commands.info.ConfigManager")
    @patch("cli_git.commands.info.check_gh_auth")
    def test_info_not_authenticated(self, mock_check_auth, mock_config_manager, runner):
        """Test info display when not authenticated."""
        # Setup mocks
        mock_check_auth.return_value = False
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "default_org": "",
                "github_token": "",
                "slack_webhook_url": "",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = []

        # Run command
        result = runner.invoke(app, ["info"])

        # Verify
        assert result.exit_code == 0
        assert "gh CLI status: ❌ Not authenticated" in result.stdout

    @patch("cli_git.commands.info.ConfigManager")
    @patch("cli_git.commands.info.check_gh_auth")
    def test_info_with_recent_mirrors(self, mock_check_auth, mock_config_manager, runner):
        """Test info display with recent mirrors."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "default_org": "",
                "github_token": "",
                "slack_webhook_url": "",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = [
            {
                "upstream": "https://github.com/owner/repo1",
                "mirror": "https://github.com/testuser/repo1-mirror",
                "created_at": "2025-01-01T12:00:00Z",
            },
            {
                "upstream": "https://github.com/owner/repo2",
                "mirror": "https://github.com/testuser/repo2-mirror",
                "created_at": "2025-01-02T12:00:00Z",
            },
        ]

        # Run command
        result = runner.invoke(app, ["info"])

        # Verify
        assert result.exit_code == 0
        assert "Recent Mirrors:" in result.stdout
        assert "repo1-mirror" in result.stdout
        assert "owner/repo1" in result.stdout
        assert "repo2-mirror" in result.stdout
        assert "owner/repo2" in result.stdout

    @patch("cli_git.commands.info.ConfigManager")
    @patch("cli_git.commands.info.check_gh_auth")
    def test_info_json_output(self, mock_check_auth, mock_config_manager, runner):
        """Test JSON output format."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "default_org": "myorg",
                "github_token": "",
                "slack_webhook_url": "",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = [
            {
                "upstream": "https://github.com/owner/repo",
                "mirror": "https://github.com/testuser/repo-mirror",
                "created_at": "2025-01-01T12:00:00Z",
            }
        ]

        # Run command with JSON flag
        result = runner.invoke(app, ["info", "--json"])

        # Verify
        assert result.exit_code == 0

        # Parse JSON output
        output_data = json.loads(result.stdout)
        assert output_data["github"]["username"] == "testuser"
        assert output_data["github"]["default_org"] == "myorg"
        assert output_data["github"]["authenticated"] is True
        assert output_data["preferences"]["default_schedule"] == "0 0 * * *"
        assert len(output_data["recent_mirrors"]) == 1
        assert output_data["recent_mirrors"][0]["upstream"] == "https://github.com/owner/repo"

    @patch("cli_git.commands.info.ConfigManager")
    def test_info_not_initialized(self, mock_config_manager, runner):
        """Test info when configuration doesn't exist."""
        # Setup mock to raise exception when accessing config
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "",
                "default_org": "",
                "github_token": "",
                "slack_webhook_url": "",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = []

        # Run command
        result = runner.invoke(app, ["info"])

        # Verify
        assert result.exit_code == 0
        assert "Username: (not set)" in result.stdout
        assert "Run 'cli-git init' to configure" in result.stdout

    @patch("cli_git.commands.info.ConfigManager")
    @patch("cli_git.commands.info.check_gh_auth")
    def test_info_with_github_token(self, mock_check_auth, mock_config_manager, runner):
        """Test info display with GitHub token configured."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "default_org": "",
                "github_token": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
                "slack_webhook_url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            },
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }
        mock_manager.get_recent_mirrors.return_value = []

        # Run command
        result = runner.invoke(app, ["info"])

        # Verify
        assert result.exit_code == 0
        assert "GitHub token: ✅ Set (ghp_...wxyz)" in result.stdout
        assert (
            "Slack webhook: ✅ Set (https://hooks.slack.com/servic...XXXXXXXXXX)" in result.stdout
        )
