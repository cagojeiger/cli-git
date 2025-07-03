"""Tests for update validation module."""

from unittest.mock import Mock, patch

import pytest
import typer

from cli_git.commands.update.update_validation import (
    check_update_prerequisites,
    display_scan_results,
    find_mirrors_to_update,
    handle_scan_option,
)
from cli_git.utils.gh import GitHubError


class TestCheckUpdatePrerequisites:
    """Tests for check_update_prerequisites function."""

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    def test_check_prerequisites_success(self, mock_config_cls, mock_get_username, mock_check_auth):
        """Test successful prerequisite check."""
        # Mock the functions
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        mock_config_manager = Mock()
        mock_config = {"github": {"github_token": "test_token"}}
        mock_config_manager.get_config.return_value = mock_config
        mock_config_cls.return_value = mock_config_manager

        result = check_update_prerequisites()

        assert result == (mock_config_manager, mock_config, "testuser")
        mock_check_auth.assert_called_once()
        mock_get_username.assert_called_once()

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    def test_check_prerequisites_no_auth(self, mock_check_auth):
        """Test when GitHub auth is not available."""
        mock_check_auth.return_value = False

        with pytest.raises(typer.Exit) as exc_info:
            check_update_prerequisites()

        assert exc_info.value.exit_code == 1

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    def test_check_prerequisites_no_token(
        self, mock_config_cls, mock_get_username, mock_check_auth
    ):
        """Test when no GitHub token is configured."""
        mock_check_auth.return_value = True
        mock_get_username.return_value = "testuser"

        mock_config_manager = Mock()
        mock_config = {"github": {}}  # No github_token
        mock_config_manager.get_config.return_value = mock_config
        mock_config_cls.return_value = mock_config_manager

        # Should not raise, just warn
        result = check_update_prerequisites()

        assert result == (mock_config_manager, mock_config, "testuser")

    @patch("cli_git.commands.update_mirrors.check_gh_auth")
    @patch("cli_git.commands.update_mirrors.get_current_username")
    @patch("cli_git.commands.update_mirrors.ConfigManager")
    def test_check_prerequisites_github_error(
        self, mock_config_cls, mock_get_username, mock_check_auth
    ):
        """Test when GitHub API returns error."""
        mock_check_auth.return_value = True
        mock_get_username.side_effect = GitHubError("API error")

        mock_config_manager = Mock()
        mock_config = {"github": {"github_token": "test_token"}}
        mock_config_manager.get_config.return_value = mock_config
        mock_config_cls.return_value = mock_config_manager

        with pytest.raises(typer.Exit) as exc_info:
            check_update_prerequisites()

        assert exc_info.value.exit_code == 1


class TestHandleScanOption:
    """Tests for handle_scan_option function."""

    @patch("cli_git.commands.modules.scan.scan_for_mirrors")
    @patch("cli_git.commands.update.update_validation.display_scan_results")
    def test_handle_scan_with_cache_verbose(self, mock_display, mock_scan):
        """Test scan option with cached results in verbose mode."""
        mock_config_manager = Mock()
        mock_config = {"github": {"default_org": "test-org"}}
        cached_mirrors = [{"name": "test-mirror", "is_private": True}]
        mock_config_manager.get_scanned_mirrors.return_value = cached_mirrors

        with pytest.raises(typer.Exit) as exc_info:
            handle_scan_option(mock_config_manager, mock_config, "testuser", verbose=True)

        assert exc_info.value.exit_code == 0
        mock_display.assert_called_once_with(cached_mirrors)
        mock_scan.assert_not_called()

    @patch("cli_git.commands.modules.scan.scan_for_mirrors")
    def test_handle_scan_no_cache_verbose(self, mock_scan):
        """Test scan option without cache in verbose mode."""
        mock_config_manager = Mock()
        mock_config = {"github": {"default_org": "test-org"}}
        mirrors = [{"name": "test-mirror", "is_private": True}]

        mock_config_manager.get_scanned_mirrors.return_value = None
        mock_scan.return_value = mirrors

        with patch(
            "cli_git.commands.update.update_validation.display_scan_results"
        ) as mock_display:
            with pytest.raises(typer.Exit) as exc_info:
                handle_scan_option(mock_config_manager, mock_config, "testuser", verbose=True)

        assert exc_info.value.exit_code == 0
        mock_scan.assert_called_once_with("testuser", "test-org")
        mock_config_manager.save_scanned_mirrors.assert_called_once_with(mirrors)
        mock_display.assert_called_once_with(mirrors)

    @patch("cli_git.commands.modules.scan.scan_for_mirrors")
    def test_handle_scan_no_mirrors_verbose(self, mock_scan):
        """Test scan option when no mirrors found in verbose mode."""
        mock_config_manager = Mock()
        mock_config = {"github": {"default_org": "test-org"}}

        mock_config_manager.get_scanned_mirrors.return_value = None
        mock_scan.return_value = []

        with pytest.raises(typer.Exit) as exc_info:
            handle_scan_option(mock_config_manager, mock_config, "testuser", verbose=True)

        assert exc_info.value.exit_code == 0

    @patch("cli_git.commands.modules.scan.scan_for_mirrors")
    def test_handle_scan_pipe_friendly(self, mock_scan):
        """Test scan option in pipe-friendly mode."""
        mock_config_manager = Mock()
        mock_config = {"github": {"default_org": "test-org"}}
        mirrors = [
            {"name": "mirror1", "is_private": True},
            {"name": "mirror2", "is_private": False},
        ]

        mock_config_manager.get_scanned_mirrors.return_value = mirrors

        with pytest.raises(typer.Exit) as exc_info:
            handle_scan_option(mock_config_manager, mock_config, "testuser", verbose=False)

        assert exc_info.value.exit_code == 0


class TestDisplayScanResults:
    """Tests for display_scan_results function."""

    def test_display_scan_results_full_info(self):
        """Test displaying scan results with full mirror information."""
        mirrors = [
            {
                "name": "test-mirror",
                "is_private": True,
                "description": "Test mirror repository",
                "upstream": "https://github.com/upstream/repo",
                "updated_at": "2023-01-01T12:00:00Z",
            }
        ]

        with pytest.raises(typer.Exit) as exc_info:
            display_scan_results(mirrors)

        assert exc_info.value.exit_code == 0

    def test_display_scan_results_minimal_info(self):
        """Test displaying scan results with minimal mirror information."""
        mirrors = [{"name": "test-mirror", "is_private": False}]

        with pytest.raises(typer.Exit) as exc_info:
            display_scan_results(mirrors)

        assert exc_info.value.exit_code == 0

    def test_display_scan_results_with_secrets_upstream(self):
        """Test displaying scan results with upstream configured via secrets."""
        mirrors = [
            {
                "name": "test-mirror",
                "is_private": True,
                "description": "Test mirror repository",
                # No upstream field - should show "configured via secrets"
            }
        ]

        with pytest.raises(typer.Exit) as exc_info:
            display_scan_results(mirrors)

        assert exc_info.value.exit_code == 0

    def test_display_scan_results_invalid_date(self):
        """Test displaying scan results with invalid date format."""
        mirrors = [{"name": "test-mirror", "is_private": True, "updated_at": "invalid-date"}]

        # Should not raise exception, just skip date formatting
        with pytest.raises(typer.Exit) as exc_info:
            display_scan_results(mirrors)

        assert exc_info.value.exit_code == 0


class TestFindMirrorsToUpdate:
    """Tests for find_mirrors_to_update function."""

    @patch("cli_git.commands.modules.interactive.select_mirrors_interactive")
    def test_find_mirrors_specific_repo(self, mock_select):
        """Test finding mirrors for a specific repository."""
        mock_config_manager = Mock()
        mock_config = {}

        result = find_mirrors_to_update(
            repo="user/repo",
            config_manager=mock_config_manager,
            config=mock_config,
            username="testuser",
        )

        expected = [{"mirror": "https://github.com/user/repo", "upstream": "", "name": "user/repo"}]
        assert result == expected
        mock_select.assert_not_called()

    @patch("cli_git.commands.modules.interactive.select_mirrors_interactive")
    def test_find_mirrors_from_cache(self, mock_select):
        """Test finding mirrors from cached scan results."""
        mock_config_manager = Mock()
        mock_config = {}
        cached_mirrors = [{"name": "test-mirror"}]
        selected_mirrors = [{"name": "test-mirror"}]

        mock_config_manager.get_scanned_mirrors.return_value = cached_mirrors
        mock_select.return_value = selected_mirrors

        result = find_mirrors_to_update(
            repo=None, config_manager=mock_config_manager, config=mock_config, username="testuser"
        )

        assert result == selected_mirrors
        mock_select.assert_called_once_with(cached_mirrors)

    @patch("cli_git.commands.modules.interactive.select_mirrors_interactive")
    @patch("cli_git.commands.modules.scan.scan_for_mirrors")
    def test_find_mirrors_scan_needed(self, mock_scan, mock_select):
        """Test finding mirrors when scanning is needed."""
        mock_config_manager = Mock()
        mock_config = {"github": {"default_org": "test-org"}}
        scanned_mirrors = [{"name": "test-mirror"}]
        selected_mirrors = [{"name": "test-mirror"}]

        mock_config_manager.get_scanned_mirrors.return_value = None
        mock_config_manager.get_recent_mirrors.return_value = []
        mock_scan.return_value = scanned_mirrors
        mock_select.return_value = selected_mirrors

        result = find_mirrors_to_update(
            repo=None, config_manager=mock_config_manager, config=mock_config, username="testuser"
        )

        assert result == selected_mirrors
        mock_scan.assert_called_once_with("testuser", "test-org")
        mock_config_manager.save_scanned_mirrors.assert_called_once_with(scanned_mirrors)

    @patch("cli_git.commands.modules.interactive.select_mirrors_interactive")
    @patch("cli_git.commands.modules.scan.scan_for_mirrors")
    def test_find_mirrors_no_mirrors_found(self, mock_scan, mock_select):
        """Test when no mirrors are found anywhere."""
        mock_config_manager = Mock()
        mock_config = {"github": {"default_org": "test-org"}}

        mock_config_manager.get_scanned_mirrors.return_value = None
        mock_config_manager.get_recent_mirrors.return_value = []
        mock_scan.return_value = []

        with pytest.raises(typer.Exit) as exc_info:
            find_mirrors_to_update(
                repo=None,
                config_manager=mock_config_manager,
                config=mock_config,
                username="testuser",
            )

        assert exc_info.value.exit_code == 0
        mock_select.assert_not_called()
