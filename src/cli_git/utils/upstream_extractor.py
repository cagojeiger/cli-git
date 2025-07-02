"""Upstream URL extraction and formatting utilities."""

from typing import Optional


def extract_upstream_name(upstream_url: str) -> str:
    """Extract clean upstream repository name from URL.

    Args:
        upstream_url: Full upstream repository URL

    Returns:
        Clean repository name in "owner/repo" format, or original URL if parsing fails
    """
    if not upstream_url:
        return ""

    if "github.com/" in upstream_url:
        try:
            # Extract from URLs like https://github.com/owner/repo or git@github.com:owner/repo
            parts = upstream_url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                owner = parts[0].rstrip(":")  # Remove colon from SSH URLs
                repo = parts[1].rstrip(".git")  # Remove .git suffix
                return f"{owner}/{repo}"
        except (IndexError, AttributeError):
            pass

    return upstream_url


def extract_repo_name_from_url(mirror_url: str) -> Optional[str]:
    """Extract repository name from mirror URL.

    Args:
        mirror_url: Mirror repository URL

    Returns:
        Repository name in "owner/repo" format, or None if parsing fails
    """
    if not mirror_url or "github.com/" not in mirror_url:
        return None

    try:
        parts = mirror_url.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1].rstrip(".git")
            return f"{owner}/{repo}"
    except (IndexError, AttributeError):
        pass

    return None


def format_mirror_description(
    upstream_url: str, fallback_description: str = "Mirror repository"
) -> str:
    """Format description for mirror repository.

    Args:
        upstream_url: Upstream repository URL
        fallback_description: Description to use if upstream is empty

    Returns:
        Formatted description with mirror emoji
    """
    if upstream_url:
        upstream_name = extract_upstream_name(upstream_url)
        return f"🔄 Mirror of {upstream_name}"
    else:
        return f"🔄 {fallback_description}"


def get_mirror_description_from_cache(mirror_data: dict) -> str:
    """Get formatted description from cached mirror data.

    Args:
        mirror_data: Mirror data dictionary from cache

    Returns:
        Formatted description string
    """
    upstream = mirror_data.get("upstream", "")
    description = mirror_data.get("description", "")

    if upstream:
        return format_mirror_description(upstream)
    elif description:
        return f"🔄 {description}"
    else:
        return "🔄 Mirror repository"
