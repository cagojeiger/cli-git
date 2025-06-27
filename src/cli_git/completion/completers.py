"""Completion functions for cli-git commands."""

from typing import List, Tuple, Union

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError, get_user_organizations


def complete_organization(incomplete: str) -> List[Union[str, Tuple[str, str]]]:
    """Complete organization names.

    Args:
        incomplete: Partial organization name

    Returns:
        List of organizations or tuples of (org, description)
    """
    try:
        orgs = get_user_organizations()
        completions = []
        for org in orgs:
            if org.lower().startswith(incomplete.lower()):
                completions.append((org, "GitHub Organization"))
        return completions
    except GitHubError:
        # If we can't get orgs, return empty list
        return []


def complete_schedule(incomplete: str) -> List[Tuple[str, str]]:
    """Complete common cron schedules.

    Args:
        incomplete: Partial schedule string

    Returns:
        List of tuples of (schedule, description)
    """
    schedules = [
        ("0 * * * *", "Every hour"),
        ("0 0 * * *", "Every day at midnight UTC"),
        ("0 0 * * 0", "Every Sunday at midnight UTC"),
        ("0 0,12 * * *", "Twice daily (midnight and noon UTC)"),
        ("0 */6 * * *", "Every 6 hours"),
        ("0 0 1 * *", "First day of every month"),
    ]

    if not incomplete:
        return schedules

    # Filter schedules that start with the incomplete string
    return [(s, d) for s, d in schedules if s.startswith(incomplete)]


def complete_prefix(incomplete: str) -> List[Tuple[str, str]]:
    """Complete common mirror prefixes.

    Args:
        incomplete: Partial prefix string

    Returns:
        List of tuples of (prefix, description)
    """
    # Get default from config
    config_manager = ConfigManager()
    config = config_manager.get_config()
    default_prefix = config["preferences"].get("default_prefix", "mirror-")

    prefixes = [
        (default_prefix, "Default prefix"),
        ("mirror-", "Standard mirror prefix"),
        ("fork-", "Fork prefix"),
        ("private-", "Private prefix"),
        ("backup-", "Backup prefix"),
        ("", "No prefix"),
    ]

    # Remove duplicates while preserving order
    seen = set()
    unique_prefixes = []
    for prefix, desc in prefixes:
        if prefix not in seen:
            seen.add(prefix)
            unique_prefixes.append((prefix, desc))

    if not incomplete:
        return unique_prefixes

    # Filter prefixes that start with the incomplete string
    return [(p, d) for p, d in unique_prefixes if p.startswith(incomplete)]
