"""Create a private mirror of a public repository."""

import os
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
)
from cli_git.utils.git import extract_repo_info, run_git_command
from cli_git.utils.validators import (
    ValidationError,
    validate_cron_schedule,
    validate_github_url,
    validate_organization,
    validate_prefix,
    validate_repository_name,
)


def disable_original_workflows(repo_path: Path) -> bool:
    """Disable original workflows by moving them to workflows-disabled.

    Args:
        repo_path: Path to the repository

    Returns:
        True if workflows were disabled, False if no workflows found
    """
    workflows_dir = repo_path / ".github" / "workflows"

    # Check if workflows directory exists
    if not workflows_dir.exists():
        return False

    # Find workflow files
    yml_files = list(workflows_dir.glob("*.yml"))
    yaml_files = list(workflows_dir.glob("*.yaml"))
    workflow_files = yml_files + yaml_files

    # No workflows to disable
    if not workflow_files:
        return False

    # Create disabled directory
    disabled_dir = repo_path / ".github" / "workflows-disabled"
    disabled_dir.mkdir(parents=True, exist_ok=True)

    # Move workflow files
    try:
        for workflow_file in workflow_files:
            target = disabled_dir / workflow_file.name
            workflow_file.rename(target)

        # Create README
        readme_content = """# Disabled Workflows
These workflows were automatically disabled during mirror creation.
Original workflows from the upstream repository are preserved here for reference.
"""
        (disabled_dir / "README.md").write_text(readme_content)

        return True
    except Exception:
        # If any error occurs, try to continue
        # The mirror is more important than disabling workflows
        return False


def private_mirror_operation(
    upstream_url: str,
    target_name: str,
    username: str,
    org: Optional[str] = None,
    schedule: str = "0 0 * * *",
    no_sync: bool = False,
    slack_webhook_url: Optional[str] = None,
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

        # Disable original workflows
        typer.echo("  ✓ Disabling original workflows")
        workflows_disabled = disable_original_workflows(repo_path)

        # Commit the workflow changes if any were disabled
        if workflows_disabled:
            run_git_command("add .")
            run_git_command('commit -m "Disable original workflows"')

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
            # Create workflow file
            typer.echo(f"  ✓ Setting up automatic sync ({schedule})")
            workflow_dir = repo_path / ".github" / "workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)

            workflow_content = generate_sync_workflow(upstream_url, schedule)
            workflow_file = workflow_dir / "mirror-sync.yml"
            workflow_file.write_text(workflow_content)

            # Commit and push workflow
            run_git_command("add .github/workflows/mirror-sync.yml")
            # workflows_disabled already committed separately, so always use simple message
            commit_msg = "Add automatic mirror sync workflow"
            run_git_command(f'commit -m "{commit_msg}"')
            run_git_command("push origin main")

            # Add secrets
            repo_full_name = f"{org or username}/{target_name}"
            add_repo_secret(repo_full_name, "UPSTREAM_URL", upstream_url)

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
