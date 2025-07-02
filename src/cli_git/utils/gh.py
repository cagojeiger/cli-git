"""GitHub CLI (gh) utility functions."""

import subprocess

from cli_git.utils.git import extract_repo_info


class GitHubError(Exception):
    """Custom exception for GitHub-related errors."""

    pass


def run_gh_command(
    args: list[str],
    check: bool = True,
    capture_output: bool = True,
    interactive: bool = False,
) -> subprocess.CompletedProcess:
    """Run a gh CLI command with common error handling.

    Args:
        args: Command arguments (without 'gh' prefix)
        check: Whether to check return code
        capture_output: Whether to capture output
        interactive: Whether to run interactively (no capture)

    Returns:
        CompletedProcess instance

    Raises:
        GitHubError: If command fails and check=True
        FileNotFoundError: If gh CLI is not found
    """
    cmd = ["gh"] + args

    try:
        if interactive:
            return subprocess.run(cmd, check=check)
        else:
            return subprocess.run(cmd, capture_output=capture_output, text=True, check=check)
    except subprocess.CalledProcessError as e:
        stderr = getattr(e, "stderr", "") or ""
        raise GitHubError(f"gh command failed: {stderr}") from e
    except FileNotFoundError as e:
        raise GitHubError("gh CLI not found. Please install GitHub CLI.") from e


def check_gh_auth() -> bool:
    """Check if gh CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    try:
        result = run_gh_command(["auth", "status"], check=False)
        return result.returncode == 0
    except GitHubError:
        return False


def run_gh_auth_login() -> bool:
    """Run gh auth login interactively.

    Returns:
        True if login succeeded, False otherwise
    """
    try:
        result = run_gh_command(["auth", "login"], check=False, interactive=True)
        return result.returncode == 0
    except GitHubError:
        return False


def get_current_username() -> str:
    """Get current GitHub username using gh CLI.

    Returns:
        GitHub username

    Raises:
        GitHubError: If unable to get username
    """
    result = run_gh_command(["api", "user", "-q", ".login"])
    return result.stdout.strip()


def create_private_repo(name: str, description: str | None = None, org: str | None = None) -> str:
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
    args = ["repo", "create", repo_name, "--private"]
    if description:
        args.extend(["--description", description])

    try:
        result = run_gh_command(args)
        return result.stdout.strip()
    except GitHubError as e:
        error_msg = str(e)
        if "Validation Failed" in error_msg or "already exists" in error_msg:
            raise GitHubError(f"Repository '{repo_name}' already exists") from e
        raise GitHubError(f"Failed to create repository: {error_msg}") from e


def add_repo_secret(repo: str, name: str, value: str) -> None:
    """Add a secret to a GitHub repository.

    Args:
        repo: Repository name (owner/repo)
        name: Secret name
        value: Secret value

    Raises:
        GitHubError: If adding secret fails
    """
    args = ["secret", "set", name, "--repo", repo]

    try:
        # Special handling for input
        cmd = ["gh"] + args
        subprocess.run(cmd, input=value, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        stderr = getattr(e, "stderr", "") or ""
        raise GitHubError(f"Failed to set secret '{name}': {stderr}") from e


def get_user_organizations() -> list[str]:
    """Get list of organizations the user belongs to.

    Returns:
        List of organization names

    Raises:
        GitHubError: If unable to fetch organizations
    """
    result = run_gh_command(["api", "user/orgs", "-q", ".[].login"])
    # Split by newlines and filter empty strings
    orgs = [org.strip() for org in result.stdout.strip().split("\n") if org.strip()]
    return orgs


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
        result = run_gh_command(["api", f"repos/{owner}/{repo}", "-q", ".default_branch"])
        return result.stdout.strip()
    except ValueError as e:
        raise GitHubError(f"Invalid repository URL: {e}") from e


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
        # Special case: need to pass header directly
        cmd = ["gh", "api", "user", "-H", f"Authorization: token {token}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
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
