"""Tests for init command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app
from cli_git.commands.init import mask_webhook_url


class TestInitCommand:
    """Test cases for init command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.get_current_username")
    @patch("cli_git.commands.init.ConfigManager")
    def test_init_success(
        self, mock_config_manager, mock_get_username, mock_check_auth, runner, tmp_path
    ):
        """Test successful initialization."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Run command with input for prompts (webhook url, github token, prefix)
        result = runner.invoke(app, ["init"], input="\n\nmirror-\n")

        # Verify
        assert result.exit_code == 0
        assert "✅ Configuration initialized successfully!" in result.stdout
        assert "GitHub username: testuser" in result.stdout

        # Check config was updated
        mock_manager.update_config.assert_called_once()
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["github"]["username"] == "testuser"

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.typer.confirm")
    def test_init_no_gh_auth(self, mock_confirm, mock_check_auth, runner):
        """Test init when gh is not authenticated and user declines login."""
        mock_check_auth.return_value = False
        mock_confirm.return_value = False  # User declines to login

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "🔐 GitHub CLI is not authenticated" in result.stdout
        assert "Please run: gh auth login" in result.stdout

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.get_current_username")
    @patch("cli_git.commands.init.get_user_organizations")
    @patch("cli_git.commands.init.ConfigManager")
    @patch("cli_git.commands.init.typer.prompt")
    def test_init_with_default_org(
        self,
        mock_prompt,
        mock_config_manager,
        mock_get_orgs,
        mock_get_username,
        mock_check_auth,
        runner,
    ):
        """Test init with default organization."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_get_orgs.return_value = []  # No organizations
        mock_prompt.side_effect = ["", "", "mirror-"]  # Slack URL, GitHub token, prefix
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "", "default_org": ""},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Run command
        result = runner.invoke(app, ["init"])

        # Verify
        assert result.exit_code == 0

        # Check config was updated
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["github"]["username"] == "testuser"
        assert config_updates["preferences"]["default_prefix"] == "mirror-"

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.get_current_username")
    @patch("cli_git.commands.init.ConfigManager")
    def test_init_already_initialized(
        self, mock_config_manager, mock_get_username, mock_check_auth, runner
    ):
        """Test init when already initialized."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "existinguser", "default_org": "existingorg"},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Run command without --force
        result = runner.invoke(app, ["init"])

        # Should warn about existing config
        assert "⚠️  Configuration already exists" in result.stdout
        assert "Use --force to reinitialize" in result.stdout
        assert result.exit_code == 0

        # Config should not be updated
        mock_manager.update_config.assert_not_called()

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.get_current_username")
    @patch("cli_git.commands.init.ConfigManager")
    def test_init_force_reinitialize(
        self, mock_config_manager, mock_get_username, mock_check_auth, runner
    ):
        """Test forced reinitialization."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "newuser"
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "olduser", "default_org": "oldorg"},
            "preferences": {"default_schedule": "0 0 * * *"},
        }

        # Run command with --force
        result = runner.invoke(app, ["init", "--force"])

        # Should succeed and update
        assert result.exit_code == 0
        assert "✅ Configuration initialized successfully!" in result.stdout

        # Config should be updated
        mock_manager.update_config.assert_called_once()
        config_updates = mock_manager.update_config.call_args[0][0]
        assert config_updates["github"]["username"] == "newuser"

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.run_gh_auth_login")
    @patch("cli_git.commands.init.typer.confirm")
    def test_init_prompts_for_login(self, mock_confirm, mock_login, mock_check_auth, runner):
        """Test init prompts for GitHub login when not authenticated."""
        # Setup mocks
        mock_check_auth.return_value = False
        mock_confirm.return_value = True
        mock_login.return_value = True

        # Need to mock the subsequent auth check and username after login
        with patch("cli_git.commands.init.get_current_username") as mock_username:
            with patch("cli_git.commands.init.ConfigManager") as mock_config_manager:
                mock_username.return_value = "testuser"
                mock_manager = MagicMock()
                mock_config_manager.return_value = mock_manager
                mock_manager.get_config.return_value = {
                    "github": {"username": "", "default_org": ""},
                    "preferences": {"default_schedule": "0 0 * * *"},
                }

                result = runner.invoke(app, ["init"], input="\n\nmirror-\n")

        assert result.exit_code == 0
        assert "🔐 GitHub CLI is not authenticated" in result.stdout
        assert "📝 Starting GitHub authentication..." in result.stdout
        assert "✅ GitHub authentication successful!" in result.stdout

        # Verify login was called
        mock_login.assert_called_once()

    @patch("cli_git.commands.init.check_gh_auth")
    @patch("cli_git.commands.init.typer.confirm")
    def test_init_exits_when_login_declined(self, mock_confirm, mock_check_auth, runner):
        """Test init exits when user declines to login."""
        # Setup mocks
        mock_check_auth.return_value = False
        mock_confirm.return_value = False

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "🔐 GitHub CLI is not authenticated" in result.stdout
        assert "Please run: gh auth login" in result.stdout

    def test_mask_webhook_url(self):
        """Test masking Slack webhook URLs."""
        # Test with valid webhook URL
        url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        masked = mask_webhook_url(url)
        assert masked == "https://hooks.slack.com/services/T00.../B00.../XXX..."

        # Test with empty URL
        assert mask_webhook_url("") == ""

        # Test with non-Slack URL
        url = "https://example.com/webhook"
        masked = mask_webhook_url(url)
        assert masked == url  # Should return as-is

        # Test with incomplete Slack URL
        url = "https://hooks.slack.com/services/T00000000"
        masked = mask_webhook_url(url)
        assert masked == url  # Should return as-is
