"""Tests for update-mirrors command."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli_git.cli import app


class TestUpdateMirrorsCommand:
    """Test cases for update-mirrors command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    def test_update_mirrors_not_authenticated(self, mock_check_auth, runner):
        """Test update-mirrors when not authenticated."""
        mock_check_auth.return_value = False

        result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 1
        assert "❌ GitHub CLI is not authenticated" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    def test_update_mirrors_no_token_warning(
        self, mock_get_username, mock_config_manager, mock_check_auth, runner
    ):
        """Test warning when no GitHub token is configured."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "github_token": ""},
            "preferences": {},
        }
        mock_manager.get_recent_mirrors.return_value = []

        result = runner.invoke(app, ["update-mirrors"])

        assert "⚠️  No GitHub token found in configuration" in result.stdout
        assert "Run 'cli-git init' to add a GitHub token" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    def test_update_mirrors_no_mirrors_in_cache(
        self, mock_get_username, mock_config_manager, mock_check_auth, runner
    ):
        """Test when no mirrors are found in cache."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "github_token": "test_token"},
            "preferences": {},
        }
        mock_manager.get_recent_mirrors.return_value = []

        result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 0
        assert "No mirrors found in cache" in result.stdout
        assert "Use --scan to search GitHub for mirrors" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_via_api")
    @patch("subprocess.run")
    @patch("cli_git.commands.update_mirrors.typer.prompt")
    def test_update_specific_mirror(
        self,
        mock_prompt,
        mock_subprocess,
        mock_update_workflow,
        mock_add_secret,
        mock_get_branch,
        mock_get_username,
        mock_config_manager,
        mock_check_auth,
        runner,
    ):
        """Test updating a specific mirror repository."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_get_branch.return_value = "main"
        mock_prompt.return_value = "https://github.com/upstream/repo"  # Provide upstream URL

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "github_token": "test_token",
                "slack_webhook_url": "https://hooks.slack.com/test",
            },
            "preferences": {},
        }

        # Mock subprocess for workflow check (returns 0 = workflow exists)
        mock_subprocess.return_value.returncode = 0

        result = runner.invoke(app, ["update-mirrors", "--repo", "testuser/mirror-repo"])

        # Verify the command succeeded
        assert result.exit_code == 0
        assert "🔄 Updating testuser/mirror-repo..." in result.stdout

        # Verify secrets were updated
        assert (
            mock_add_secret.call_count >= 3
        )  # At least UPSTREAM_URL, UPSTREAM_DEFAULT_BRANCH, GH_TOKEN

        # Verify workflow was updated
        mock_update_workflow.assert_called_once()

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_via_api")
    def test_update_all_mirrors_from_cache(
        self,
        mock_update_workflow,
        mock_add_secret,
        mock_get_branch,
        mock_get_username,
        mock_config_manager,
        mock_check_auth,
        runner,
    ):
        """Test updating all mirrors from cache."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_get_branch.return_value = "main"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "github_token": "test_token"},
            "preferences": {},
        }
        mock_manager.get_recent_mirrors.return_value = [
            {
                "upstream": "https://github.com/owner1/repo1",
                "mirror": "https://github.com/testuser/mirror-repo1",
            },
            {
                "upstream": "https://github.com/owner2/repo2",
                "mirror": "https://github.com/testuser/mirror-repo2",
            },
        ]

        result = runner.invoke(app, ["update-mirrors", "--all"])

        assert result.exit_code == 0
        assert "📊 Update complete: 2/2 mirrors updated successfully" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.scan_for_mirrors")
    def test_scan_for_mirrors(
        self, mock_scan, mock_get_username, mock_config_manager, mock_check_auth, runner
    ):
        """Test scanning GitHub for mirrors."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "github_token": "test_token",
                "default_org": "testorg",
            },
            "preferences": {},
        }

        # Mock scan results
        mock_scan.return_value = []

        result = runner.invoke(app, ["update-mirrors", "--scan"])

        assert result.exit_code == 0
        assert "No mirror repositories found" in result.stdout

        # Verify scan was called with username and org
        mock_scan.assert_called_once_with("testuser", "testorg")

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_via_api")
    @patch("cli_git.commands.update_mirrors.typer.prompt")
    def test_interactive_mirror_selection(
        self,
        mock_prompt,
        mock_update_workflow,
        mock_add_secret,
        mock_get_branch,
        mock_get_username,
        mock_config_manager,
        mock_check_auth,
        runner,
    ):
        """Test interactive mirror selection."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_get_branch.return_value = "main"
        mock_prompt.return_value = "1,2"  # Select first two mirrors

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "github_token": "test_token"},
            "preferences": {},
        }
        mock_manager.get_recent_mirrors.return_value = [
            {
                "upstream": "https://github.com/owner1/repo1",
                "mirror": "https://github.com/testuser/mirror1",
            },
            {
                "upstream": "https://github.com/owner2/repo2",
                "mirror": "https://github.com/testuser/mirror2",
            },
            {
                "upstream": "https://github.com/owner3/repo3",
                "mirror": "https://github.com/testuser/mirror3",
            },
        ]

        result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 0
        assert "📋 Available mirrors:" in result.stdout
        assert "📊 Update complete: 2/2 mirrors updated successfully" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_via_api")
    def test_update_mirror_with_error(
        self,
        mock_update_workflow,
        mock_add_secret,
        mock_get_branch,
        mock_get_username,
        mock_config_manager,
        mock_check_auth,
        runner,
    ):
        """Test handling errors during mirror update."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"
        mock_get_branch.side_effect = Exception("API error")

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"username": "testuser", "github_token": "test_token"},
            "preferences": {},
        }
        mock_manager.get_recent_mirrors.return_value = [
            {
                "upstream": "https://github.com/owner/repo",
                "mirror": "https://github.com/testuser/mirror",
            }
        ]

        result = runner.invoke(app, ["update-mirrors", "--all"])

        assert result.exit_code == 0
        assert "❌ Unexpected error updating" in result.stdout
        assert "💡 For failed updates, you may need to:" in result.stdout

    def test_update_workflow_via_api(self):
        """Test the update_workflow_via_api function."""
        from cli_git.commands.update_mirrors import update_workflow_via_api

        with patch("subprocess.run") as mock_run:
            # Mock getting current file (exists)
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({"sha": "abc123"})

            # Test updating existing file
            update_workflow_via_api("owner/repo", "workflow content")

            # Verify API was called with PUT and SHA
            calls = mock_run.call_args_list
            assert len(calls) == 2
            assert "PUT" in str(calls[1])
            assert "sha=abc123" in str(calls[1])

    def test_scan_for_mirrors_function(self):
        """Test the scan_for_mirrors function."""
        from cli_git.commands.update_mirrors import scan_for_mirrors

        with patch("subprocess.run") as mock_run:
            # Mock repo list
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(
                [
                    {
                        "nameWithOwner": "testuser/mirror-repo",
                        "url": "https://github.com/testuser/mirror-repo",
                    },
                    {
                        "nameWithOwner": "testuser/regular-repo",
                        "url": "https://github.com/testuser/regular-repo",
                    },
                ]
            )

            # First call returns repo list, second checks for workflow (success), third checks for workflow (fail)
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        [
                            {
                                "nameWithOwner": "testuser/mirror-repo",
                                "url": "https://github.com/testuser/mirror-repo",
                            },
                            {
                                "nameWithOwner": "testuser/regular-repo",
                                "url": "https://github.com/testuser/regular-repo",
                            },
                        ]
                    ),
                ),
                MagicMock(returncode=0),  # mirror-repo has workflow
                MagicMock(returncode=1),  # regular-repo doesn't have workflow
            ]

            mirrors = scan_for_mirrors("testuser")

            assert len(mirrors) == 1
            assert mirrors[0]["name"] == "testuser/mirror-repo"
