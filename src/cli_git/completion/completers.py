"""Completion functions for cli-git commands."""

import json
import subprocess
from typing import Dict, List, Tuple, Union

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError, get_current_username, get_user_organizations
from cli_git.utils.github import extract_repo_name_from_url, format_repo_description


def _matches_incomplete(repo_name: str, incomplete: str) -> bool:
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


def _extract_mirror_name_from_url(mirror_url: str) -> str:
    """Extract repository name from mirror URL.

    Args:
        mirror_url: Mirror URL (any format)

    Returns:
        Repository name in "owner/repo" format, or original URL if parsing fails
    """
    repo_name = extract_repo_name_from_url(mirror_url)
    return repo_name if repo_name else mirror_url


def _create_completion_entry(
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


def _get_completions_from_scanned_mirrors(
    incomplete: str, config_manager: ConfigManager
) -> List[Tuple[str, str]]:
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
        if _matches_incomplete(mirror_name, incomplete):
            description = mirror.get("description", "")
            completions.append(_create_completion_entry(mirror_name, description))

    return completions


def _get_completions_from_cache(
    incomplete: str, config_manager: ConfigManager
) -> List[Tuple[str, str]]:
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
        if _matches_incomplete(repo_name, incomplete):
            description = repo_data.get("description", "")
            completions.append(_create_completion_entry(repo_name, description))

    # Also check recent mirrors
    recent_mirrors = config_manager.get_recent_mirrors()
    if recent_mirrors:
        for mirror in recent_mirrors:
            mirror_name = mirror.get("name", "")
            if not mirror_name or any(c[0] == mirror_name for c in completions):
                continue

            if _matches_incomplete(mirror_name, incomplete):
                upstream = mirror.get("upstream", "")
                desc = format_repo_description(upstream, "Mirror repository (from cache)")
                completions.append((mirror_name, desc))

    return completions


def _check_is_mirror(repo_name: str) -> bool:
    """Check if a repository is a mirror by looking for mirror-sync.yml.

    Args:
        repo_name: Repository name in owner/repo format

    Returns:
        True if repository has mirror-sync.yml workflow
    """
    try:
        check = subprocess.run(
            ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
            capture_output=True,
            timeout=5,
        )
        return check.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _determine_search_owners(
    incomplete: str, username: str, default_org: str
) -> Tuple[List[str], str]:
    """Determine which owners to search for repositories.

    Args:
        incomplete: Partial repository name
        username: Current GitHub username
        default_org: Default organization from config

    Returns:
        Tuple of (owners_list, repo_part)
    """
    if "/" in incomplete:
        # User is typing owner/repo format
        owner, repo_part = incomplete.split("/", 1)
        owners = [owner] if owner else [username]
    else:
        # Just repo name - search in user and default org
        owners = [username]
        if default_org and default_org != username:
            owners.append(default_org)
        repo_part = incomplete

    return owners, repo_part


def _fetch_repos_for_owner(owner: str, repo_part: str, incomplete: str) -> List[Dict[str, str]]:
    """Fetch repositories for a specific owner.

    Args:
        owner: Repository owner (user or org)
        repo_part: Repository name part to match
        incomplete: Full incomplete string

    Returns:
        List of repository data dictionaries
    """
    try:
        # Use gh CLI to get repositories
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                owner,
                "--limit",
                "100",
                "--json",
                "nameWithOwner,description,isArchived,updatedAt",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        repos = json.loads(result.stdout)
        processed_repos = []

        # Process all repos and check if they're mirrors
        for repo in repos:
            if repo.get("isArchived", False):
                continue

            repo_name = repo["nameWithOwner"]

            # Check if it's a mirror by looking for workflow
            is_mirror = _check_is_mirror(repo_name)

            # Add to results
            repo_data = {
                "nameWithOwner": repo_name,
                "description": repo.get("description", ""),
                "is_mirror": is_mirror,
                "updatedAt": repo.get("updatedAt", ""),
            }
            processed_repos.append(repo_data)

        return processed_repos

    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def _get_completions_from_api(
    incomplete: str, config_manager: ConfigManager
) -> List[Tuple[str, str]]:
    """Get completions from GitHub API.

    Args:
        incomplete: Partial repository name
        config_manager: Configuration manager instance

    Returns:
        List of completion tuples
    """
    completions = []
    all_repos_data = []

    # Get current username and config
    username = get_current_username()
    config = config_manager.get_config()
    default_org = config["github"].get("default_org", "")

    # Determine owners to search
    owners, repo_part = _determine_search_owners(incomplete, username, default_org)

    # Fetch repos for each owner
    for owner in owners:
        repos = _fetch_repos_for_owner(owner, repo_part, incomplete)
        all_repos_data.extend(repos)

        # Add mirrors to completions
        for repo in repos:
            if repo["is_mirror"]:
                completions.append(
                    _create_completion_entry(repo["nameWithOwner"], repo["description"])
                )

    # Save to cache for future use
    if all_repos_data:
        config_manager.save_repo_completion_cache(all_repos_data)

    # Also add recent mirrors
    recent_mirrors = config_manager.get_recent_mirrors()
    if recent_mirrors:
        for mirror in recent_mirrors[:10]:
            mirror_name = mirror.get("name", "")
            if mirror_name and not any(c[0] == mirror_name for c in completions):
                if _matches_incomplete(mirror_name, incomplete):
                    upstream = mirror.get("upstream", "")
                    desc = format_repo_description(upstream, "Mirror repository")
                    completions.append((mirror_name, desc))

    return completions


def _get_fallback_completions(
    incomplete: str, config_manager: ConfigManager
) -> List[Tuple[str, str]]:
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

        if _matches_incomplete(mirror_name, incomplete):
            upstream = mirror.get("upstream", "")

            # Extract the repo name from URL
            if upstream:
                repo_name = _extract_mirror_name_from_url(upstream)
                desc = f"🔄 Mirror of {repo_name}"
            else:
                desc = "🔄 Mirror repository (from cache)"

            completions.append((mirror_name, desc))

    return completions


def _get_mirror_description(upstream: str) -> str:
    """Get description for a mirror based on upstream URL.

    Args:
        upstream: Upstream repository URL

    Returns:
        Formatted description string
    """
    return format_repo_description(upstream)


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


def complete_repository(incomplete: str) -> List[Union[str, Tuple[str, str]]]:
    """Complete repository names for mirror operations.

    Args:
        incomplete: Partial repository name (can be "owner/repo" or just "repo")

    Returns:
        List of tuples of (repository, description)
    """
    config_manager = ConfigManager()

    # First, check scanned mirrors cache (faster than completion cache)
    completions = _get_completions_from_scanned_mirrors(incomplete, config_manager)
    if completions:
        completions.sort(key=lambda x: x[0])
        return completions[:20]

    # Try to use cached completion data
    completions = _get_completions_from_cache(incomplete, config_manager)
    if completions:
        completions.sort(key=lambda x: x[0])
        return completions[:20]

    # If no cache, fall back to API calls
    try:
        completions = _get_completions_from_api(incomplete, config_manager)
        completions.sort(key=lambda x: x[0])
        return completions[:20]

    except GitHubError:
        # If we can't get repos, at least return cached mirrors
        return _get_fallback_completions(incomplete, config_manager)[:10]
