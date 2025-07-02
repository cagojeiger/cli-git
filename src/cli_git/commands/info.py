"""Display current cli-git configuration and status."""

import json
from typing import Annotated

import typer

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import check_gh_auth, mask_token


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
    github_token = config["github"].get("github_token", "")
    slack_webhook_url = config["github"].get("slack_webhook_url", "")
    default_prefix = config["preferences"].get("default_prefix", "mirror-")

    if json_output:
        # JSON output
        output = {
            "github": {
                "username": config["github"]["username"],
                "default_org": config["github"]["default_org"],
                "authenticated": is_authenticated,
                "github_token_set": bool(github_token),
                "github_token": mask_token(github_token) if github_token else "",
                "slack_webhook_set": bool(slack_webhook_url),
                "slack_webhook": slack_webhook_url[:30] + "..." if slack_webhook_url else "",
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
        typer.echo(f"  Username: {username}")
        typer.echo(f"  Default organization: {default_org}")
        typer.echo(
            f"  gh CLI status: {'✅ Authenticated' if is_authenticated else '❌ Not authenticated'}"
        )

        # Token information
        if github_token:
            typer.echo(f"  GitHub token: ✅ Set ({mask_token(github_token)})")
        else:
            typer.echo("  GitHub token: ❌ Not set")

        if slack_webhook_url:
            masked_webhook = (
                f"{slack_webhook_url[:30]}...{slack_webhook_url[-10:]}"
                if len(slack_webhook_url) > 40
                else slack_webhook_url
            )
            typer.echo(f"  Slack webhook: ✅ Set ({masked_webhook})")
        else:
            typer.echo("  Slack webhook: ❌ Not set")

        typer.echo()

        # Preferences
        typer.echo("Preferences:")
        typer.echo(f"  Default sync schedule: {config['preferences']['default_schedule']}")
        typer.echo(f"  Default prefix: {default_prefix}")
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
        elif not github_token and recent_mirrors:
            typer.echo("💡 Run 'cli-git init' to add a GitHub token for better tag synchronization")
            typer.echo("   Then run 'cli-git update-mirrors --all' to update existing mirrors")
