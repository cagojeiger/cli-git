"""Tests for init command with validation."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestInitValidation:
    """Test validation in init command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_auth_and_username(self):
        """Mock authentication and username."""
        with patch("cli_git.commands.init.check_gh_auth") as mock_auth:
            with patch("cli_git.commands.init.get_current_username") as mock_username:
                mock_auth.return_value = True
                mock_username.return_value = "testuser"
                yield mock_auth, mock_username

    @patch("cli_git.commands.init.ConfigManager")
    @patch("cli_git.commands.init.get_user_organizations")
    @patch("cli_git.commands.init.typer.prompt")
    def test_invalid_slack_webhook_validation(
        self, mock_prompt, mock_get_orgs, mock_config_manager, runner, mock_auth_and_username
    ):
        """Test validation of invalid Slack webhook URL."""
        # Setup mocks
        mock_get_orgs.return_value = []
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Simulate user input: invalid webhook, then empty (skip), github token, then valid prefix
        mock_prompt.side_effect = [
            "https://invalid-webhook.com",  # Invalid webhook
            "",  # Skip webhook on retry
            "",  # Skip GitHub token
            "mirror-",  # Valid prefix
        ]

        result = runner.invoke(app, ["init"])

        # Should show validation error but still succeed
        assert result.exit_code == 0
        assert "❌ Invalid Slack webhook URL" in result.stdout
        assert "Press Enter to skip" in result.stdout
        assert "✅ Configuration initialized successfully!" in result.stdout

        # Verify configuration was saved with empty webhook
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["github"]["slack_webhook_url"] == ""

    @patch("cli_git.commands.init.ConfigManager")
    @patch("cli_git.commands.init.get_user_organizations")
    @patch("cli_git.commands.init.typer.prompt")
    def test_valid_slack_webhook_accepted(
        self, mock_prompt, mock_get_orgs, mock_config_manager, runner, mock_auth_and_username
    ):
        """Test that valid Slack webhook URL is accepted."""
        # Setup mocks
        mock_get_orgs.return_value = []
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        valid_webhook = (
            "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        )
        mock_prompt.side_effect = [
            valid_webhook,  # Valid webhook
            "",  # Skip GitHub token
            "mirror-",  # Valid prefix
        ]

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "✅ Configuration initialized successfully!" in result.stdout
        assert (
            "Slack webhook: https://hooks.slack.com/services/T00.../B00.../XXX..." in result.stdout
        )

        # Verify configuration was saved with the webhook
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["github"]["slack_webhook_url"] == valid_webhook

    @patch("cli_git.commands.init.ConfigManager")
    @patch("cli_git.commands.init.get_user_organizations")
    @patch("cli_git.commands.init.typer.prompt")
    def test_invalid_prefix_validation(
        self, mock_prompt, mock_get_orgs, mock_config_manager, runner, mock_auth_and_username
    ):
        """Test validation of invalid prefix."""
        # Setup mocks
        mock_get_orgs.return_value = []
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Simulate user input: empty webhook, invalid prefix, then valid prefix
        mock_prompt.side_effect = [
            "",  # Skip webhook
            "",  # Skip GitHub token
            "my prefix",  # Invalid prefix (contains space)
            "my-prefix-",  # Valid prefix
        ]

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "❌ Prefix contains invalid characters" in result.stdout
        assert "✅ Configuration initialized successfully!" in result.stdout

        # Verify configuration was saved with valid prefix
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["preferences"]["default_prefix"] == "my-prefix-"

    @patch("cli_git.commands.init.ConfigManager")
    @patch("cli_git.commands.init.get_user_organizations")
    @patch("cli_git.commands.init.typer.prompt")
    def test_long_prefix_validation(
        self, mock_prompt, mock_get_orgs, mock_config_manager, runner, mock_auth_and_username
    ):
        """Test validation of too long prefix."""
        # Setup mocks
        mock_get_orgs.return_value = []
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Simulate user input
        long_prefix = "a" * 51  # Too long
        mock_prompt.side_effect = [
            "",  # Skip webhook
            "",  # Skip GitHub token
            long_prefix,  # Too long prefix
            "short-",  # Valid prefix
        ]

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "❌ Prefix too long" in result.stdout
        assert "✅ Configuration initialized successfully!" in result.stdout

        # Verify configuration was saved with valid prefix
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["preferences"]["default_prefix"] == "short-"

    @patch("cli_git.commands.init.ConfigManager")
    @patch("cli_git.commands.init.get_user_organizations")
    @patch("cli_git.commands.init.typer.prompt")
    @patch("cli_git.commands.init.typer.confirm")
    def test_organization_selection_with_validation(
        self,
        mock_confirm,
        mock_prompt,
        mock_get_orgs,
        mock_config_manager,
        runner,
        mock_auth_and_username,
    ):
        """Test organization selection process."""
        # Setup mocks
        mock_get_orgs.return_value = ["org1", "org2", "org3"]
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # User selects organization 2
        mock_prompt.side_effect = [
            "2",  # Select org2
            "",  # Skip webhook
            "",  # Skip GitHub token
            "mirror-",  # Default prefix
        ]
        mock_confirm.return_value = True  # Confirm selection

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "📋 Your GitHub organizations:" in result.stdout
        assert "1. org1" in result.stdout
        assert "2. org2" in result.stdout
        assert "3. org3" in result.stdout
        assert "✅ Configuration initialized successfully!" in result.stdout

        # Verify configuration was saved with selected org
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["github"]["default_org"] == "org2"
