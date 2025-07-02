"""Utility functions for completion operations."""

from typing import Tuple

from cli_git.utils.github import extract_repo_name_from_url, format_repo_description


def matches_incomplete(repo_name: str, incomplete: str) -> bool:
    """Check if repository name matches the incomplete string.

    Args:
        repo_name: Full repository name (owner/repo format)
        incomplete: Partial string (can be "owner/repo" or just "repo")

    Returns:
        True if matches, False otherwise
    """
    if not repo_name or not incomplete:
        return not incomplete  # Empty incomplete matches everything

    if "/" in incomplete:
        # Full owner/repo format
        return repo_name.lower().startswith(incomplete.lower())
    else:
        # Just repo name - check if repo name part matches
        if "/" in repo_name:
            _, name_only = repo_name.split("/", 1)
            return name_only.lower().startswith(incomplete.lower())
        return repo_name.lower().startswith(incomplete.lower())


def extract_mirror_name_from_url(mirror_url: str) -> str:
    """Extract repository name from mirror URL.

    Args:
        mirror_url: Mirror URL (any format)

    Returns:
        Repository name in "owner/repo" format, or original URL if parsing fails
    """
    repo_name = extract_repo_name_from_url(mirror_url)
    return repo_name if repo_name else mirror_url


def create_completion_entry(
    repo_name: str, description: str = "", is_mirror: bool = True
) -> Tuple[str, str]:
    """Create a completion entry tuple.

    Args:
        repo_name: Repository name
        description: Repository description
        is_mirror: Whether this is a mirror repository

    Returns:
        Tuple of (repo_name, formatted_description)
    """
    if not description:
        description = "Mirror repository" if is_mirror else "Repository"

    # Add emoji prefix for mirrors
    if is_mirror and not description.startswith("🔄"):
        description = f"🔄 {description}"

    return (repo_name, description)


def get_mirror_description(upstream: str) -> str:
    """Get description for a mirror based on upstream URL.

    Args:
        upstream: Upstream repository URL

    Returns:
        Formatted description string
    """
    return format_repo_description(upstream)
