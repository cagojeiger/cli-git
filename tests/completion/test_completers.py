"""Tests for completion functionality."""

from unittest.mock import MagicMock, patch

from cli_git.completion.completers import complete_organization, complete_prefix, complete_schedule


class TestCompletion:
    """Test cases for completion functions."""

    @patch("cli_git.completion.completers.get_user_organizations")
    def test_complete_organization_success(self, mock_get_orgs):
        """Test organization completion with successful API call."""
        mock_get_orgs.return_value = ["myorg", "mycompany", "another-org"]

        # Test partial match
        result = complete_organization("my")
        expected = [("myorg", "GitHub Organization"), ("mycompany", "GitHub Organization")]
        assert result == expected

        # Test no match
        result = complete_organization("xyz")
        assert result == []

        # Test case insensitive
        result = complete_organization("MY")
        expected = [("myorg", "GitHub Organization"), ("mycompany", "GitHub Organization")]
        assert result == expected

    @patch("cli_git.completion.completers.get_user_organizations")
    def test_complete_organization_github_error(self, mock_get_orgs):
        """Test organization completion when GitHub API fails."""
        from cli_git.utils.gh import GitHubError

        mock_get_orgs.side_effect = GitHubError("API error")

        result = complete_organization("test")
        assert result == []

    def test_complete_schedule(self):
        """Test schedule completion."""
        # Test empty input returns all
        result = complete_schedule("")
        assert len(result) == 6
        assert ("0 * * * *", "Every hour") in result
        assert ("0 0 * * *", "Every day at midnight UTC") in result

        # Test partial match
        result = complete_schedule("0 0")
        expected = [
            ("0 0 * * *", "Every day at midnight UTC"),
            ("0 0 * * 0", "Every Sunday at midnight UTC"),
            ("0 0,12 * * *", "Twice daily (midnight and noon UTC)"),
            ("0 0 1 * *", "First day of every month"),
        ]
        assert result == expected

        # Test no match
        result = complete_schedule("5 5")
        assert result == []

    @patch("cli_git.completion.completers.ConfigManager")
    def test_complete_prefix(self, mock_config_manager):
        """Test prefix completion."""
        # Mock config
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {"preferences": {"default_prefix": "custom-"}}

        # Test empty input returns all
        result = complete_prefix("")
        assert len(result) >= 5
        assert ("custom-", "Default prefix") in result
        assert ("mirror-", "Standard mirror prefix") in result
        assert ("", "No prefix") in result

        # Test partial match
        result = complete_prefix("m")
        assert ("mirror-", "Standard mirror prefix") in result

        # Test prefix match
        result = complete_prefix("fork")
        assert ("fork-", "Fork prefix") in result

    @patch("cli_git.completion.completers.ConfigManager")
    def test_complete_prefix_no_default(self, mock_config_manager):
        """Test prefix completion when no default is set."""
        # Mock config without default prefix
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {"preferences": {}}

        result = complete_prefix("")
        # Should fall back to "mirror-" as default
        assert ("mirror-", "Default prefix") in result
