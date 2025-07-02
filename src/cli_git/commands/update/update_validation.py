"""Validation and preprocessing functions for update operations."""

import typer

from cli_git.commands.modules.interactive import select_mirrors_interactive
from cli_git.commands.modules.scan import scan_for_mirrors
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import GitHubError


def check_update_prerequisites():
    """Check prerequisites for mirror update.

    Returns:
        Tuple of (config_manager, config, username)

    Raises:
        typer.Exit: If prerequisites are not met
    """
    # Import from parent module to ensure test patches work
    from .. import update_mirrors

    # Direct check for compatibility with existing tests
    if not update_mirrors.check_gh_auth():
        typer.echo("❌ GitHub CLI is not authenticated")
        typer.echo("   Please run: gh auth login")
        raise typer.Exit(1)

    config_manager = update_mirrors.ConfigManager()
    config = config_manager.get_config()

    github_token = config["github"].get("github_token", "")
    if not github_token:
        typer.echo("⚠️  No GitHub token found in configuration")
        typer.echo("   Run 'cli-git init' to add a GitHub token")
        typer.echo("   Continuing without GH_TOKEN (tag sync may fail)...")

    try:
        username = update_mirrors.get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from e

    return config_manager, config, username


def handle_scan_option(
    config_manager: ConfigManager, config: dict, username: str, verbose: bool
) -> None:
    """Handle the --scan option to display mirrors without updating."""
    if verbose:
        typer.echo("\n🔍 Scanning GitHub for mirror repositories...")

    org = config["github"].get("default_org")

    # Check cache first
    cached_mirrors = config_manager.get_scanned_mirrors()
    if cached_mirrors is not None:
        if verbose:
            typer.echo("  Using cached scan results (less than 30 minutes old)")
        mirrors = cached_mirrors
    else:
        mirrors = scan_for_mirrors(username, org)
        # Save to cache
        config_manager.save_scanned_mirrors(mirrors)

    if not mirrors:
        if verbose:
            typer.echo("\n❌ No mirror repositories found")
            typer.echo(
                "\n💡 Make sure you have mirror repositories with .github/workflows/mirror-sync.yml"
            )
        raise typer.Exit(0)

    # Display found mirrors
    if verbose:
        display_scan_results(mirrors)
    else:
        # Pipe-friendly output - just repo names
        for mirror in mirrors:
            typer.echo(mirror.get("name", ""))


def display_scan_results(mirrors: list) -> None:
    """Display scan results in a formatted way."""
    typer.echo(f"\n✅ Found {len(mirrors)} mirror repositories:")
    typer.echo("=" * 70)

    for i, mirror in enumerate(mirrors, 1):
        mirror_name = mirror.get("name", "Unknown")
        is_private = mirror.get("is_private", False)
        description = mirror.get("description", "")
        updated_at = mirror.get("updated_at", "")

        visibility = "🔒" if is_private else "🌐"
        typer.echo(f"\n  [{i}] {visibility} {mirror_name}")

        if description:
            typer.echo(f"      📝 {description}")

        upstream = mirror.get("upstream", "")
        if upstream:
            typer.echo(f"      🔗 Upstream: {upstream}")
        else:
            typer.echo("      🔗 Upstream: (configured via secrets)")

        if updated_at:
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                typer.echo(f"      🕐 Updated: {formatted_date}")
            except Exception:
                pass

    typer.echo("\n" + "=" * 70)
    typer.echo("\n💡 To update these mirrors:")
    typer.echo("   • Update all mirrors:")
    typer.echo("     cli-git update-mirrors --scan | xargs -I {} cli-git update-mirrors --repo {}")
    typer.echo("   • Update specific: cli-git update-mirrors --repo <name>")
    typer.echo("   • Interactive selection: cli-git update-mirrors")

    raise typer.Exit(0)


def find_mirrors_to_update(
    repo: str | None,
    config_manager: ConfigManager,
    config: dict,
    username: str,
) -> list:
    """Find mirrors to update based on options."""
    typer.echo("\n🔍 Finding mirrors to update...")

    if repo:
        # Specific repository
        return [{"mirror": f"https://github.com/{repo}", "upstream": "", "name": repo}]

    # Check scanned mirrors cache first
    mirrors = config_manager.get_scanned_mirrors()

    if mirrors is None:
        # Fall back to recent mirrors if no scanned cache
        mirrors = config_manager.get_recent_mirrors()

        if not mirrors:
            # Need to scan
            org = config["github"].get("default_org")
            typer.echo("  Scanning for mirrors...")
            mirrors = scan_for_mirrors(username, org)
            # Save to cache
            config_manager.save_scanned_mirrors(mirrors)

    if not mirrors:
        typer.echo("\n❌ No mirror repositories found")
        typer.echo("\n💡 Run 'cli-git update-mirrors --scan' to find mirrors")
        raise typer.Exit(0)

    # Always use interactive selection when no specific repo is provided
    mirrors = select_mirrors_interactive(mirrors)

    return mirrors
