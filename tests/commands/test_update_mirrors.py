"""Tests for update-mirrors command."""

import json
from unittest.mock import MagicMock, mock_open, patch

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
        mock_manager.get_scanned_mirrors.return_value = []  # Mock empty scan cache

        result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 0
        # When cached mirrors is empty and scanned cache is also empty, it shows no mirrors found
        assert "No mirror repositories found" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_file")
    @patch("cli_git.commands.update_mirrors.subprocess.run")
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
        if result.exit_code != 0:
            print(result.stdout)
            print(result.stderr)
        assert result.exit_code == 0
        assert "🔄 Updating testuser/mirror-repo..." in result.stdout

        # Verify secrets were updated (only GH_TOKEN and SLACK_WEBHOOK_URL since no upstream URL)
        assert mock_add_secret.call_count == 2

        # Verify workflow was updated
        mock_update_workflow.assert_called_once()

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_file")
    @patch("cli_git.commands.update_mirrors.subprocess.run")
    def test_update_specific_mirror_without_upstream(
        self,
        mock_subprocess,
        mock_update_workflow,
        mock_add_secret,
        mock_get_username,
        mock_config_manager,
        mock_check_auth,
        runner,
    ):
        """Test updating a specific mirror repository without upstream URL in cache."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

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
        assert "Existing mirror detected" in result.stdout
        assert "Preserving current upstream configuration" in result.stdout

        # Verify only GH_TOKEN and SLACK_WEBHOOK_URL were updated
        assert mock_add_secret.call_count == 2

        # Verify workflow was updated
        mock_update_workflow.assert_called_once()

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_file")
    @patch("cli_git.commands.update_mirrors.subprocess.run")
    def test_update_all_mirrors_from_cache(
        self,
        mock_subprocess,
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
        # Return None for scanned mirrors so it falls back to recent mirrors
        mock_manager.get_scanned_mirrors.return_value = None
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

        # Mock subprocess for workflow check (returns 0 = workflow exists)
        mock_subprocess.return_value.returncode = 0

        # Simulate selecting all mirrors in interactive mode
        with patch("cli_git.commands.update_mirrors.typer.prompt", return_value="1,2"):
            result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 0
        # First shows the interactive menu, then update results
        assert "📋 Found mirror repositories:" in result.stdout
        assert "📊 Update complete: 2/2 mirrors updated successfully" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.scan_for_mirrors")
    def test_scan_for_mirrors_no_results(
        self, mock_scan, mock_get_username, mock_config_manager, mock_check_auth, runner
    ):
        """Test scanning GitHub for mirrors when none found."""
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

        # Mock scan results - no mirrors found
        mock_scan.return_value = []
        mock_manager.get_scanned_mirrors.return_value = None  # No cache

        # Test without verbose - should exit with no output for empty results
        result = runner.invoke(app, ["update-mirrors", "--scan"])
        assert result.exit_code == 0
        assert result.stdout.strip() == ""  # No output for empty results

        # Verify scan was called
        mock_scan.assert_called_with("testuser", "testorg")
        # Verify cache was saved
        mock_manager.save_scanned_mirrors.assert_called_with([])

        # Reset mocks for second invocation
        mock_scan.reset_mock()
        mock_manager.save_scanned_mirrors.reset_mock()

        # Test with verbose
        result = runner.invoke(app, ["update-mirrors", "--scan", "--verbose"])
        assert result.exit_code == 0
        assert "Scanning GitHub for mirror repositories" in result.stdout
        # Since scan returns empty list, it should show "No mirror repositories found"
        assert "No mirror repositories found" in result.stdout
        assert "Make sure you have mirror repositories" in result.stdout

        # Verify scan was called again
        mock_scan.assert_called_once_with("testuser", "testorg")
        # Verify cache was saved again
        mock_manager.save_scanned_mirrors.assert_called_once_with([])

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.scan_for_mirrors")
    def test_scan_for_mirrors_with_results(
        self, mock_scan, mock_get_username, mock_config_manager, mock_check_auth, runner
    ):
        """Test scanning GitHub for mirrors when some are found."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "github_token": "test_token",
                "default_org": "",
            },
            "preferences": {},
        }

        # Mock scan results - found some mirrors
        mirrors = [
            {
                "name": "testuser/mirror-project1",
                "mirror": "https://github.com/testuser/mirror-project1",
                "upstream": "https://github.com/upstream/project1",
                "description": "Mirror of project1",
                "is_private": False,
                "updated_at": "2025-01-01T12:00:00Z",
            },
            {
                "name": "testuser/mirror-project2",
                "mirror": "https://github.com/testuser/mirror-project2",
                "upstream": "",
                "description": "",
                "is_private": True,
                "updated_at": "2025-01-02T12:00:00Z",
            },
        ]
        mock_scan.return_value = mirrors
        mock_manager.get_scanned_mirrors.return_value = None  # No cache

        # Test without verbose - should output just repo names
        result = runner.invoke(app, ["update-mirrors", "--scan"])
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "testuser/mirror-project1"
        assert lines[1] == "testuser/mirror-project2"

        # Reset mocks
        mock_scan.reset_mock()
        mock_manager.save_scanned_mirrors.reset_mock()

        # Test with verbose
        result = runner.invoke(app, ["update-mirrors", "--scan", "--verbose"])
        assert result.exit_code == 0
        assert "Found 2 mirror repositories" in result.stdout
        assert "testuser/mirror-project1" in result.stdout
        assert "testuser/mirror-project2" in result.stdout
        assert "Mirror of project1" in result.stdout
        assert "🔒" in result.stdout  # Private repo indicator
        assert "🌐" in result.stdout  # Public repo indicator
        assert "To update these mirrors:" in result.stdout
        assert "cli-git update-mirrors --scan | xargs" in result.stdout
        assert "cli-git update-mirrors --repo" in result.stdout

        # Verify scan was called
        mock_scan.assert_called_once_with("testuser", "")
        # Verify mirrors were saved to cache
        mock_manager.save_scanned_mirrors.assert_called_once_with(mirrors)

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.scan_for_mirrors")
    def test_scan_pipe_friendly_output(
        self, mock_scan, mock_get_username, mock_config_manager, mock_check_auth, runner
    ):
        """Test scanning GitHub for mirrors with pipe-friendly output."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        # Mock ConfigManager
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {
                "username": "testuser",
                "github_token": "test_token",
                "default_org": "",
            },
            "preferences": {},
        }

        # Mock scan results - found some mirrors
        mirrors = [
            {
                "name": "testuser/mirror-project1",
                "mirror": "https://github.com/testuser/mirror-project1",
                "upstream": "https://github.com/upstream/project1",
                "description": "Mirror of project1",
                "is_private": False,
                "updated_at": "2025-01-01T12:00:00Z",
            },
            {
                "name": "testuser/mirror-project2",
                "mirror": "https://github.com/testuser/mirror-project2",
                "upstream": "",
                "description": "",
                "is_private": True,
                "updated_at": "2025-01-02T12:00:00Z",
            },
        ]
        mock_scan.return_value = mirrors
        mock_manager.get_scanned_mirrors.return_value = None  # No cache

        # Test without --verbose (pipe-friendly)
        result = runner.invoke(app, ["update-mirrors", "--scan"])

        assert result.exit_code == 0
        # Should output just the repo names, one per line
        lines = result.stdout.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "testuser/mirror-project1"
        assert lines[1] == "testuser/mirror-project2"
        # Should not contain descriptive text
        assert "Found" not in result.stdout
        assert "Scanning" not in result.stdout

        # Test with --verbose
        result = runner.invoke(app, ["update-mirrors", "--scan", "--verbose"])

        assert result.exit_code == 0
        # Should contain descriptive output
        assert "Found 2 mirror repositories" in result.stdout
        assert "testuser/mirror-project1" in result.stdout
        assert "Mirror of project1" in result.stdout
        assert "To update these mirrors:" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_file")
    @patch("cli_git.commands.update_mirrors.subprocess.run")
    @patch("cli_git.commands.update_mirrors.typer.prompt")
    def test_interactive_mirror_selection(
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
        mock_manager.get_scanned_mirrors.return_value = None  # No scanned cache
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

        # Mock subprocess for workflow check (returns 0 = workflow exists)
        mock_subprocess.return_value.returncode = 0

        result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 0
        assert "📋 Found mirror repositories:" in result.stdout
        assert "📊 Update complete: 2/2 mirrors updated successfully" in result.stdout

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.get_upstream_default_branch")
    @patch("cli_git.commands.update_mirrors.add_repo_secret")
    @patch("cli_git.commands.update_mirrors.update_workflow_file")
    @patch("cli_git.commands.update_mirrors.subprocess.run")
    def test_update_mirror_with_error(
        self,
        mock_subprocess,
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
        mock_manager.get_scanned_mirrors.return_value = None  # No scanned cache
        mock_manager.get_recent_mirrors.return_value = [
            {
                "upstream": "https://github.com/owner/repo",
                "mirror": "https://github.com/testuser/mirror",
            }
        ]

        # Mock subprocess for workflow check (returns 0 = workflow exists)
        mock_subprocess.return_value.returncode = 0

        # Simulate selecting all mirrors in interactive mode
        with patch("cli_git.commands.update_mirrors.typer.prompt", return_value="1"):
            result = runner.invoke(app, ["update-mirrors"])

        assert result.exit_code == 0
        # First shows the interactive menu, then error
        assert "📋 Found mirror repositories:" in result.stdout
        assert "❌ Unexpected error updating" in result.stdout
        assert "💡 For failed updates, you may need to:" in result.stdout

    def test_update_workflow_file(self):
        """Test the update_workflow_file function."""
        from cli_git.commands.modules.workflow_updater import update_workflow_file

        with patch("subprocess.run") as mock_run:
            # Mock getting current file (exists)
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps({"sha": "abc123"})

            with patch("tempfile.TemporaryDirectory") as mock_tempdir:
                with patch("os.chdir"):
                    with patch("os.makedirs"):
                        with patch("builtins.open", mock_open()) as mock_file:
                            # Mock successful clone and push
                            mock_run.return_value.returncode = 0
                            mock_tempdir.return_value.__enter__.return_value = "/tmp/test"

                            # Test updating workflow
                            update_workflow_file("owner/repo", "workflow content")

                            # Verify file was written
                            mock_file.assert_called_once()
                            mock_file().write.assert_called_once_with("workflow content")

    def test_scan_for_mirrors_function(self):
        """Test the scan_for_mirrors function."""
        from cli_git.commands.modules.scan import scan_for_mirrors

        with patch("subprocess.run") as mock_run:
            with patch("cli_git.commands.modules.scan.typer.echo"):  # Mock echo to suppress output
                # First call returns repo list with extended fields
                repo_list = [
                    {
                        "nameWithOwner": "testuser/mirror-repo",
                        "url": "https://github.com/testuser/mirror-repo",
                        "description": "A mirror repository",
                        "isPrivate": False,
                        "updatedAt": "2025-01-01T12:00:00Z",
                    },
                    {
                        "nameWithOwner": "testuser/regular-repo",
                        "url": "https://github.com/testuser/regular-repo",
                        "description": "A regular repository",
                        "isPrivate": True,
                        "updatedAt": "2025-01-02T12:00:00Z",
                    },
                ]

                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout=json.dumps(repo_list)),  # repo list
                    MagicMock(returncode=0),  # mirror-repo has workflow
                    MagicMock(returncode=0, stdout=""),  # workflow content (empty for test)
                    MagicMock(returncode=1),  # regular-repo doesn't have workflow
                ]

                mirrors = scan_for_mirrors("testuser")

                assert len(mirrors) == 1
                assert mirrors[0]["name"] == "testuser/mirror-repo"
                assert mirrors[0]["description"] == "A mirror repository"
                assert mirrors[0]["is_private"] is False
                assert mirrors[0]["updated_at"] == "2025-01-01T12:00:00Z"

    def test_scan_for_mirrors_function_with_org(self):
        """Test the scan_for_mirrors function with organization."""
        from cli_git.commands.modules.scan import scan_for_mirrors

        with patch("subprocess.run") as mock_run:
            with patch("cli_git.commands.modules.scan.typer.echo"):  # Mock echo
                # Mock for user repos
                user_repos = [
                    {
                        "nameWithOwner": "testuser/mirror-personal",
                        "url": "https://github.com/testuser/mirror-personal",
                        "description": "Personal mirror",
                        "isPrivate": False,
                        "updatedAt": "2025-01-01T12:00:00Z",
                    },
                ]

                # Mock for org repos
                org_repos = [
                    {
                        "nameWithOwner": "testorg/mirror-shared",
                        "url": "https://github.com/testorg/mirror-shared",
                        "description": "Shared mirror",
                        "isPrivate": True,
                        "updatedAt": "2025-01-02T12:00:00Z",
                    },
                ]

                mock_run.side_effect = [
                    # User repos
                    MagicMock(returncode=0, stdout=json.dumps(user_repos)),
                    MagicMock(returncode=0),  # mirror-personal has workflow
                    MagicMock(returncode=0, stdout=""),  # workflow content
                    # Org repos
                    MagicMock(returncode=0, stdout=json.dumps(org_repos)),
                    MagicMock(returncode=0),  # mirror-shared has workflow
                    MagicMock(returncode=0, stdout=""),  # workflow content
                ]

                mirrors = scan_for_mirrors("testuser", "testorg")

                assert len(mirrors) == 2
                assert any(m["name"] == "testuser/mirror-personal" for m in mirrors)
                assert any(m["name"] == "testorg/mirror-shared" for m in mirrors)

    def test_update_workflow_file_no_changes(self):
        """Test update_workflow_file when content hasn't changed."""
        from cli_git.commands.modules.workflow_updater import update_workflow_file

        with patch("subprocess.run") as mock_run:
            with patch("tempfile.TemporaryDirectory") as mock_tempdir:
                with patch("os.chdir"):
                    with patch("os.makedirs"):
                        with patch("os.path.exists", return_value=True):
                            with patch(
                                "builtins.open", mock_open(read_data="existing content")
                            ) as mock_file:
                                # Mock successful clone
                                mock_run.return_value.returncode = 0
                                mock_tempdir.return_value.__enter__.return_value = "/tmp/test"

                                # Test updating workflow with same content
                                result = update_workflow_file("owner/repo", "existing content")

                                # Should return False (no changes)
                                assert result is False

                                # Verify file was read to compare
                                mock_file.assert_called()

                                # Verify no git commands were run after clone
                                # Only clone command should have been called
                                assert mock_run.call_count == 1

    def test_update_workflow_file_with_changes(self):
        """Test update_workflow_file when content has changed."""
        from cli_git.commands.modules.workflow_updater import update_workflow_file

        with patch("subprocess.run") as mock_run:
            with patch("tempfile.TemporaryDirectory") as mock_tempdir:
                with patch("os.chdir"):
                    with patch("os.makedirs"):
                        with patch("os.path.exists", return_value=True):
                            with patch(
                                "builtins.open", mock_open(read_data="old content")
                            ) as mock_file:
                                # Mock all git commands to succeed
                                mock_run.return_value.returncode = 0
                                mock_tempdir.return_value.__enter__.return_value = "/tmp/test"

                                # Test updating workflow with new content
                                result = update_workflow_file("owner/repo", "new content")

                                # Should return True (changes made)
                                assert result is True

                                # Verify git commands were called
                                # Should have: clone, add, commit, push
                                assert mock_run.call_count >= 4

                                # Verify file was written
                                handle = mock_file()
                                handle.write.assert_called_with("new content")

    def test_update_workflow_file_clone_failure(self):
        """Test update_workflow_file when clone fails."""
        from cli_git.commands.modules.workflow_updater import update_workflow_file
        from cli_git.utils.gh import GitHubError

        with patch("subprocess.run") as mock_run:
            with patch("tempfile.TemporaryDirectory") as mock_tempdir:
                # Mock clone failure
                mock_run.side_effect = [
                    MagicMock(returncode=1, stderr="Clone failed"),  # First clone attempt
                    MagicMock(returncode=1, stderr="Clone failed"),  # Second clone attempt with gh
                ]
                mock_tempdir.return_value.__enter__.return_value = "/tmp/test"

                # Test updating workflow
                with pytest.raises(GitHubError) as exc_info:
                    update_workflow_file("owner/repo", "new content")

                assert "Failed to clone repository" in str(exc_info.value)

    def test_get_repo_secret_value(self):
        """Test get_repo_secret_value function."""
        from cli_git.commands.modules.workflow_updater import get_repo_secret_value

        with patch("subprocess.run") as mock_run:
            # Test non-UPSTREAM_URL secret
            result = get_repo_secret_value("owner/repo", "GH_TOKEN")
            assert result is None

            # Test UPSTREAM_URL with workflow content
            workflow_content = """
name: Mirror Sync
on:
  schedule:
    - cron: '0 0 * * *'
env:
  UPSTREAM_URL: ${{ secrets.UPSTREAM_URL }}  # UPSTREAM_URL: https://github.com/upstream/repo
"""
            import base64

            encoded_content = base64.b64encode(workflow_content.encode()).decode()

            mock_run.return_value = MagicMock(returncode=0, stdout=encoded_content + "\n")

            result = get_repo_secret_value("owner/repo", "UPSTREAM_URL")
            assert result == "https://github.com/upstream/repo"

            # Test UPSTREAM_URL when secret is used but no comment
            workflow_content2 = """
name: Mirror Sync
env:
  UPSTREAM_URL: ${{ secrets.UPSTREAM_URL }}
"""
            encoded_content2 = base64.b64encode(workflow_content2.encode()).decode()
            mock_run.return_value.stdout = encoded_content2 + "\n"

            result = get_repo_secret_value("owner/repo", "UPSTREAM_URL")
            assert result == ""  # Empty string indicates it's a mirror

            # Test when API call fails
            mock_run.side_effect = Exception("API error")
            result = get_repo_secret_value("owner/repo", "UPSTREAM_URL")
            assert result is None
