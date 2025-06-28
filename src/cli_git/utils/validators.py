"""Validation functions for cli-git commands."""

import re
from typing import Optional

from cli_git.utils.gh import GitHubError, get_user_organizations


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_organization(org: Optional[str]) -> Optional[str]:
    """Validate that the organization exists and user has access.

    Args:
        org: Organization name to validate

    Returns:
        The organization name if valid, None if empty

    Raises:
        ValidationError: If organization is invalid
    """
    if not org:
        return None

    try:
        available_orgs = get_user_organizations()
        if org not in available_orgs:
            raise ValidationError(
                f"❌ Organization '{org}' not found or you don't have access.\n"
                f"   Available organizations: {', '.join(available_orgs) if available_orgs else 'none'}"
            )
    except GitHubError:
        # If we can't verify, let it pass (GitHub CLI might have issues)
        pass

    return org


def validate_cron_schedule(schedule: str) -> str:
    """Validate cron schedule format.

    Args:
        schedule: Cron schedule string

    Returns:
        The schedule if valid

    Raises:
        ValidationError: If schedule format is invalid
    """
    # Split and check field count
    fields = schedule.strip().split()
    if len(fields) != 5:
        raise ValidationError(
            f"❌ Invalid cron schedule: '{schedule}'\n"
            "   Expected 5 fields: minute hour day month weekday\n"
            "   Example: '0 0 * * *' (daily at midnight)"
        )

    # Validate each field range
    try:
        minute, hour, day, month, weekday = fields

        # Validate minute (0-59)
        if not _validate_cron_field(minute, 0, 59):
            raise ValidationError(f"❌ Invalid minute field: '{minute}' (must be 0-59)")

        # Validate hour (0-23)
        if not _validate_cron_field(hour, 0, 23):
            raise ValidationError(f"❌ Invalid hour field: '{hour}' (must be 0-23)")

        # Validate day (1-31)
        if not _validate_cron_field(day, 1, 31):
            raise ValidationError(f"❌ Invalid day field: '{day}' (must be 1-31)")

        # Validate month (1-12)
        if not _validate_cron_field(month, 1, 12):
            raise ValidationError(f"❌ Invalid month field: '{month}' (must be 1-12)")

        # Validate weekday (0-7, where 0 and 7 are Sunday)
        if not _validate_cron_field(weekday, 0, 7):
            raise ValidationError(f"❌ Invalid weekday field: '{weekday}' (must be 0-7)")

    except ValueError as e:
        raise ValidationError(f"❌ Invalid cron schedule: {e}")

    return schedule


def _validate_cron_field(field: str, min_val: int, max_val: int) -> bool:
    """Validate a single cron field.

    Args:
        field: Cron field value
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        True if valid, False otherwise
    """
    if field == "*":
        return True

    # Handle step values (*/n or n-m/s)
    if "/" in field:
        parts = field.split("/")
        if len(parts) != 2:
            return False

        base, step_str = parts
        try:
            step = int(step_str)
            if step <= 0:
                return False
        except ValueError:
            return False

        # Base can be * or range
        if base == "*":
            return True
        elif "-" in base:
            # Range with step (e.g., 0-59/5)
            try:
                start, end = base.split("-")
                start_val = int(start)
                end_val = int(end)
                return min_val <= start_val <= end_val <= max_val
            except ValueError:
                return False
        else:
            return False

    # Handle ranges (n-m)
    if "-" in field:
        try:
            start, end = field.split("-")
            start_val = int(start)
            end_val = int(end)
            return min_val <= start_val <= end_val <= max_val
        except ValueError:
            return False

    # Handle lists (n,m,o)
    if "," in field:
        try:
            values = [int(v) for v in field.split(",")]
            return all(min_val <= v <= max_val for v in values)
        except ValueError:
            return False

    # Handle single values
    try:
        value = int(field)
        return min_val <= value <= max_val
    except ValueError:
        return False


def validate_github_url(url: str) -> str:
    """Validate GitHub repository URL format.

    Args:
        url: Repository URL to validate

    Returns:
        The URL if valid

    Raises:
        ValidationError: If URL format is invalid
    """
    # GitHub URL patterns
    patterns = [
        r"^https://github\.com/[\w.-]+/[\w.-]+/?$",  # HTTPS URL
        r"^git@github\.com:[\w.-]+/[\w.-]+\.git$",  # SSH URL
        r"^github\.com/[\w.-]+/[\w.-]+/?$",  # Short form
    ]

    if not any(re.match(pattern, url) for pattern in patterns):
        raise ValidationError(
            f"❌ Invalid GitHub repository URL: '{url}'\n"
            "   Expected format:\n"
            "   - https://github.com/owner/repo\n"
            "   - git@github.com:owner/repo.git\n"
            "   - github.com/owner/repo"
        )

    return url


def validate_repository_name(name: str) -> str:
    """Validate repository name according to GitHub rules.

    Args:
        name: Repository name to validate

    Returns:
        The name if valid

    Raises:
        ValidationError: If name is invalid
    """
    # GitHub repository name rules
    if not name:
        raise ValidationError("❌ Repository name cannot be empty")

    if len(name) > 100:
        raise ValidationError(f"❌ Repository name too long: {len(name)} characters (max 100)")

    # Reserved names (check first)
    reserved_names = ["..", ".", "con", "prn", "aux", "nul"]
    if name.lower() in reserved_names:
        raise ValidationError(f"❌ Repository name is reserved: '{name}'")

    # Must start with alphanumeric
    if not re.match(r"^[a-zA-Z0-9]", name):
        raise ValidationError(f"❌ Repository name must start with a letter or number: '{name}'")

    # Can only contain alphanumeric, dash, underscore, and period
    if not re.match(r"^[a-zA-Z0-9._-]+$", name):
        raise ValidationError(
            f"❌ Repository name contains invalid characters: '{name}'\n"
            "   Allowed: letters, numbers, dash (-), underscore (_), period (.)"
        )

    # Cannot end with .git
    if name.endswith(".git"):
        raise ValidationError(f"❌ Repository name cannot end with '.git': '{name}'")

    return name


def validate_prefix(prefix: str) -> str:
    """Validate repository name prefix.

    Args:
        prefix: Prefix to validate

    Returns:
        The prefix if valid

    Raises:
        ValidationError: If prefix is invalid
    """
    if not prefix:
        # Empty prefix is valid
        return prefix

    # Prefix should follow repository name rules but can end with dash
    if len(prefix) > 50:
        raise ValidationError(f"❌ Prefix too long: {len(prefix)} characters (max 50)")

    # Can only contain alphanumeric, dash, underscore
    if not re.match(r"^[a-zA-Z0-9_-]+$", prefix):
        raise ValidationError(
            f"❌ Prefix contains invalid characters: '{prefix}'\n"
            "   Allowed: letters, numbers, dash (-), underscore (_)"
        )

    return prefix


def validate_slack_webhook_url(url: str) -> str:
    """Validate Slack webhook URL format.

    Args:
        url: Slack webhook URL to validate

    Returns:
        The URL if valid or empty

    Raises:
        ValidationError: If URL format is invalid
    """
    if not url:
        # Empty is valid (optional)
        return url

    # Slack webhook URL pattern
    pattern = r"^https://hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+$"

    if not re.match(pattern, url):
        raise ValidationError(
            "❌ Invalid Slack webhook URL format\n"
            "   Expected: https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX"
        )

    return url
