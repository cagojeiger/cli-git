"""Workflow setup for private mirror functionality."""

from pathlib import Path

from cli_git.core.workflow import generate_sync_workflow
from cli_git.utils.gh import add_repo_secret


def create_workflow_file(
    repo_path: Path, upstream_url: str, schedule: str, upstream_branch: str
) -> Path:
    """Create sync workflow file in the repository.

    Args:
        repo_path: Path to the repository
        upstream_url: URL of the upstream repository
        schedule: Cron schedule for synchronization
        upstream_branch: Default branch of upstream repository

    Returns:
        Path to the created workflow file
    """
    workflow_dir = repo_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflow_content = generate_sync_workflow(upstream_url, schedule, upstream_branch)
    workflow_file = workflow_dir / "mirror-sync.yml"
    workflow_file.write_text(workflow_content)

    return workflow_file


def add_workflow_secrets(
    repo_full_name: str,
    upstream_url: str,
    upstream_branch: str,
    slack_url: str | None = None,
    github_token: str | None = None,
) -> None:
    """Add necessary secrets for workflow execution.

    Args:
        repo_full_name: Full repository name (owner/repo)
        upstream_url: URL of the upstream repository
        upstream_branch: Default branch of upstream repository
        slack_url: Slack webhook URL for notifications (optional)
        github_token: GitHub Personal Access Token for tag sync (optional)
    """
    # Add required secrets
    add_repo_secret(repo_full_name, "UPSTREAM_URL", upstream_url)
    add_repo_secret(repo_full_name, "UPSTREAM_DEFAULT_BRANCH", upstream_branch)

    # Add optional secrets
    if github_token:
        add_repo_secret(repo_full_name, "GH_TOKEN", github_token)

    if slack_url:
        add_repo_secret(repo_full_name, "SLACK_WEBHOOK_URL", slack_url)
