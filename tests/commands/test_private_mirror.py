"""Tests for private-mirror command."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestPrivateMirrorCommand:
    """Test cases for private-mirror command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_private_mirror_success(
        self,
        mock_mirror_operation,
        mock_get_username,
        mock_check_auth,
        mock_config_manager,
        runner,
    ):
        """Test successful private mirror creation."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_mirror_operation.return_value = "https://github.com/testuser/repo-mirror"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_schedule": "0 0 * * *", "default_prefix": "mirror-"},
        }

        # Run command
        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        # Verify success
        assert result.exit_code == 0
        assert "✅ Success! Your private mirror is ready:" in result.stdout
        assert "https://github.com/testuser/repo-mirror" in result.stdout

        # Verify mirror operation was called correctly
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/repo",
            target_name="mirror-repo",  # prefix applied
            username="testuser",
            org=None,
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

        # Verify mirror was added to recent mirrors
        mock_manager.add_recent_mirror.assert_called_once()

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    def test_private_mirror_not_authenticated(self, mock_check_auth, runner):
        """Test private mirror when not authenticated."""
        mock_check_auth.return_value = False

        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        assert result.exit_code == 1
        assert "❌ GitHub CLI is not authenticated" in result.stdout

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    def test_private_mirror_not_initialized(self, mock_config_manager, mock_check_auth, runner):
        """Test private mirror when not initialized."""
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {"github": {"username": "", "default_org": ""}}

        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        assert result.exit_code == 1
        assert "❌ Configuration not initialized" in result.stdout
        assert "Run 'cli-git init' first" in result.stdout

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    def test_private_mirror_invalid_url(self, mock_config_manager, mock_check_auth, runner):
        """Test private mirror with invalid URL."""
        mock_check_auth.return_value = True
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        result = runner.invoke(app, ["private-mirror", "not-a-valid-url"])

        assert result.exit_code == 1
        assert "❌ Invalid GitHub repository URL" in result.stdout

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_private_mirror_with_custom_name(
        self, mock_mirror_operation, mock_config_manager, mock_get_username, mock_check_auth, runner
    ):
        """Test private mirror with custom repository name."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }
        mock_mirror_operation.return_value = "https://github.com/testuser/my-custom-mirror"

        runner.invoke(
            app, ["private-mirror", "https://github.com/owner/repo", "--repo", "my-custom-mirror"]
        )

        # Verify custom name was used
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/repo",
            target_name="my-custom-mirror",
            username="testuser",
            org=None,
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.private_mirror_operation")
    def test_private_mirror_with_organization(
        self, mock_mirror_operation, mock_config_manager, mock_get_username, mock_check_auth, runner
    ):
        """Test private mirror with organization."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "myorg", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }
        mock_mirror_operation.return_value = "https://github.com/myorg/repo-mirror"

        runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        # Verify org from config was used
        mock_mirror_operation.assert_called_once_with(
            upstream_url="https://github.com/owner/repo",
            target_name="mirror-repo",  # prefix applied
            username="testuser",
            org="myorg",
            schedule="0 0 * * *",
            no_sync=False,
            slack_webhook_url="",
            github_token="",
        )

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.generate_sync_workflow")
    def test_private_mirror_no_sync_option(
        self,
        mock_generate_workflow,
        mock_config_manager,
        mock_get_username,
        mock_check_auth,
        runner,
    ):
        """Test private mirror with --no-sync option."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        with patch("cli_git.commands.private_mirror.private_mirror_operation"):
            runner.invoke(app, ["private-mirror", "https://github.com/owner/repo", "--no-sync"])

            # Verify workflow generation was not called
            mock_generate_workflow.assert_not_called()

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.get_default_branch")
    @patch("cli_git.commands.private_mirror.run_git_command")
    @patch("cli_git.commands.private_mirror.create_private_repo")
    @patch("cli_git.commands.private_mirror.get_upstream_default_branch")
    @patch("cli_git.commands.private_mirror.add_repo_secret")
    @patch("cli_git.commands.private_mirror.generate_sync_workflow")
    @patch("cli_git.commands.private_mirror.clean_github_directory")
    @patch("os.chdir")
    @patch("tempfile.TemporaryDirectory")
    def test_private_mirror_with_master_branch(
        self,
        mock_temp_dir,
        mock_chdir,
        mock_clean_github,
        mock_generate_workflow,
        mock_add_secret,
        mock_get_upstream_default_branch,
        mock_create_repo,
        mock_run_git,
        mock_get_default_branch,
        mock_config_manager,
        mock_get_username,
        mock_check_auth,
        runner,
    ):
        """Test private mirror operation with master branch."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_get_default_branch.return_value = "master"
        mock_create_repo.return_value = "https://github.com/testuser/mirror-repo"
        mock_clean_github.return_value = True
        mock_generate_workflow.return_value = "workflow content"
        mock_get_upstream_default_branch.return_value = "master"

        # Mock temp directory
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"

        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        # Verify success
        assert result.exit_code == 0

        # Verify that git push was called with master branch
        push_calls = [
            call for call in mock_run_git.call_args_list if "push origin master" in str(call)
        ]
        assert (
            len(push_calls) > 0
        ), f"Expected 'push origin master' call, got: {mock_run_git.call_args_list}"

    @patch("cli_git.commands.private_mirror.check_gh_auth")
    @patch("cli_git.commands.private_mirror.get_current_username")
    @patch("cli_git.commands.private_mirror.ConfigManager")
    @patch("cli_git.commands.private_mirror.get_default_branch")
    @patch("cli_git.commands.private_mirror.run_git_command")
    @patch("cli_git.commands.private_mirror.create_private_repo")
    @patch("cli_git.commands.private_mirror.get_upstream_default_branch")
    @patch("cli_git.commands.private_mirror.add_repo_secret")
    @patch("cli_git.commands.private_mirror.generate_sync_workflow")
    @patch("cli_git.commands.private_mirror.clean_github_directory")
    @patch("os.chdir")
    @patch("tempfile.TemporaryDirectory")
    def test_private_mirror_fallback_push_strategy(
        self,
        mock_temp_dir,
        mock_chdir,
        mock_clean_github,
        mock_generate_workflow,
        mock_add_secret,
        mock_get_upstream_default_branch,
        mock_create_repo,
        mock_run_git,
        mock_get_default_branch,
        mock_config_manager,
        mock_get_username,
        mock_check_auth,
        runner,
    ):
        """Test private mirror fallback push strategy when get_default_branch fails."""
        # Setup mocks
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_create_repo.return_value = "https://github.com/testuser/mirror-repo"
        mock_clean_github.return_value = True
        mock_generate_workflow.return_value = "workflow content"
        mock_get_upstream_default_branch.return_value = "main"

        # Mock temp directory
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"

        # Mock get_default_branch to fail, then git commands
        import subprocess

        mock_get_default_branch.side_effect = subprocess.CalledProcessError(1, "git")

        # Mock git commands - first push main succeeds
        def git_side_effect(cmd, cwd=None):
            if "push origin main" in cmd:
                return "pushed to main"
            return "git output"

        mock_run_git.side_effect = git_side_effect

        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "default_org": "", "slack_webhook_url": ""},
            "preferences": {"default_prefix": "mirror-"},
        }

        result = runner.invoke(app, ["private-mirror", "https://github.com/owner/repo"])

        # Verify success
        assert result.exit_code == 0

        # Verify fallback push to main was attempted
        push_calls = [
            call for call in mock_run_git.call_args_list if "push origin main" in str(call)
        ]
        assert len(push_calls) > 0, "Expected fallback 'push origin main' call"
