"""Core operations for mirror functionality."""

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import typer

from cli_git.commands.git_operations import (
    clone_repository,
    commit_changes,
    push_to_mirror,
    push_workflow_branch,
    setup_remotes,
)
from cli_git.commands.mirror.mirror_config import MirrorConfig
from cli_git.commands.workflow_setup import add_workflow_secrets, create_workflow_file


def clean_github_directory(repo_path: Path) -> bool:
    """Remove the entire .github directory from the repository.

    Args:
        repo_path: Path to the repository

    Returns:
        True if .github directory was removed, False if not found
    """
    github_dir = repo_path / ".github"

    # Check if .github directory exists
    if not github_dir.exists():
        return False

    # Remove entire .github directory
    try:
        shutil.rmtree(github_dir)
        return True
    except (OSError, PermissionError) as e:
        # Log specific error but continue
        # The mirror is more important than cleaning .github
        import sys

        print(f"Warning: Failed to remove .github directory: {e}", file=sys.stderr)
        return False


def setup_mirror_sync(
    repo_path: Path,
    repo_full_name: str,
    upstream_url: str,
    schedule: str,
    slack_webhook_url: str | None = None,
    github_token: str | None = None,
) -> None:
    """Setup automatic synchronization for mirror repository.

    Args:
        repo_path: Path to the repository
        repo_full_name: Full repository name (owner/repo)
        upstream_url: URL of the upstream repository
        schedule: Cron schedule for synchronization
        slack_webhook_url: Slack webhook URL for notifications (optional)
        github_token: GitHub Personal Access Token for tag sync (optional)
    """
    # Get upstream default branch
    typer.echo("  ✓ Getting upstream default branch")
    from cli_git.core.services import GitHubService

    upstream_default_branch = GitHubService.get_upstream_branch(upstream_url)

    # Create workflow file
    typer.echo(f"  ✓ Setting up automatic sync ({schedule})")
    create_workflow_file(repo_path, upstream_url, schedule, upstream_default_branch)

    # Commit and push workflow
    commit_changes(repo_path, "Add automatic mirror sync workflow")
    push_workflow_branch(repo_path)

    # Add secrets
    add_workflow_secrets(
        repo_full_name,
        upstream_url,
        upstream_default_branch,
        slack_webhook_url,
        github_token,
    )

    # Show token status
    if github_token:
        typer.echo("  ✓ GitHub token added for tag synchronization")
    else:
        typer.echo(
            "  ⚠️  No GitHub token provided. Tag sync may fail if tags contain workflow files."
        )


def private_mirror_operation(config: MirrorConfig) -> str:
    """Perform the private mirror operation.

    Args:
        config: MirrorConfig with all operation parameters

    Returns:
        URL of the created mirror repository

    Raises:
        GitHubError: If mirror operation fails
    """
    with TemporaryDirectory() as temp_dir:
        # Clone the repository
        repo_path = Path(temp_dir) / config.target_name
        typer.echo("  ✓ Cloning repository")
        clone_repository(config.upstream_url, repo_path)

        # Change to repo directory
        os.chdir(repo_path)

        # Clean .github directory
        typer.echo("  ✓ Removing original .github directory")
        github_cleaned = clean_github_directory(repo_path)

        # Commit the changes if .github was removed
        if github_cleaned:
            commit_changes(repo_path, "Remove original .github directory")

        # Create private repository
        typer.echo(
            f"  ✓ Creating private repository: {config.org or config.username}/{config.target_name}"
        )
        from cli_git.core.services import GitHubService

        mirror_url = GitHubService.create_repository(config.target_name, org=config.org)

        # Setup remotes
        setup_remotes(repo_path, mirror_url)

        # Push all branches and tags
        typer.echo("  ✓ Pushing branches and tags")
        push_to_mirror(repo_path)

        # Setup automatic sync if not disabled
        if not config.no_sync:
            repo_full_name = f"{config.org or config.username}/{config.target_name}"
            setup_mirror_sync(
                repo_path,
                repo_full_name,
                config.upstream_url,
                config.schedule,
                config.slack_webhook_url,
                config.github_token,
            )

    return mirror_url
