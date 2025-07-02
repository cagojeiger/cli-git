"""Tests for completion functionality."""

import json
from unittest.mock import MagicMock, patch

from cli_git.completion.completers import (
    complete_organization,
    complete_prefix,
    complete_repository,
    complete_schedule,
)


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

    @patch("cli_git.completion.completers.get_current_username")
    @patch("cli_git.completion.completers.ConfigManager")
    @patch("subprocess.run")
    def test_complete_repository_basic(
        self, mock_subprocess, mock_config_manager, mock_get_username
    ):
        """Test basic repository completion."""
        # Setup mocks
        mock_get_username.return_value = "testuser"

        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"default_org": ""},
        }
        mock_manager.get_recent_mirrors.return_value = []
        mock_manager.get_repo_completion_cache.return_value = None  # No cache
        mock_manager.save_repo_completion_cache.return_value = None

        # Mock repository list
        repo_list = [
            {
                "nameWithOwner": "testuser/mirror-fastmcp",
                "description": "Mirror of fastmcp",
                "isArchived": False,
            },
            {
                "nameWithOwner": "testuser/regular-repo",
                "description": "Regular repository",
                "isArchived": False,
            },
            {
                "nameWithOwner": "testuser/mirror-typer",
                "description": None,
                "isArchived": False,
            },
        ]

        # Mock gh repo list call
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = json.dumps(repo_list)

        # Test partial repository name
        # First call returns repo list, then check for mirror-sync.yml
        # Note: regular-repo won't be checked since it doesn't start with "mirror"
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout=json.dumps(repo_list)),  # repo list
            MagicMock(returncode=0),  # mirror-fastmcp has workflow
            MagicMock(returncode=0),  # mirror-typer has workflow
        ]

        result = complete_repository("mirror")

        # Should only return mirror repositories
        assert len(result) == 2
        assert ("testuser/mirror-fastmcp", "🔄 Mirror of fastmcp") in result
        assert ("testuser/mirror-typer", "🔄 Mirror repository") in result

    @patch("cli_git.completion.completers.get_current_username")
    @patch("cli_git.completion.completers.ConfigManager")
    @patch("subprocess.run")
    def test_complete_repository_with_owner(
        self, mock_subprocess, mock_config_manager, mock_get_username
    ):
        """Test repository completion with owner specified."""
        # Setup mocks
        mock_get_username.return_value = "testuser"

        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"default_org": ""},
        }
        mock_manager.get_recent_mirrors.return_value = []
        mock_manager.get_repo_completion_cache.return_value = None  # No cache
        mock_manager.save_repo_completion_cache.return_value = None

        # Mock repository list for specific owner
        repo_list = [
            {
                "nameWithOwner": "anotheruser/mirror-project",
                "description": "Forked mirror",
                "isArchived": False,
            },
        ]

        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout=json.dumps(repo_list)),  # repo list
            MagicMock(returncode=0),  # has workflow
        ]

        result = complete_repository("anotheruser/mirror")

        assert len(result) == 1
        assert ("anotheruser/mirror-project", "🔄 Forked mirror") in result

    @patch("cli_git.completion.completers.ConfigManager")
    @patch("cli_git.completion.completers.get_current_username")
    def test_complete_repository_from_cache(self, mock_get_username, mock_config_manager_class):
        """Test repository completion from cache when API fails."""
        from cli_git.utils.gh import GitHubError

        # Setup mocks to fail getting username (simulating API failure)
        mock_get_username.side_effect = GitHubError("API error")

        # Create a single mock manager instance
        mock_manager = MagicMock()

        # Configure the mock manager
        mock_manager.get_config.return_value = {
            "github": {"default_org": ""},
        }
        mock_manager.get_recent_mirrors.return_value = [
            {
                "mirror": "https://github.com/testuser/mirror-cached",
                "upstream": "https://github.com/upstream/project",
                "name": "testuser/mirror-cached",
            },
            {
                "mirror": "https://github.com/testuser/mirror-another",
                "upstream": "",
                "name": "testuser/mirror-another",
            },
        ]
        mock_manager.get_repo_completion_cache.return_value = None  # No cache

        # Make ConfigManager class always return the same mock instance
        # This ensures both instantiations return the same mock
        mock_config_manager_class.return_value = mock_manager

        result = complete_repository("mirror")

        assert len(result) == 2
        assert any("mirror-cached" in r[0] for r in result)
        assert any("from cache" in r[1] for r in result)

    @patch("cli_git.completion.completers.get_current_username")
    @patch("cli_git.completion.completers.ConfigManager")
    @patch("subprocess.run")
    def test_complete_repository_with_org(
        self, mock_subprocess, mock_config_manager, mock_get_username
    ):
        """Test repository completion with organization."""
        # Setup mocks
        mock_get_username.return_value = "testuser"

        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.get_config.return_value = {
            "github": {"default_org": "myorg"},
        }
        mock_manager.get_recent_mirrors.return_value = []
        mock_manager.get_repo_completion_cache.return_value = None  # No cache
        mock_manager.save_repo_completion_cache.return_value = None

        # Mock repository lists for user and org
        user_repos = [
            {
                "nameWithOwner": "testuser/mirror-personal",
                "description": "Personal mirror",
                "isArchived": False,
            },
        ]
        org_repos = [
            {
                "nameWithOwner": "myorg/mirror-shared",
                "description": "Shared mirror",
                "isArchived": False,
            },
        ]

        # Mock calls: user repo list, check workflow, org repo list, check workflow
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout=json.dumps(user_repos)),  # user repo list
            MagicMock(returncode=0),  # user mirror has workflow
            MagicMock(returncode=0, stdout=json.dumps(org_repos)),  # org repo list
            MagicMock(returncode=0),  # org mirror has workflow
        ]

        result = complete_repository("mirror")

        assert len(result) == 2
        assert ("testuser/mirror-personal", "🔄 Personal mirror") in result
        assert ("myorg/mirror-shared", "🔄 Shared mirror") in result
