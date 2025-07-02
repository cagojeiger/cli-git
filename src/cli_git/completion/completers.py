"""Completion functions for cli-git commands."""

import json
import subprocess
from typing import List, Tuple, Union

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError, get_current_username, get_user_organizations


def _get_mirror_description(upstream: str) -> str:
    """Get description for a mirror based on upstream URL.

    Args:
        upstream: Upstream repository URL

    Returns:
        Formatted description string
    """
    if upstream:
        # Extract upstream name
        if "github.com/" in upstream:
            upstream_parts = upstream.split("github.com/")[-1].split("/")
            if len(upstream_parts) >= 2:
                upstream_name = f"{upstream_parts[0]}/{upstream_parts[1]}"
            else:
                upstream_name = upstream
        else:
            upstream_name = upstream
        return f"🔄 Mirror of {upstream_name}"
    else:
        return "🔄 Mirror repository"


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
    completions = []
    config_manager = ConfigManager()

    # First, check scanned mirrors cache (faster than completion cache)
    scanned_mirrors = config_manager.get_scanned_mirrors()
    if scanned_mirrors:
        for mirror in scanned_mirrors:
            mirror_name = mirror.get("name", "")
            if not mirror_name:
                continue

            # Check if it matches the incomplete string
            if "/" in incomplete:
                # Full owner/repo format
                if mirror_name.lower().startswith(incomplete.lower()):
                    description = mirror.get("description", "Mirror repository")
                    if not description:
                        description = "Mirror repository"
                    completions.append((mirror_name, f"🔄 {description}"))
            else:
                # Just repo name - check if repo name part matches
                if "/" in mirror_name:
                    _, name_only = mirror_name.split("/")
                    if name_only.lower().startswith(incomplete.lower()):
                        description = mirror.get("description", "Mirror repository")
                        if not description:
                            description = "Mirror repository"
                        completions.append((mirror_name, f"🔄 {description}"))

        # If we have results from scanned mirrors, return them
        if completions:
            completions.sort(key=lambda x: x[0])
            return completions[:20]

    # Try to use cached completion data
    cached_repos = config_manager.get_repo_completion_cache()

    if cached_repos is not None:
        # Use cached data
        for repo_data in cached_repos:
            repo_name = repo_data["nameWithOwner"]
            is_mirror = repo_data.get("is_mirror", False)

            if not is_mirror:
                continue

            # Check if it matches the incomplete string
            if "/" in incomplete:
                # Full owner/repo format
                if repo_name.lower().startswith(incomplete.lower()):
                    description = repo_data.get("description", "Mirror repository")
                    if not description:
                        description = "Mirror repository"
                    completions.append((repo_name, f"🔄 {description}"))
            else:
                # Just repo name - check if repo name part matches
                _, name_only = repo_name.split("/")
                if name_only.lower().startswith(incomplete.lower()):
                    description = repo_data.get("description", "Mirror repository")
                    if not description:
                        description = "Mirror repository"
                    completions.append((repo_name, f"🔄 {description}"))

        # Also check recent mirrors from cache
        recent_mirrors = config_manager.get_recent_mirrors()
        for mirror in recent_mirrors[:10]:
            mirror_name = mirror.get("name", "")
            if mirror_name and not any(c[0] == mirror_name for c in completions):
                # Check if it matches incomplete
                if "/" in incomplete:
                    if mirror_name.lower().startswith(incomplete.lower()):
                        upstream = mirror.get("upstream", "")
                        desc = _get_mirror_description(upstream)
                        completions.append((mirror_name, desc))
                else:
                    # Just repo name
                    _, name_only = (
                        mirror_name.split("/") if "/" in mirror_name else ("", mirror_name)
                    )
                    if name_only.lower().startswith(incomplete.lower()):
                        upstream = mirror.get("upstream", "")
                        desc = _get_mirror_description(upstream)
                        completions.append((mirror_name, desc))

        # Sort and return
        completions.sort(key=lambda x: x[0])
        return completions[:20]

    # If no cache, fall back to API calls
    try:
        # Get current username
        username = get_current_username()

        # Get config for organization
        config = config_manager.get_config()
        default_org = config["github"].get("default_org", "")

        # Determine if we're searching for a specific owner
        if "/" in incomplete:
            # User is typing owner/repo format
            owner, repo_part = incomplete.split("/", 1)
            owners = [owner] if owner else [username]
        else:
            # Just repo name - search in user's repos and default org
            owners = [username]
            if default_org and default_org != username:
                owners.append(default_org)
            repo_part = incomplete

        # Collect all repos for caching
        all_repos_data = []

        # Get repositories for each owner
        for owner in owners:
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

                # Process all repos and save to cache data
                for repo in repos:
                    if repo.get("isArchived", False):
                        continue

                    repo_name = repo["nameWithOwner"]

                    # Check if it's a mirror by looking for workflow
                    check = subprocess.run(
                        [
                            "gh",
                            "api",
                            f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml",
                        ],
                        capture_output=True,
                    )

                    is_mirror = check.returncode == 0

                    # Add to cache data
                    repo_data = {
                        "nameWithOwner": repo_name,
                        "description": repo.get("description", ""),
                        "is_mirror": is_mirror,
                        "updatedAt": repo.get("updatedAt", ""),
                    }
                    all_repos_data.append(repo_data)

                    # Add to completions if it's a mirror and matches
                    if is_mirror:
                        if "/" in incomplete:
                            # Full owner/repo format
                            if repo_name.lower().startswith(incomplete.lower()):
                                description = repo.get("description", "Mirror repository")
                                if not description:
                                    description = "Mirror repository"
                                completions.append((repo_name, f"🔄 {description}"))
                        else:
                            # Just repo name - check if repo name part matches
                            _, name_only = repo_name.split("/")
                            if name_only.lower().startswith(repo_part.lower()):
                                description = repo.get("description", "Mirror repository")
                                if not description:
                                    description = "Mirror repository"
                                completions.append((repo_name, f"🔄 {description}"))

            except (subprocess.CalledProcessError, json.JSONDecodeError):
                # Continue with next owner if this one fails
                continue

        # Save to cache for future use
        if all_repos_data:
            config_manager.save_repo_completion_cache(all_repos_data)

        # Also check recent mirrors from cache
        recent_mirrors = config_manager.get_recent_mirrors()
        for mirror in recent_mirrors[:10]:  # Limit to recent 10
            mirror_name = mirror.get("name", "")
            if not mirror_name:
                # Extract from URL
                mirror_url = mirror.get("mirror", "")
                if "github.com/" in mirror_url:
                    parts = mirror_url.split("github.com/")[-1].split("/")
                    if len(parts) >= 2:
                        mirror_name = f"{parts[0]}/{parts[1]}"

            if mirror_name:
                # Check if it matches incomplete
                if "/" in incomplete:
                    if mirror_name.lower().startswith(incomplete.lower()):
                        upstream = mirror.get("upstream", "")
                        if upstream:
                            # Extract upstream name
                            if "github.com/" in upstream:
                                upstream_parts = upstream.split("github.com/")[-1].split("/")
                                if len(upstream_parts) >= 2:
                                    upstream_name = f"{upstream_parts[0]}/{upstream_parts[1]}"
                                else:
                                    upstream_name = upstream
                            else:
                                upstream_name = upstream
                            desc = f"🔄 Mirror of {upstream_name}"
                        else:
                            desc = "🔄 Mirror repository (from cache)"

                        # Add if not already in completions
                        if not any(c[0] == mirror_name for c in completions):
                            completions.append((mirror_name, desc))
                else:
                    # Just repo name
                    _, name_only = (
                        mirror_name.split("/") if "/" in mirror_name else ("", mirror_name)
                    )
                    if name_only.lower().startswith(repo_part.lower()):
                        upstream = mirror.get("upstream", "")
                        if upstream:
                            # Extract upstream name
                            if "github.com/" in upstream:
                                upstream_parts = upstream.split("github.com/")[-1].split("/")
                                if len(upstream_parts) >= 2:
                                    upstream_name = f"{upstream_parts[0]}/{upstream_parts[1]}"
                                else:
                                    upstream_name = upstream
                            else:
                                upstream_name = upstream
                            desc = f"🔄 Mirror of {upstream_name}"
                        else:
                            desc = "🔄 Mirror repository (from cache)"

                        # Add if not already in completions
                        if not any(c[0] == mirror_name for c in completions):
                            completions.append((mirror_name, desc))

        # Sort by repository name
        completions.sort(key=lambda x: x[0])

        # Limit to reasonable number
        return completions[:20]

    except GitHubError:
        # If we can't get repos, at least return cached mirrors
        try:
            config_manager = ConfigManager()
            recent_mirrors = config_manager.get_recent_mirrors()
            completions = []

            for mirror in recent_mirrors[:10]:
                mirror_name = mirror.get("name", "")
                if not mirror_name:
                    mirror_url = mirror.get("mirror", "")
                    if "github.com/" in mirror_url:
                        parts = mirror_url.split("github.com/")[-1].split("/")
                        if len(parts) >= 2:
                            mirror_name = f"{parts[0]}/{parts[1]}"

                if mirror_name:
                    # Check if matches based on whether incomplete has "/"
                    if "/" in incomplete:
                        # Full owner/repo format
                        if mirror_name.lower().startswith(incomplete.lower()):
                            completions.append((mirror_name, "🔄 Mirror repository (from cache)"))
                    else:
                        # Just repo name
                        _, name_only = (
                            mirror_name.split("/") if "/" in mirror_name else ("", mirror_name)
                        )
                        if name_only.lower().startswith(incomplete.lower()):
                            completions.append((mirror_name, "🔄 Mirror repository (from cache)"))

            return completions[:10]
        except Exception:
            return []
