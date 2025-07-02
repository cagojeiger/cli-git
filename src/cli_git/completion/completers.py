"""Completion functions for cli-git commands."""

import json
import subprocess
from typing import List, Tuple, Union

from cli_git.utils.cache_manager import CacheManager
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError, get_current_username, get_user_organizations
from cli_git.utils.mirror_detection import extract_mirror_info_from_repo_data, is_mirror_repository
from cli_git.utils.upstream_extractor import (
    extract_repo_name_from_url,
    get_mirror_description_from_cache,
)


def _check_repo_match(repo_name: str, incomplete: str) -> bool:
    """Check if repository name matches incomplete string.

    Args:
        repo_name: Repository name in "owner/repo" format
        incomplete: Partial input from user

    Returns:
        True if repo matches the incomplete string
    """
    if "/" in incomplete:
        # Full owner/repo format
        return repo_name.lower().startswith(incomplete.lower())
    else:
        # Just repo name - check if repo part matches
        if "/" in repo_name:
            _, name_only = repo_name.split("/", 1)
            return name_only.lower().startswith(incomplete.lower())
        else:
            return repo_name.lower().startswith(incomplete.lower())


def _complete_from_scanned_cache(
    cache_manager: CacheManager, incomplete: str
) -> List[Tuple[str, str]]:
    """Complete from scanned mirrors cache (highest priority).

    Args:
        cache_manager: Cache manager instance
        incomplete: Partial repository name

    Returns:
        List of (repo_name, description) tuples
    """
    scanned_mirrors = cache_manager.config_manager.get_scanned_mirrors()
    if not scanned_mirrors:
        return []

    completions = []
    for mirror in scanned_mirrors:
        mirror_name = mirror.get("name", "")
        if not mirror_name or not _check_repo_match(mirror_name, incomplete):
            continue

        description = get_mirror_description_from_cache(mirror)
        completions.append((mirror_name, description))

    return completions


def _complete_from_repo_cache(
    cache_manager: CacheManager, incomplete: str
) -> List[Tuple[str, str]]:
    """Complete from repository completion cache.

    Args:
        cache_manager: Cache manager instance
        incomplete: Partial repository name

    Returns:
        List of (repo_name, description) tuples
    """
    cached_repos = cache_manager.config_manager.get_repo_completion_cache()
    if cached_repos is None:
        return []

    completions = []
    for repo_data in cached_repos:
        repo_name = repo_data.get("nameWithOwner", "")
        if not repo_data.get("is_mirror", False) or not _check_repo_match(repo_name, incomplete):
            continue

        description = repo_data.get("description", "Mirror repository")
        if not description:
            description = "Mirror repository"
        completions.append((repo_name, f"🔄 {description}"))

    return completions


def _complete_from_recent_cache(
    cache_manager: CacheManager, incomplete: str
) -> List[Tuple[str, str]]:
    """Complete from recent mirrors cache (fallback).

    Args:
        cache_manager: Cache manager instance
        incomplete: Partial repository name

    Returns:
        List of (repo_name, description) tuples
    """
    recent_mirrors = cache_manager.config_manager.get_recent_mirrors()
    if not recent_mirrors:
        return []

    completions = []
    for mirror in recent_mirrors[:10]:  # Limit to recent 10
        mirror_name = mirror.get("name", "")

        # Extract from URL if name not available
        if not mirror_name:
            mirror_name = extract_repo_name_from_url(mirror.get("mirror", ""))

        if not mirror_name or not _check_repo_match(mirror_name, incomplete):
            continue

        description = get_mirror_description_from_cache(mirror)
        completions.append((mirror_name, description))

    return completions


def _complete_from_live_api(cache_manager: CacheManager, incomplete: str) -> List[Tuple[str, str]]:
    """Complete using live GitHub API calls (last resort).

    Args:
        cache_manager: Cache manager instance
        incomplete: Partial repository name

    Returns:
        List of (repo_name, description) tuples
    """
    try:
        username = get_current_username()
        config = cache_manager.config_manager.get_config()
        default_org = config["github"].get("default_org", "")

        # Determine search owners
        if "/" in incomplete:
            owner, _ = incomplete.split("/", 1)
            owners = [owner] if owner else [username]
        else:
            owners = [username]
            if default_org and default_org != username:
                owners.append(default_org)

        all_repos_data = []
        completions = []

        # Search repositories for each owner
        for owner in owners:
            try:
                repos = _fetch_repositories_for_owner(owner)
                for repo in repos:
                    if repo.get("isArchived", False):
                        continue

                    repo_name = repo["nameWithOwner"]
                    is_mirror = is_mirror_repository(repo_name)

                    # Add to cache data
                    repo_data = extract_mirror_info_from_repo_data({**repo, "is_mirror": is_mirror})
                    all_repos_data.append(repo_data)

                    # Add to completions if it's a mirror and matches
                    if is_mirror and _check_repo_match(repo_name, incomplete):
                        description = (
                            repo.get("description", "Mirror repository") or "Mirror repository"
                        )
                        completions.append((repo_name, f"🔄 {description}"))

            except (subprocess.CalledProcessError, json.JSONDecodeError):
                continue

        # Save results to cache
        cache_manager.save_api_results_to_cache(all_repos_data)

        return completions

    except GitHubError:
        return []


def _fetch_repositories_for_owner(owner: str) -> List[dict]:
    """Fetch repositories for a specific owner using GitHub API.

    Args:
        owner: Repository owner (username or organization)

    Returns:
        List of repository data dictionaries
    """
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
        timeout=30,
    )
    return json.loads(result.stdout)


def complete_repository(incomplete: str) -> List[Union[str, Tuple[str, str]]]:
    """Complete repository names for mirror operations.

    Uses a hierarchical cache system with fallback to live API.

    Args:
        incomplete: Partial repository name (can be "owner/repo" or just "repo")

    Returns:
        List of (repository, description) tuples, limited to 20 results
    """
    cache_manager = CacheManager()
    completions = []

    # Try each cache level in priority order
    cache_functions = [
        _complete_from_scanned_cache,
        _complete_from_repo_cache,
        _complete_from_recent_cache,
    ]

    for cache_func in cache_functions:
        completions = cache_func(cache_manager, incomplete)
        if completions:
            break

    # Fall back to live API if no cache results
    if not completions:
        completions = _complete_from_live_api(cache_manager, incomplete)

        # Also try recent cache as final fallback for API failures
        if not completions:
            completions = _complete_from_recent_cache(cache_manager, incomplete)

    # Sort and limit results
    completions.sort(key=lambda x: x[0])
    return completions[:20]


def complete_organization(incomplete: str) -> List[Union[str, Tuple[str, str]]]:
    """Complete organization names.

    Args:
        incomplete: Partial organization name

    Returns:
        List of organizations or tuples of (org, description)
    """
    try:
        orgs = get_user_organizations()
        return [
            (org, "GitHub Organization")
            for org in orgs
            if org.lower().startswith(incomplete.lower())
        ]
    except GitHubError:
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

    return [(s, d) for s, d in schedules if s.startswith(incomplete)]


def complete_prefix(incomplete: str) -> List[Tuple[str, str]]:
    """Complete common mirror prefixes.

    Args:
        incomplete: Partial prefix string

    Returns:
        List of tuples of (prefix, description)
    """
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

    return [(p, d) for p, d in unique_prefixes if p.startswith(incomplete)]
