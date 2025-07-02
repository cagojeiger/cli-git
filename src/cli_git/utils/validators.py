"""Validation functions for cli-git commands."""

import re
from typing import Optional

from cli_git.utils.gh import GitHubError, get_user_organizations


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


# Validation patterns and constants
GITHUB_URL_PATTERNS = [
    r"^https://github\.com/[\w.-]+/[\w.-]+/?$",  # HTTPS URL
    r"^git@github\.com:[\w.-]+/[\w.-]+\.git$",  # SSH URL
    r"^github\.com/[\w.-]+/[\w.-]+/?$",  # Short form
]

REPO_NAME_PATTERN = r"^[a-zA-Z0-9._-]+$"
PREFIX_PATTERN = r"^[a-zA-Z0-9_-]+$"
SLACK_WEBHOOK_PATTERN = r"^https://hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+$"

RESERVED_REPO_NAMES = ["..", ".", "con", "prn", "aux", "nul"]

# Cron field validation ranges
CRON_FIELD_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "weekday": (0, 7),
}


def _validate_with_pattern(value: str, patterns: list, error_message: str) -> str:
    """Generic pattern validation helper.

    Args:
        value: Value to validate
        patterns: List of regex patterns to match against
        error_message: Error message to show on validation failure

    Returns:
        The value if valid

    Raises:
        ValidationError: If value doesn't match any pattern
    """
    if not any(re.match(pattern, value) for pattern in patterns):
        raise ValidationError(error_message)
    return value


def _validate_length(value: str, max_length: int, field_name: str) -> str:
    """Generic length validation helper.

    Args:
        value: Value to validate
        max_length: Maximum allowed length
        field_name: Name of the field for error messages

    Returns:
        The value if valid

    Raises:
        ValidationError: If value is too long
    """
    if len(value) > max_length:
        raise ValidationError(
            f"❌ {field_name} too long: {len(value)} characters (max {max_length})"
        )
    return value


def _validate_not_reserved(value: str, reserved_list: list, field_name: str) -> str:
    """Generic reserved name validation helper.

    Args:
        value: Value to validate
        reserved_list: List of reserved names
        field_name: Name of the field for error messages

    Returns:
        The value if valid

    Raises:
        ValidationError: If value is reserved
    """
    if value.lower() in reserved_list:
        raise ValidationError(f"❌ {field_name} is reserved: '{value}'")
    return value


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

    # Validate each field
    field_names = ["minute", "hour", "day", "month", "weekday"]
    for field_name, field_value in zip(field_names, fields):
        min_val, max_val = CRON_FIELD_RANGES[field_name]
        if not _validate_cron_field(field_value, min_val, max_val):
            raise ValidationError(
                f"❌ Invalid {field_name} field: '{field_value}' (must be {min_val}-{max_val})"
            )

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
        return _validate_cron_step_field(field, min_val, max_val)

    # Handle ranges (n-m)
    if "-" in field:
        return _validate_cron_range_field(field, min_val, max_val)

    # Handle lists (n,m,o)
    if "," in field:
        return _validate_cron_list_field(field, min_val, max_val)

    # Handle single values
    return _validate_cron_single_value(field, min_val, max_val)


def _validate_cron_step_field(field: str, min_val: int, max_val: int) -> bool:
    """Validate cron step field (*/n or n-m/s)."""
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

    if base == "*":
        return True
    elif "-" in base:
        return _validate_cron_range_field(base, min_val, max_val)

    return False


def _validate_cron_range_field(field: str, min_val: int, max_val: int) -> bool:
    """Validate cron range field (n-m)."""
    try:
        start, end = field.split("-")
        start_val = int(start)
        end_val = int(end)
        return min_val <= start_val <= end_val <= max_val
    except ValueError:
        return False


def _validate_cron_list_field(field: str, min_val: int, max_val: int) -> bool:
    """Validate cron list field (n,m,o)."""
    try:
        values = [int(v) for v in field.split(",")]
        return all(min_val <= v <= max_val for v in values)
    except ValueError:
        return False


def _validate_cron_single_value(field: str, min_val: int, max_val: int) -> bool:
    """Validate single cron value."""
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
    return _validate_with_pattern(
        url,
        GITHUB_URL_PATTERNS,
        f"❌ Invalid GitHub repository URL: '{url}'\n"
        "   Expected format:\n"
        "   - https://github.com/owner/repo\n"
        "   - git@github.com:owner/repo.git\n"
        "   - github.com/owner/repo",
    )


def validate_repository_name(name: str) -> str:
    """Validate repository name according to GitHub rules.

    Args:
        name: Repository name to validate

    Returns:
        The name if valid

    Raises:
        ValidationError: If name is invalid
    """
    if not name:
        raise ValidationError("❌ Repository name cannot be empty")

    # Validate length
    _validate_length(name, 100, "Repository name")

    # Check reserved names
    _validate_not_reserved(name, RESERVED_REPO_NAMES, "Repository name")

    # Must start with alphanumeric
    if not re.match(r"^[a-zA-Z0-9]", name):
        raise ValidationError(f"❌ Repository name must start with a letter or number: '{name}'")

    # Validate character pattern
    _validate_with_pattern(
        name,
        [REPO_NAME_PATTERN],
        f"❌ Repository name contains invalid characters: '{name}'\n"
        "   Allowed: letters, numbers, dash (-), underscore (_), period (.)",
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
        return prefix  # Empty prefix is valid

    # Validate length
    _validate_length(prefix, 50, "Prefix")

    # Validate character pattern
    _validate_with_pattern(
        prefix,
        [PREFIX_PATTERN],
        f"❌ Prefix contains invalid characters: '{prefix}'\n"
        "   Allowed: letters, numbers, dash (-), underscore (_)",
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
        return url  # Empty is valid (optional)

    return _validate_with_pattern(
        url,
        [SLACK_WEBHOOK_PATTERN],
        "❌ Invalid Slack webhook URL format\n"
        "   Expected: https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX",
    )
