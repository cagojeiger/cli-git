"""Create a private mirror of a public repository."""

import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Optional

import typer

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


def private_mirror_operation(
    upstream_url: str,
    target_name: str,
    username: str,
    org: Optional[str] = None,
    schedule: str = "0 0 * * *",
    no_sync: bool = False,
) -> str:
    """Perform the private mirror operation.

    Args:
        upstream_url: URL of the upstream repository
        target_name: Name for the mirror repository
        username: GitHub username
        org: Organization name (optional)
        schedule: Cron schedule for synchronization
        no_sync: Skip automatic synchronization setup

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
            run_git_command('commit -m "Add automatic mirror sync workflow"')
            run_git_command("push origin main")

            # Add secret
            repo_full_name = f"{org or username}/{target_name}"
            add_repo_secret(repo_full_name, "UPSTREAM_URL", upstream_url)

    return mirror_url


def private_mirror_command(
    upstream: Annotated[str, typer.Argument(help="Upstream repository URL")],
    repo: Annotated[
        Optional[str], typer.Option("--repo", "-r", help="Mirror repository name")
    ] = None,
    org: Annotated[Optional[str], typer.Option("--org", "-o", help="Target organization")] = None,
    schedule: Annotated[
        str, typer.Option("--schedule", "-s", help="Sync schedule (cron format)")
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

    # Extract repository information
    try:
        _, repo_name = extract_repo_info(upstream)
    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    # Determine target repository name
    target_name = repo or f"{repo_name}-mirror"

    # Use default org from config if not specified
    if not org and config["github"]["default_org"]:
        org = config["github"]["default_org"]

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
