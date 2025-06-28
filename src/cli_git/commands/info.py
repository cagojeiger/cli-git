"""Display current cli-git configuration and status."""

import json
from typing import Annotated

import typer

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import check_gh_auth


def info_command(
    json_output: Annotated[bool, typer.Option("--json", help="Output in JSON format")] = False,
) -> None:
    """Display current configuration and recent mirrors."""
    # Initialize config manager
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Check gh authentication status
    is_authenticated = check_gh_auth()

    # Get recent mirrors
    recent_mirrors = config_manager.get_recent_mirrors()

    # Prepare data
    username = config["github"]["username"] or "(not set)"
    default_org = config["github"]["default_org"] or "(not set)"

    if json_output:
        # JSON output
        output = {
            "github": {
                "username": config["github"]["username"],
                "default_org": config["github"]["default_org"],
                "authenticated": is_authenticated,
            },
            "preferences": config["preferences"],
            "recent_mirrors": recent_mirrors,
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        # Human-readable output
        typer.echo("📋 CLI-Git Configuration")
        typer.echo("=" * 40)
        typer.echo()

        # GitHub information
        typer.echo("GitHub Account:")
        typer.echo(f"  GitHub username: {username}")
        typer.echo(f"  Default organization: {default_org}")
        typer.echo(
            f"  gh CLI status: {'✅ Authenticated' if is_authenticated else '❌ Not authenticated'}"
        )
        typer.echo()

        # Preferences
        typer.echo("Preferences:")
        typer.echo(f"  Default sync schedule: {config['preferences']['default_schedule']}")
        typer.echo()

        # Recent mirrors
        if recent_mirrors:
            typer.echo("Recent Mirrors:")
            for mirror in recent_mirrors[:5]:  # Show max 5
                # Extract repo name from URL
                mirror_name = mirror["mirror"].split("/")[-1]
                upstream_parts = mirror["upstream"].split("/")
                upstream_name = f"{upstream_parts[-2]}/{upstream_parts[-1]}"
                typer.echo(f"  • {mirror_name} ← {upstream_name}")
            if len(recent_mirrors) > 5:
                typer.echo(f"  ... and {len(recent_mirrors) - 5} more")
        else:
            typer.echo("Recent Mirrors: None")

        typer.echo()

        # Next steps
        if not config["github"]["username"]:
            typer.echo("💡 Run 'cli-git init' to configure your GitHub account")
