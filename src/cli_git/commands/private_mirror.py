"""Create a private mirror of a public repository."""

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Optional

import typer

from cli_git.completion.completers import complete_organization, complete_prefix, complete_schedule
from cli_git.core.workflow import generate_sync_workflow
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import (
    GitHubError,
    add_repo_secret,
    check_gh_auth,
    create_private_repo,
    get_current_username,
    get_upstream_default_branch,
)
from cli_git.utils.git import extract_repo_info, get_default_branch, run_git_command
from cli_git.utils.validators import (
    ValidationError,
    validate_cron_schedule,
    validate_github_url,
    validate_organization,
    validate_prefix,
    validate_repository_name,
)


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


def private_mirror_operation(
    upstream_url: str,
    target_name: str,
    username: str,
    org: Optional[str] = None,
    schedule: str = "0 0 * * *",
    no_sync: bool = False,
    slack_webhook_url: Optional[str] = None,
    github_token: Optional[str] = None,
) -> str:
    """Perform the private mirror operation.

    Args:
        upstream_url: URL of the upstream repository
        target_name: Name for the mirror repository
        username: GitHub username
        org: Organization name (optional)
        schedule: Cron schedule for synchronization
        no_sync: Skip automatic synchronization setup
        slack_webhook_url: Slack webhook URL for notifications (optional)
        github_token: GitHub Personal Access Token for tag sync (optional)

    Returns:
        URL of the created mirror repository
    """
    with TemporaryDirectory() as temp_dir:
        # Clone the repository
        repo_path = Path(temp_dir) / target_name
        typer.echo("  ✓ Cloning repository")
        run_git_command(f"clone {upstream_url} {repo_path}")

        # Change to repo directory
        os.chdir(repo_path)

        # Clean .github directory
        typer.echo("  ✓ Removing original .github directory")
        github_cleaned = clean_github_directory(repo_path)

        # Commit the changes if .github was removed
        if github_cleaned:
            run_git_command("add -A")
            run_git_command('commit -m "Remove original .github directory"')

        # Create private repository
        typer.echo(f"  ✓ Creating private repository: {org or username}/{target_name}")
        mirror_url = create_private_repo(target_name, org=org)

        # Update remotes
        run_git_command("remote rename origin upstream")
        run_git_command(f"remote add origin {mirror_url}")

        # Push all branches and tags
        typer.echo("  ✓ Pushing branches and tags")
        run_git_command("push origin --all")
        run_git_command("push origin --tags")

        if not no_sync:
            # Get upstream default branch
            typer.echo("  ✓ Getting upstream default branch")
            upstream_default_branch = get_upstream_default_branch(upstream_url)

            # Create workflow file
            typer.echo(f"  ✓ Setting up automatic sync ({schedule})")
            workflow_dir = repo_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)

            workflow_content = generate_sync_workflow(
                upstream_url, schedule, upstream_default_branch
            )
            workflow_file = workflow_dir / "mirror-sync.yml"
            workflow_file.write_text(workflow_content)

            # Commit and push workflow
            run_git_command("add .github/workflows/mirror-sync.yml")
            # Commit message for sync workflow
            commit_msg = "Add automatic mirror sync workflow"
            run_git_command(f'commit -m "{commit_msg}"')

            # Get the default branch and push to it
            try:
                default_branch = get_default_branch(repo_path)
                run_git_command(f"push origin {default_branch}")
            except subprocess.CalledProcessError:
                # Fallback to common branch names if detection fails
                for branch in ["main", "master"]:
                    try:
                        run_git_command(f"push origin {branch}")
                        break
                    except subprocess.CalledProcessError:
                        continue
                else:
                    # If all fails, just push current branch
                    run_git_command("push origin HEAD")

            # Add secrets
            repo_full_name = f"{org or username}/{target_name}"
            add_repo_secret(repo_full_name, "UPSTREAM_URL", upstream_url)
            add_repo_secret(repo_full_name, "UPSTREAM_DEFAULT_BRANCH", upstream_default_branch)

            # Add GitHub token if available
            if github_token:
                add_repo_secret(repo_full_name, "GH_TOKEN", github_token)
                typer.echo("  ✓ GitHub token added for tag synchronization")
            else:
                typer.echo(
                    "  ⚠️  No GitHub token provided. Tag sync may fail if tags contain workflow files."
                )

            # Add Slack webhook secret if provided
            if slack_webhook_url:
                add_repo_secret(repo_full_name, "SLACK_WEBHOOK_URL", slack_webhook_url)

    return mirror_url


def private_mirror_command(
    upstream: Annotated[str, typer.Argument(help="Upstream repository URL")],
    repo: Annotated[
        Optional[str], typer.Option("--repo", "-r", help="Mirror repository name")
    ] = None,
    org: Annotated[
        Optional[str],
        typer.Option(
            "--org", "-o", help="Target organization", autocompletion=complete_organization
        ),
    ] = None,
    prefix: Annotated[
        Optional[str],
        typer.Option("--prefix", "-p", help="Mirror name prefix", autocompletion=complete_prefix),
    ] = None,
    schedule: Annotated[
        str,
        typer.Option(
            "--schedule", "-s", help="Sync schedule (cron format)", autocompletion=complete_schedule
        ),
    ] = "0 0 * * *",
    no_sync: Annotated[
        bool, typer.Option("--no-sync", help="Disable automatic synchronization")
    ] = False,
) -> None:
    """Create a private mirror of a public repository with auto-sync."""
    # Check prerequisites
    if not check_gh_auth():
        typer.echo("❌ GitHub CLI is not authenticated")
        typer.echo("   Please run: gh auth login")
        raise typer.Exit(1)

    # Check configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()

    if not config["github"]["username"]:
        typer.echo("❌ Configuration not initialized")
        typer.echo("   Run 'cli-git init' first")
        raise typer.Exit(1)

    # Validate inputs
    try:
        # Validate upstream URL
        validate_github_url(upstream)

        # Validate organization if provided
        if org:
            validate_organization(org)

        # Validate schedule
        validate_cron_schedule(schedule)

        # Validate prefix if provided
        if prefix is not None:
            validate_prefix(prefix)

    except ValidationError as e:
        typer.echo(str(e))
        raise typer.Exit(1)

    # Extract repository information
    try:
        _, repo_name = extract_repo_info(upstream)
    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    # Get default prefix from config if not specified
    if prefix is None:
        prefix = config["preferences"].get("default_prefix", "mirror-")

    # Determine target repository name
    if repo:
        target_name = repo  # Custom name overrides prefix
    else:
        target_name = f"{prefix}{repo_name}" if prefix else repo_name

    # Validate the final repository name
    try:
        validate_repository_name(target_name)
    except ValidationError as e:
        typer.echo(str(e))
        raise typer.Exit(1)

    # Use default org from config if not specified
    if not org and config["github"]["default_org"]:
        org = config["github"]["default_org"]

    # Get Slack webhook URL from config
    slack_webhook_url = config["github"].get("slack_webhook_url", "")

    # Get GitHub token from config
    github_token = config["github"].get("github_token", "")

    # Get current username
    try:
        username = get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    typer.echo("\n🔄 Creating private mirror...")

    try:
        # Perform the mirror operation
        mirror_url = private_mirror_operation(
            upstream_url=upstream,
            target_name=target_name,
            username=username,
            org=org,
            schedule=schedule,
            no_sync=no_sync,
            slack_webhook_url=slack_webhook_url,
            github_token=github_token,
        )

        # Save to recent mirrors
        mirror_info = {
            "upstream": upstream,
            "mirror": mirror_url,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        config_manager.add_recent_mirror(mirror_info)

        # Success message
        typer.echo("\n✅ Success! Your private mirror is ready:")
        typer.echo(f"   {mirror_url}")
        typer.echo("\n📋 Next steps:")

        if no_sync:
            typer.echo("   - Manual sync is required (automatic sync disabled)")
        else:
            typer.echo("   - The mirror will sync daily at 00:00 UTC")
            typer.echo("   - To sync manually: Go to Actions → Mirror Sync → Run workflow")

        typer.echo(f"   - Clone your mirror: git clone {mirror_url}")

    except GitHubError as e:
        typer.echo(f"\n❌ Failed to create mirror: {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"\n❌ Unexpected error: {e}")
        raise typer.Exit(1)
