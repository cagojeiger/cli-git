"""GitHub API-related completion functions."""

import json
import subprocess
from typing import Dict, List, Tuple

from cli_git.completion.utils import create_completion_entry, matches_incomplete
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import get_current_username
from cli_git.utils.github import format_repo_description


def determine_search_owners(
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


def check_is_mirror(repo_name: str) -> bool:
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


def fetch_repos_for_owner(owner: str, repo_part: str, incomplete: str) -> List[Dict[str, str]]:
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
            is_mirror = check_is_mirror(repo_name)

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


def get_completions_from_api(
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
    owners, repo_part = determine_search_owners(incomplete, username, default_org)

    # Fetch repos for each owner
    for owner in owners:
        repos = fetch_repos_for_owner(owner, repo_part, incomplete)
        all_repos_data.extend(repos)

        # Add mirrors to completions
        for repo in repos:
            if repo["is_mirror"]:
                completions.append(
                    create_completion_entry(repo["nameWithOwner"], repo["description"])
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
                if matches_incomplete(mirror_name, incomplete):
                    upstream = mirror.get("upstream", "")
                    desc = format_repo_description(upstream, "Mirror repository")
                    completions.append((mirror_name, desc))

    return completions
