"""GitHub CLI (gh) utility functions."""

import subprocess
from typing import Optional


class GitHubError(Exception):
    """Custom exception for GitHub-related errors."""

    pass


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    try:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_current_username() -> str:
    """Get current GitHub username using gh CLI.

    Returns:
        GitHub username

    Raises:
        GitHubError: If unable to get username
    """
    try:
        result = subprocess.run(
            ["gh", "api", "user", "-q", ".login"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to get current user: {e.stderr}")
    except FileNotFoundError:
        raise GitHubError("gh CLI not found. Please install GitHub CLI.")


def create_private_repo(
    name: str, description: Optional[str] = None, org: Optional[str] = None
) -> str:
    """Create a private GitHub repository.

    Args:
        name: Repository name
        description: Repository description
        org: Organization name (optional)

    Returns:
        Repository URL

    Raises:
        GitHubError: If repository creation fails
    """
    # Construct repository name
    repo_name = f"{org}/{name}" if org else name

    # Build command
    cmd = ["gh", "repo", "create", repo_name, "--private"]
    if description:
        cmd.extend(["--description", description])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if "Validation Failed" in e.stderr or "already exists" in e.stderr:
            raise GitHubError(f"Repository '{repo_name}' already exists")
        raise GitHubError(f"Failed to create repository: {e.stderr}")


def add_repo_secret(repo: str, name: str, value: str) -> None:
    """Add a secret to a GitHub repository.

    Args:
        repo: Repository name (owner/repo)
        name: Secret name
        value: Secret value

    Raises:
        GitHubError: If adding secret fails
    """
    cmd = ["gh", "secret", "set", name, "--repo", repo]

    try:
        subprocess.run(cmd, input=value, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to set secret '{name}': {e.stderr}")
