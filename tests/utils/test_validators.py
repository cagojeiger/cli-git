"""Tests for validators module."""

from unittest.mock import patch

import pytest

from cli_git.utils.validators import (
    ValidationError,
    validate_cron_schedule,
    validate_github_url,
    validate_organization,
    validate_prefix,
    validate_repository_name,
    validate_slack_webhook_url,
)


class TestValidateOrganization:
    """Test organization validation."""

    @patch("cli_git.utils.validators.get_user_organizations")
    def test_valid_organization(self, mock_get_orgs):
        """Test validation with valid organization."""
        mock_get_orgs.return_value = ["myorg", "anotherorg"]
        assert validate_organization("myorg") == "myorg"

    @patch("cli_git.utils.validators.get_user_organizations")
    def test_invalid_organization(self, mock_get_orgs):
        """Test validation with invalid organization."""
        mock_get_orgs.return_value = ["myorg", "anotherorg"]
        with pytest.raises(ValidationError) as exc_info:
            validate_organization("invalidorg")
        assert "Organization 'invalidorg' not found" in str(exc_info.value)
        assert "Available organizations: myorg, anotherorg" in str(exc_info.value)

    def test_empty_organization(self):
        """Test validation with empty organization."""
        assert validate_organization(None) is None
        assert validate_organization("") is None

    @patch("cli_git.utils.validators.get_user_organizations")
    def test_organization_when_api_fails(self, mock_get_orgs):
        """Test validation when GitHub API fails."""
        from cli_git.utils.gh import GitHubError

        mock_get_orgs.side_effect = GitHubError("API error")
        # Should pass validation when API fails
        assert validate_organization("anyorg") == "anyorg"


class TestValidateCronSchedule:
    """Test cron schedule validation."""

    def test_valid_schedules(self):
        """Test with valid cron schedules."""
        valid_schedules = [
            "0 0 * * *",  # Daily at midnight
            "0 * * * *",  # Every hour
            "*/15 * * * *",  # Every 15 minutes
            "0 0,12 * * *",  # Twice daily
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly
            "30 2 * * 1-5",  # Weekdays at 2:30
            "0-59/5 * * * *",  # Every 5 minutes
        ]
        for schedule in valid_schedules:
            assert validate_cron_schedule(schedule) == schedule

    def test_invalid_field_count(self):
        """Test with wrong number of fields."""
        with pytest.raises(ValidationError) as exc_info:
            validate_cron_schedule("0 0 * *")  # Only 4 fields
        assert "Expected 5 fields" in str(exc_info.value)

    def test_invalid_minute(self):
        """Test with invalid minute field."""
        with pytest.raises(ValidationError) as exc_info:
            validate_cron_schedule("60 * * * *")  # 60 is invalid
        assert "Invalid minute field" in str(exc_info.value)

    def test_invalid_hour(self):
        """Test with invalid hour field."""
        with pytest.raises(ValidationError) as exc_info:
            validate_cron_schedule("0 24 * * *")  # 24 is invalid
        assert "Invalid hour field" in str(exc_info.value)

    def test_invalid_day(self):
        """Test with invalid day field."""
        with pytest.raises(ValidationError) as exc_info:
            validate_cron_schedule("0 0 0 * *")  # 0 is invalid for day
        assert "Invalid day field" in str(exc_info.value)

    def test_invalid_month(self):
        """Test with invalid month field."""
        with pytest.raises(ValidationError) as exc_info:
            validate_cron_schedule("0 0 * 13 *")  # 13 is invalid
        assert "Invalid month field" in str(exc_info.value)

    def test_invalid_weekday(self):
        """Test with invalid weekday field."""
        with pytest.raises(ValidationError) as exc_info:
            validate_cron_schedule("0 0 * * 8")  # 8 is invalid
        assert "Invalid weekday field" in str(exc_info.value)


class TestValidateGitHubUrl:
    """Test GitHub URL validation."""

    def test_valid_urls(self):
        """Test with valid GitHub URLs."""
        valid_urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/",
            "git@github.com:owner/repo.git",
            "github.com/owner/repo",
            "https://github.com/owner-name/repo-name",
            "https://github.com/owner.name/repo.name",
        ]
        for url in valid_urls:
            assert validate_github_url(url) == url

    def test_invalid_urls(self):
        """Test with invalid URLs."""
        invalid_urls = [
            "https://gitlab.com/owner/repo",  # Wrong domain
            "https://github.com/owner",  # Missing repo
            "not-a-url",
            "http://github.com/owner/repo",  # HTTP not HTTPS
            "github.com/",  # Missing owner/repo
        ]
        for url in invalid_urls:
            with pytest.raises(ValidationError) as exc_info:
                validate_github_url(url)
            assert "Invalid GitHub repository URL" in str(exc_info.value)


class TestValidateRepositoryName:
    """Test repository name validation."""

    def test_valid_names(self):
        """Test with valid repository names."""
        valid_names = [
            "my-repo",
            "my_repo",
            "my.repo",
            "MyRepo",
            "repo123",
            "123repo",
            "a",  # Single character
        ]
        for name in valid_names:
            assert validate_repository_name(name) == name

    def test_empty_name(self):
        """Test with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            validate_repository_name("")
        assert "Repository name cannot be empty" in str(exc_info.value)

    def test_too_long_name(self):
        """Test with name exceeding 100 characters."""
        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            validate_repository_name(long_name)
        assert "Repository name too long" in str(exc_info.value)

    def test_invalid_start_character(self):
        """Test with invalid starting character."""
        with pytest.raises(ValidationError) as exc_info:
            validate_repository_name("-repo")
        assert "must start with a letter or number" in str(exc_info.value)

    def test_invalid_characters(self):
        """Test with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            validate_repository_name("my repo")  # Space
        assert "contains invalid characters" in str(exc_info.value)

    def test_ends_with_git(self):
        """Test name ending with .git."""
        with pytest.raises(ValidationError) as exc_info:
            validate_repository_name("repo.git")
        assert "cannot end with '.git'" in str(exc_info.value)

    def test_reserved_names(self):
        """Test with reserved names."""
        reserved = [".", "..", "con", "prn", "aux", "nul"]
        for name in reserved:
            with pytest.raises(ValidationError) as exc_info:
                validate_repository_name(name)
            assert "Repository name is reserved" in str(exc_info.value)


class TestValidatePrefix:
    """Test prefix validation."""

    def test_valid_prefixes(self):
        """Test with valid prefixes."""
        valid_prefixes = [
            "mirror-",
            "fork-",
            "private-",
            "backup_",
            "test123-",
            "",  # Empty is valid
        ]
        for prefix in valid_prefixes:
            assert validate_prefix(prefix) == prefix

    def test_too_long_prefix(self):
        """Test with prefix exceeding 50 characters."""
        long_prefix = "a" * 51
        with pytest.raises(ValidationError) as exc_info:
            validate_prefix(long_prefix)
        assert "Prefix too long" in str(exc_info.value)

    def test_invalid_characters(self):
        """Test with invalid characters."""
        with pytest.raises(ValidationError) as exc_info:
            validate_prefix("my prefix")  # Space
        assert "Prefix contains invalid characters" in str(exc_info.value)


class TestValidateSlackWebhookUrl:
    """Test Slack webhook URL validation."""

    def test_valid_url(self):
        """Test with valid Slack webhook URL."""
        url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        assert validate_slack_webhook_url(url) == url

    def test_empty_url(self):
        """Test with empty URL (optional field)."""
        assert validate_slack_webhook_url("") == ""

    def test_invalid_urls(self):
        """Test with invalid URLs."""
        invalid_urls = [
            "https://slack.com/webhook",  # Wrong domain
            "https://hooks.slack.com/services/",  # Missing tokens
            "https://hooks.slack.com/services/T000/B000",  # Missing last token
            "http://hooks.slack.com/services/T000/B000/XXX",  # HTTP not HTTPS
            "not-a-url",
        ]
        for url in invalid_urls:
            with pytest.raises(ValidationError) as exc_info:
                validate_slack_webhook_url(url)
            assert "Invalid Slack webhook URL" in str(exc_info.value)
