"""Main workflow for update mirrors command."""

from typing import Annotated

import typer

from cli_git.commands.update.update_operations import update_mirrors_batch
from cli_git.commands.update.update_validation import (
    check_update_prerequisites,
    find_mirrors_to_update,
    handle_scan_option,
)
from cli_git.completion.completers import complete_repository


def update_mirrors_command(
    repo: Annotated[
        str | None,
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
    # Step 1: Check prerequisites
    config_manager, config, username = check_update_prerequisites()

    # Step 2: Handle scan option
    if scan:
        handle_scan_option(config_manager, config, username, verbose)
        return

    # Step 3: Find mirrors to update
    mirrors = find_mirrors_to_update(repo, config_manager, config, username)

    # Step 4: Update mirrors
    github_token = config["github"].get("github_token", "")
    slack_webhook_url = config["github"].get("slack_webhook_url", "")
    update_mirrors_batch(mirrors, github_token, slack_webhook_url)
