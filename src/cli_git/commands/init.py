"""Initialize user configuration for cli-git."""

from typing import Annotated

import typer

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError, check_gh_auth, get_current_username


def init_command(
    force: Annotated[bool, typer.Option("--force", "-f", help="Force reinitialization")] = False,
) -> None:
    """Initialize cli-git configuration with GitHub account information."""
    # Check gh CLI authentication first
    if not check_gh_auth():
        typer.echo("❌ GitHub CLI is not authenticated")
        typer.echo("   Please run: gh auth login")
        raise typer.Exit(1)

    # Get current GitHub username
    try:
        username = get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    # Initialize config manager
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Check if already initialized
    if config["github"]["username"] and not force:
        typer.echo("⚠️  Configuration already exists")
        typer.echo(f"   Current user: {config['github']['username']}")
        if config["github"]["default_org"]:
            typer.echo(f"   Default org: {config['github']['default_org']}")
        typer.echo("   Use --force to reinitialize")
        return

    # Ask for default organization
    default_org = typer.prompt("Default organization (optional)", default="")

    # Update configuration
    updates = {"github": {"username": username, "default_org": default_org}}
    config_manager.update_config(updates)

    # Success message
    typer.echo()
    typer.echo("✅ Configuration initialized successfully!")
    typer.echo(f"   GitHub username: {username}")
    if default_org:
        typer.echo(f"   Default organization: {default_org}")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("- Run 'cli-git info' to see your configuration")
    typer.echo("- Run 'cli-git private-mirror <repo-url>' to create your first mirror")
