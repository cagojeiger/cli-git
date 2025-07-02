"""Validation and configuration functions for mirror operations."""

import typer

from cli_git.commands.mirror.mirror_config import MirrorConfig
from cli_git.utils.gh import GitHubError
from cli_git.utils.git import extract_repo_info
from cli_git.utils.validators import (
    ValidationError,
    validate_cron_schedule,
    validate_github_url,
    validate_organization,
    validate_prefix,
    validate_repository_name,
)


def validate_mirror_inputs(
    upstream: str, org: str | None, schedule: str, prefix: str | None
) -> None:
    """Validate all inputs for private mirror command.

    Args:
        upstream: Upstream repository URL
        org: Organization name (optional)
        schedule: Cron schedule for synchronization
        prefix: Mirror name prefix (optional)

    Raises:
        ValidationError: If any validation fails
    """
    # Validate all inputs in one place to reduce function calls
    validate_github_url(upstream)
    if org:
        validate_organization(org)
    validate_cron_schedule(schedule)
    if prefix is not None:
        validate_prefix(prefix)


def resolve_mirror_parameters(
    config: dict[str, any],
    repo_name: str,
    custom_repo: str | None,
    prefix: str | None,
    org: str | None,
) -> tuple[str, str]:
    """Resolve mirror parameters from config and inputs.

    Args:
        config: Configuration dictionary
        repo_name: Extracted repository name
        custom_repo: Custom repository name (optional)
        prefix: Mirror prefix (optional)
        org: Organization name (optional)

    Returns:
        Tuple of (target_name, organization)
    """
    # Simplified parameter resolution - apply defaults in single operations
    prefix = prefix or config["preferences"].get("default_prefix", "mirror-")
    target_name = custom_repo or (f"{prefix}{repo_name}" if prefix else repo_name)
    org = org or config["github"]["default_org"]

    return target_name, org


def check_prerequisites():
    """Check GitHub auth and configuration prerequisites.

    Returns:
        ConfigManager instance with loaded config

    Raises:
        typer.Exit: If prerequisites are not met
    """
    # Import from parent module to ensure test patches work
    from .. import private_mirror

    # Direct check for compatibility with existing tests
    if not private_mirror.check_gh_auth():
        typer.echo("❌ GitHub CLI is not authenticated")
        typer.echo("   Please run: gh auth login")
        raise typer.Exit(1)

    config_manager = private_mirror.ConfigManager()
    config = config_manager.get_config()

    if not config["github"]["username"]:
        typer.echo("❌ Configuration not initialized")
        typer.echo("   Run 'cli-git init' first")
        raise typer.Exit(1)

    return config_manager


def prepare_mirror_config(
    upstream: str,
    repo: str | None,
    prefix: str | None,
    org: str | None,
    schedule: str,
    no_sync: bool,
    config: dict[str, any],
) -> MirrorConfig:
    """Prepare mirror configuration from inputs and config.

    Args:
        upstream: Upstream repository URL
        repo: Custom repository name (optional)
        prefix: Mirror name prefix (optional)
        org: Organization name (optional)
        schedule: Cron schedule
        no_sync: Whether to disable sync
        config: Configuration dictionary

    Returns:
        MirrorConfig with all parameters resolved

    Raises:
        typer.Exit: If validation fails
    """
    # Extract repository information
    try:
        _, repo_name = extract_repo_info(upstream)
    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from e

    # Resolve parameters
    target_name, org = resolve_mirror_parameters(config, repo_name, repo, prefix, org)

    # Validate final repository name
    try:
        validate_repository_name(target_name)
    except ValidationError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e

    # Get current username
    from .. import private_mirror

    try:
        username = private_mirror.get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from e

    return MirrorConfig(
        upstream_url=upstream,
        target_name=target_name,
        username=username,
        org=org,
        schedule=schedule,
        no_sync=no_sync,
        slack_webhook_url=config["github"].get("slack_webhook_url", ""),
        github_token=config["github"].get("github_token", ""),
    )
