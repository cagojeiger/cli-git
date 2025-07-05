"""GitHub Actions workflow generation for mirror synchronization."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def generate_sync_workflow(upstream_url: str, schedule: str, upstream_default_branch: str) -> str:
    """Generate GitHub Actions workflow for mirror synchronization.

    Args:
        upstream_url: URL of the upstream repository
        schedule: Cron schedule for synchronization
        upstream_default_branch: Default branch of the upstream repository

    Returns:
        YAML content for the workflow file
    """
    # Get the template directory path
    template_dir = Path(__file__).parent.parent / "templates"

    # Create Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Load the template
    template = env.get_template("mirror-sync.yml.j2")

    # Render the template with variables
    workflow_yaml = template.render(
        schedule=schedule,
        upstream_url=upstream_url,
        upstream_default_branch=upstream_default_branch,
    )

    return workflow_yaml
