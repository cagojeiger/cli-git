"""GitHub-related utility functions."""


def extract_repo_name_from_url(url: str) -> str | None:
    """Extract repository name from GitHub URL.

    Args:
        url: GitHub repository URL (any format)

    Returns:
        Repository name in "owner/repo" format, or None if parsing fails

    Examples:
        >>> extract_repo_name_from_url("https://github.com/owner/repo")
        "owner/repo"
        >>> extract_repo_name_from_url("git@github.com:owner/repo.git")
        "owner/repo"
        >>> extract_repo_name_from_url("invalid-url")
        None
    """
    if not url or "github.com/" not in url:
        return None

    try:
        # Extract the part after github.com/
        parts = url.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            owner = parts[0].rstrip(":")  # Remove colon from SSH URLs
            repo = parts[1].rstrip(".git")  # Remove .git suffix
            return f"{owner}/{repo}"
    except (IndexError, AttributeError):
        pass

    return None


def format_repo_description(upstream_url: str, description: str = "") -> str:
    """Format repository description for display.

    Args:
        upstream_url: Upstream repository URL
        description: Optional repository description

    Returns:
        Formatted description string with mirror emoji
    """
    if upstream_url:
        repo_name = extract_repo_name_from_url(upstream_url)
        if repo_name:
            return f"🔄 Mirror of {repo_name}"
        else:
            return f"🔄 Mirror of {upstream_url}"
    elif description:
        return f"🔄 {description}"
    else:
        return "🔄 Mirror repository"
