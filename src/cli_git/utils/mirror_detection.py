"""Mirror repository detection utilities."""

import subprocess
from typing import Any, Dict


def is_mirror_repository(repo_name: str) -> bool:
    """Check if a repository is a mirror by looking for workflow file.

    Args:
        repo_name: Repository name in "owner/repo" format

    Returns:
        True if repository has mirror-sync.yml workflow
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def check_mirror_workflow_exists(repo_name: str) -> bool:
    """Alias for is_mirror_repository for backward compatibility."""
    return is_mirror_repository(repo_name)


def extract_mirror_info_from_repo_data(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant mirror information from repository data.

    Args:
        repo_data: Repository data from GitHub API

    Returns:
        Dictionary with mirror-relevant fields
    """
    return {
        "nameWithOwner": repo_data.get("nameWithOwner", ""),
        "description": repo_data.get("description", ""),
        "is_mirror": repo_data.get("is_mirror", False),
        "updatedAt": repo_data.get("updatedAt", ""),
        "isArchived": repo_data.get("isArchived", False),
    }
