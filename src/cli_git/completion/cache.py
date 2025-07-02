"""Cache-related completion functions."""

from cli_git.completion.utils import (
    create_completion_entry,
    extract_mirror_name_from_url,
    matches_incomplete,
)
from cli_git.utils.config import ConfigManager
from cli_git.utils.github import format_repo_description


def get_completions_from_scanned_mirrors(
    incomplete: str, config_manager: ConfigManager
) -> list[tuple[str, str]]:
    """Get completions from scanned mirrors cache.

    Args:
        incomplete: Partial repository name
        config_manager: Configuration manager instance

    Returns:
        List of completion tuples
    """
    completions = []
    scanned_mirrors = config_manager.get_scanned_mirrors()

    if not scanned_mirrors:
        return completions

    for mirror in scanned_mirrors:
        mirror_name = mirror.get("name", "")
        if not mirror_name:
            continue

        # Check if it matches the incomplete string
        if matches_incomplete(mirror_name, incomplete):
            description = mirror.get("description", "")
            completions.append(create_completion_entry(mirror_name, description))

    return completions


def get_completions_from_cache(
    incomplete: str, config_manager: ConfigManager
) -> list[tuple[str, str]]:
    """Get completions from repository completion cache.

    Args:
        incomplete: Partial repository name
        config_manager: Configuration manager instance

    Returns:
        List of completion tuples
    """
    completions = []
    cached_repos = config_manager.get_repo_completion_cache()

    if cached_repos is None:
        return completions

    # Filter cached repositories
    for repo_data in cached_repos:
        repo_name = repo_data["nameWithOwner"]
        is_mirror = repo_data.get("is_mirror", False)

        if not is_mirror:
            continue

        # Check if it matches the incomplete string
        if matches_incomplete(repo_name, incomplete):
            description = repo_data.get("description", "")
            completions.append(create_completion_entry(repo_name, description))

    # Also check recent mirrors
    recent_mirrors = config_manager.get_recent_mirrors()
    if recent_mirrors:
        for mirror in recent_mirrors:
            mirror_name = mirror.get("name", "")
            if not mirror_name or any(c[0] == mirror_name for c in completions):
                continue

            if matches_incomplete(mirror_name, incomplete):
                upstream = mirror.get("upstream", "")
                desc = format_repo_description(upstream, "Mirror repository (from cache)")
                completions.append((mirror_name, desc))

    return completions


def get_fallback_completions(
    incomplete: str, config_manager: ConfigManager
) -> list[tuple[str, str]]:
    """Get fallback completions from recent mirrors when API fails.

    Args:
        incomplete: Partial repository name
        config_manager: Configuration manager instance

    Returns:
        List of completion tuples
    """
    completions = []
    recent_mirrors = config_manager.get_recent_mirrors()

    if not recent_mirrors:
        return completions

    for mirror in recent_mirrors[:10]:
        mirror_name = mirror.get("name", "")
        if not mirror_name:
            continue

        if matches_incomplete(mirror_name, incomplete):
            upstream = mirror.get("upstream", "")

            # Extract the repo name from URL
            if upstream:
                repo_name = extract_mirror_name_from_url(upstream)
                desc = f"🔄 Mirror of {repo_name}"
            else:
                desc = "🔄 Mirror repository (from cache)"

            completions.append((mirror_name, desc))

    return completions
