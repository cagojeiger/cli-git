"""GitHub CLI (gh) utility functions."""

import subprocess
from typing import Optional

from cli_git.utils.git import extract_repo_info


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


def run_gh_auth_login() -> bool:
    """Run gh auth login interactively.

    Returns:
        True if login succeeded, False otherwise
    """
    try:
        result = subprocess.run(["gh", "auth", "login"], check=False)
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


def get_user_organizations() -> list[str]:
    """Get list of organizations the user belongs to.

    Returns:
        List of organization names

    Raises:
        GitHubError: If unable to fetch organizations
    """
    try:
        result = subprocess.run(
            ["gh", "api", "user/orgs", "-q", ".[].login"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Split by newlines and filter empty strings
        orgs = [org.strip() for org in result.stdout.strip().split("\n") if org.strip()]
        return orgs
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to get organizations: {e.stderr}")
    except FileNotFoundError:
        raise GitHubError("gh CLI not found. Please install GitHub CLI.")


def get_upstream_default_branch(upstream_url: str) -> str:
    """Get the default branch of an upstream repository.

    Args:
        upstream_url: URL of the upstream repository

    Returns:
        Name of the default branch

    Raises:
        GitHubError: If unable to fetch repository information
    """
    try:
        owner, repo = extract_repo_info(upstream_url)
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}", "-q", ".default_branch"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to get default branch: {e.stderr}")
    except ValueError as e:
        raise GitHubError(f"Invalid repository URL: {e}")
    except FileNotFoundError:
        raise GitHubError("gh CLI not found. Please install GitHub CLI.")


def validate_github_token(token: str) -> bool:
    """Validate a GitHub Personal Access Token.

    Args:
        token: GitHub Personal Access Token to validate

    Returns:
        True if token is valid, False otherwise
    """
    if not token:
        return False

    try:
        # Use the token to make a simple API call
        result = subprocess.run(
            ["gh", "api", "user", "-H", f"Authorization: token {token}"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def mask_token(token: str) -> str:
    """Mask a GitHub token for display.

    Args:
        token: GitHub token to mask

    Returns:
        Masked token for display
    """
    if not token:
        return ""

    # GitHub tokens typically start with 'ghp_' or 'github_pat_'
    if len(token) <= 8:
        return "***"

    # Show first 4 and last 4 characters
    return f"{token[:4]}...{token[-4:]}"
