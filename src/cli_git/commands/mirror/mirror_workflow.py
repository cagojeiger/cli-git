"""Workflow and UI functions for mirror operations."""

from datetime import UTC, datetime
from typing import Annotated

import typer

from cli_git.commands.mirror.mirror_command_options import MirrorCommandOptions
from cli_git.commands.mirror.mirror_operations import private_mirror_operation
from cli_git.commands.mirror.mirror_validation import (
    check_prerequisites,
    prepare_mirror_config,
    validate_mirror_inputs,
)
from cli_git.completion.completers import complete_organization, complete_prefix, complete_schedule
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError
from cli_git.utils.validators import ValidationError


def save_mirror_info(config_manager: ConfigManager, upstream: str, mirror_url: str) -> None:
    """Save mirror information to config.

    Args:
        config_manager: ConfigManager instance
        upstream: Upstream repository URL
        mirror_url: Created mirror repository URL
    """
    mirror_info = {
        "upstream": upstream,
        "mirror": mirror_url,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    config_manager.add_recent_mirror(mirror_info)


def display_success_message(mirror_url: str, no_sync: bool) -> None:
    """Display success message with next steps.

    Args:
        mirror_url: Created mirror repository URL
        no_sync: Whether automatic sync is disabled
    """
    typer.echo("\n✅ Success! Your private mirror is ready:")
    typer.echo(f"   {mirror_url}")
    typer.echo("\n📋 Next steps:")

    if no_sync:
        typer.echo("   - Manual sync is required (automatic sync disabled)")
    else:
        typer.echo("   - The mirror will sync daily at 00:00 UTC")
        typer.echo("   - To sync manually: Go to Actions → Mirror Sync → Run workflow")

    typer.echo(f"   - Clone your mirror: git clone {mirror_url}")


def private_mirror_command(
    upstream: Annotated[str, typer.Argument(help="Upstream repository URL")],
    repo: Annotated[str | None, typer.Option("--repo", "-r", help="Mirror repository name")] = None,
    org: Annotated[
        str | None,
        typer.Option(
            "--org", "-o", help="Target organization", autocompletion=complete_organization
        ),
    ] = None,
    prefix: Annotated[
        str | None,
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
    # Create options object for cleaner parameter passing
    options = MirrorCommandOptions.from_typer_args(upstream, repo, org, prefix, schedule, no_sync)

    # Step 1: Check prerequisites
    config_manager = check_prerequisites()

    # Step 2: Validate inputs
    try:
        validate_mirror_inputs(options.upstream, options.org, options.schedule, options.prefix)
    except ValidationError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e

    # Step 3: Prepare mirror configuration
    mirror_config = prepare_mirror_config(
        options.upstream,
        options.repo,
        options.prefix,
        options.org,
        options.schedule,
        options.no_sync,
        config_manager.get_config(),
    )

    typer.echo("\n🔄 Creating private mirror...")

    try:
        # Step 4: Perform mirror operation
        mirror_url = private_mirror_operation(mirror_config)

        # Step 5: Save mirror info
        save_mirror_info(config_manager, options.upstream, mirror_url)

        # Step 6: Display success message
        display_success_message(mirror_url, options.no_sync)

    except GitHubError as e:
        typer.echo(f"\n❌ Failed to create mirror: {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"\n❌ Unexpected error: {e}")
        raise typer.Exit(1) from e
