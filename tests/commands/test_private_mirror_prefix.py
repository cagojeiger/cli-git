"""Tests for prefix feature in private-mirror command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestPrefixFeature:
    """Test cases for prefix functionality."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_default_prefix_from_config(
        self,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test using default prefix from config."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/custom-react"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "custom-"},
        }

        # Run command without prefix option
        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/react"])

        # Verify prefix was applied
        assert result.exit_code == 0
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/react",
            target_name="custom-react",  # prefix + repo name
            username="testuser",
            org=None,
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_custom_prefix_option(
        self,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test using custom prefix via option."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/fork-react"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        # Run command with custom prefix
        result = runner.invoke(
            app, ["private-mirror", "https://github.com/owner/react", "--prefix", "fork-"]
        )

        # Verify custom prefix was used
        assert result.exit_code == 0
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/react",
            target_name="fork-react",  # custom prefix + repo name
            username="testuser",
            org=None,
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_no_prefix_option(
        self,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test using no prefix."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/react"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        # Run command with empty prefix
        result = runner.invoke(
            app, ["private-mirror", "https://github.com/owner/react", "--prefix", ""]
        )

        # Verify no prefix was applied
        assert result.exit_code == 0
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/react",
            target_name="react",  # no prefix, just repo name
            username="testuser",
            org=None,
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_custom_repo_name_overrides_prefix(
        self,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test that custom repo name overrides prefix."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/my-custom-name"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        # Run command with custom repo name and prefix
        result = runner.invoke(
            app,
            [
                "private-mirror",
                "https://github.com/owner/react",
                "--repo",
                "my-custom-name",
                "--prefix",
                "ignored-",
            ],
        )

        # Verify custom repo name was used (prefix ignored)
        assert result.exit_code == 0
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/react",
            target_name="my-custom-name",  # custom name, prefix ignored
            username="testuser",
            org=None,
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )
