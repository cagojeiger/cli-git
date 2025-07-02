"""Mirror repository scanning functionality."""

import base64
import json
import subprocess
from typing import Dict, List, Optional

import typer


def scan_for_mirrors(
    username: str, org: Optional[str] = None, prefix: Optional[str] = None
) -> List[Dict[str, str]]:
    """Scan GitHub for mirror repositories.

    Args:
        username: GitHub username
        org: Organization name (optional)
        prefix: Repository name prefix to filter by (optional, deprecated)

    Returns:
        List of mirror dictionaries
    """
    mirrors = []
    owners = [username]
    if org:
        owners.append(org)

    for owner in owners:
        typer.echo(f"  Scanning {owner}...")

        # Get repositories
        repos = _get_repositories(owner, prefix)
        if not repos:
            continue

        # Check each repository
        found = 0
        for repo in repos:
            if _is_mirror_repo(repo.get("fullName", repo.get("nameWithOwner", ""))):
                found += 1
                mirror_info = _extract_mirror_info(repo)
                mirrors.append(mirror_info)

        typer.echo(f"    ✓ Found {found} mirrors out of {len(repos)} repositories")

    return mirrors


def _get_repositories(owner: str, prefix: Optional[str] = None) -> List[Dict]:
    """Get repositories for an owner, optionally filtered by prefix.

    Args:
        owner: Repository owner
        prefix: Optional prefix filter

    Returns:
        List of repository data
    """
    if prefix:
        # Use search with prefix
        cmd = [
            "gh",
            "search",
            "repos",
            f"{prefix} in:name",
            "--owner",
            owner,
            "--limit",
            "100",
            "--json",
            "fullName,url,description,isPrivate,updatedAt",
        ]
    else:
        # List all repos
        cmd = [
            "gh",
            "repo",
            "list",
            owner,
            "--limit",
            "1000",
            "--json",
            "fullName,url,description,isPrivate,updatedAt",
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        typer.echo(f"    ⚠️  Failed to list {owner}'s repositories")
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        typer.echo("    ⚠️  Failed to parse repository data")
        return []


def _is_mirror_repo(repo_name: str) -> bool:
    """Check if a repository is a mirror by looking for mirror-sync.yml.

    Args:
        repo_name: Full repository name (owner/repo)

    Returns:
        True if repository has mirror-sync.yml
    """
    result = subprocess.run(
        ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
        capture_output=True,
    )
    return result.returncode == 0


def _extract_mirror_info(repo_data: Dict) -> Dict[str, str]:
    """Extract mirror information from repository data.

    Args:
        repo_data: Repository data from GitHub API

    Returns:
        Mirror information dictionary
    """
    repo_name = repo_data.get("fullName", repo_data.get("nameWithOwner", ""))

    # Try to get upstream URL from workflow
    upstream = _get_upstream_from_workflow(repo_name)

    return {
        "name": repo_name,
        "mirror": repo_data["url"],
        "upstream": upstream,
        "description": repo_data.get("description", ""),
        "is_private": repo_data.get("isPrivate", False),
        "updated_at": repo_data.get("updatedAt", ""),
    }


def _get_upstream_from_workflow(repo_name: str) -> str:
    """Try to extract upstream URL from workflow file.

    Args:
        repo_name: Full repository name (owner/repo)

    Returns:
        Upstream URL or empty string
    """
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml",
            "-q",
            ".content",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return ""

    try:
        content = base64.b64decode(result.stdout.strip()).decode()

        # Look for upstream URL in comments
        for line in content.split("\n"):
            if "UPSTREAM_URL:" in line and "#" in line:
                comment_part = line.split("#", 1)[1].strip()
                if "UPSTREAM_URL:" in comment_part:
                    return comment_part.split("UPSTREAM_URL:", 1)[1].strip()
    except Exception:
        pass

    return ""
