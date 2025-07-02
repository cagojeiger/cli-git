"""GitHub Actions workflow generation for mirror synchronization."""

from pathlib import Path


def generate_sync_workflow(upstream_url: str, schedule: str, upstream_default_branch: str) -> str:
    """Generate GitHub Actions workflow for mirror synchronization.

    Args:
        upstream_url: URL of the upstream repository
        schedule: Cron schedule for synchronization
        upstream_default_branch: Default branch of the upstream repository

    Returns:
        YAML content for the workflow file
    """
    # Load template
    template_path = Path(__file__).parent.parent / "templates" / "mirror-sync.yml"
    template_content = template_path.read_text()

    # Replace placeholders
    workflow_content = template_content.replace("{{ schedule }}", schedule)

    # Note: Other placeholders like secrets are handled by GitHub Actions at runtime
    # We don't need to replace them here

    return workflow_content
