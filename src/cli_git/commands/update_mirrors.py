"""Update existing mirror repositories with current settings."""

import subprocess
from typing import Annotated, Optional

import typer

from cli_git.commands.modules.interactive import select_mirrors_interactive
from cli_git.commands.modules.scan import scan_for_mirrors
from cli_git.commands.modules.workflow_updater import update_workflow_file
from cli_git.completion.completers import complete_repository
from cli_git.core.workflow import generate_sync_workflow
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import (
    GitHubError,
    add_repo_secret,
    check_gh_auth,
    get_current_username,
    get_upstream_default_branch,
)
from cli_git.utils.git import extract_repo_info


def update_mirrors_command(
    repo: Annotated[
        Optional[str],
        typer.Option(
            "--repo",
            "-r",
            help="Specific repository to update (owner/repo). Use --scan to list available mirrors.",
            autocompletion=complete_repository,
        ),
    ] = None,
    scan: Annotated[
        bool,
        typer.Option(
            "--scan", "-s", help="Scan and list mirror repositories (outputs repo names only)"
        ),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed information when scanning")
    ] = False,
) -> None:
    """Update mirror repositories with current settings.

    Examples:
        # Scan for mirrors (pipe-friendly output)
        cli-git update-mirrors --scan

        # Update specific mirror
        cli-git update-mirrors --repo testuser/mirror-repo

        # Update all mirrors using xargs
        cli-git update-mirrors --scan | xargs -I {} cli-git update-mirrors --repo {}
    """
    # Check prerequisites
    if not check_gh_auth():
        typer.echo("❌ GitHub CLI is not authenticated")
        typer.echo("   Please run: gh auth login")
        raise typer.Exit(1)

    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()

    github_token = config["github"].get("github_token", "")
    slack_webhook_url = config["github"].get("slack_webhook_url", "")

    if not github_token:
        typer.echo("⚠️  No GitHub token found in configuration")
        typer.echo("   Run 'cli-git init' to add a GitHub token")
        typer.echo("   Continuing without GH_TOKEN (tag sync may fail)...")

    # Get current username
    try:
        username = get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    # Handle scan option
    if scan:
        _handle_scan_option(config_manager, config, username, verbose)
        return

    # Find mirrors to update
    mirrors = _find_mirrors_to_update(repo, config_manager, config, username)

    # Update each mirror
    _update_mirrors(mirrors, github_token, slack_webhook_url)


def _handle_scan_option(
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
        _display_scan_results(mirrors)
    else:
        # Pipe-friendly output - just repo names
        for mirror in mirrors:
            typer.echo(mirror.get("name", ""))


def _display_scan_results(mirrors: list) -> None:
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


def _find_mirrors_to_update(
    repo: Optional[str],
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


def _update_mirrors(mirrors: list, github_token: str, slack_webhook_url: str) -> None:
    """Update the selected mirrors."""
    success_count = 0

    for mirror in mirrors:
        repo_name = mirror.get("name")
        if not repo_name:
            # Extract from URL
            try:
                _, repo_part = extract_repo_info(mirror["mirror"])
                owner = mirror["mirror"].split("/")[-2]
                repo_name = f"{owner}/{repo_part}"
            except Exception:
                typer.echo(f"\n❌ Invalid repository URL: {mirror['mirror']}")
                continue

        typer.echo(f"\n🔄 Updating {repo_name}...")

        try:
            # Check if mirror-sync.yml exists
            check = subprocess.run(
                ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
                capture_output=True,
            )
            if check.returncode != 0:
                typer.echo(f"  ⚠️  Skipping {repo_name}: No mirror-sync.yml found")
                continue

            # Get upstream URL
            upstream_url = mirror.get("upstream")

            if not upstream_url:
                typer.echo("  ✓ Existing mirror detected")
                typer.echo("  Preserving current upstream configuration")
            else:
                # Update upstream secrets
                typer.echo("  Getting upstream branch info...")
                upstream_branch = get_upstream_default_branch(upstream_url)

                typer.echo("  Updating repository secrets...")
                add_repo_secret(repo_name, "UPSTREAM_URL", upstream_url)
                add_repo_secret(repo_name, "UPSTREAM_DEFAULT_BRANCH", upstream_branch)

            # Update additional secrets
            if github_token:
                add_repo_secret(repo_name, "GH_TOKEN", github_token)
                typer.echo("    ✓ GitHub token added")

            if slack_webhook_url:
                add_repo_secret(repo_name, "SLACK_WEBHOOK_URL", slack_webhook_url)
                typer.echo("    ✓ Slack webhook added")

            # Update workflow file
            typer.echo("  Updating workflow file...")

            workflow_content = generate_sync_workflow(
                upstream_url or "https://github.com/PLACEHOLDER/PLACEHOLDER",
                "0 0 * * *",  # Default schedule
                upstream_branch if upstream_url else "main",
            )

            workflow_updated = update_workflow_file(repo_name, workflow_content)

            if workflow_updated:
                typer.echo("    ✓ Workflow file updated")
            else:
                typer.echo("    ✓ Workflow file already up to date")

            typer.echo(f"  ✅ Successfully updated {repo_name}")
            success_count += 1

        except GitHubError as e:
            typer.echo(f"  ❌ Failed to update {repo_name}: {e}")
        except Exception as e:
            typer.echo(f"  ❌ Unexpected error updating {repo_name}: {e}")

    # Summary
    typer.echo(f"\n📊 Update complete: {success_count}/{len(mirrors)} mirrors updated successfully")

    if success_count < len(mirrors):
        typer.echo("\n💡 For failed updates, you may need to:")
        typer.echo("   - Check repository permissions")
        typer.echo("   - Verify the repository exists")
        typer.echo("   - Try updating individually with --repo option")
