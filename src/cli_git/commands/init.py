"""Initialize user configuration for cli-git."""

from dataclasses import dataclass
from typing import Annotated

import typer

from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import (
    GitHubError,
    check_gh_auth,
    get_current_username,
    get_user_organizations,
    mask_token,
    run_gh_auth_login,
    validate_github_token,
)
from cli_git.utils.validators import ValidationError, validate_prefix, validate_slack_webhook_url


@dataclass
class InitConfig:
    """Configuration data for cli-git initialization."""

    username: str
    default_org: str = ""
    slack_webhook_url: str = ""
    github_token: str = ""
    default_prefix: str = "mirror-"


def mask_webhook_url(url: str) -> str:
    """Mask Slack webhook URL for display.

    Args:
        url: Slack webhook URL to mask

    Returns:
        Masked URL for display
    """
    if not url:
        return ""

    # https://hooks.slack.com/services/XXXXXXXXX/XXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXX
    # -> https://hooks.slack.com/services/XXX.../XXX.../XXX...
    parts = url.split("/")
    if len(parts) >= 7 and "hooks.slack.com" in url:
        # Mask the tokens (parts[4] = T..., parts[5] = B..., parts[6] = XXX...)
        parts[4] = parts[4][:3] + "..." if len(parts[4]) > 3 else parts[4]
        parts[5] = parts[5][:3] + "..." if len(parts[5]) > 3 else parts[5]
        parts[6] = parts[6][:3] + "..." if len(parts[6]) > 3 else parts[6]
    return "/".join(parts)


def ensure_github_auth() -> None:
    """Ensure GitHub CLI is authenticated.

    Raises:
        typer.Exit: If authentication fails or user declines to login
    """
    if not check_gh_auth():
        typer.echo("🔐 GitHub CLI is not authenticated")
        if typer.confirm("Would you like to login now?", default=True):
            typer.echo("📝 Starting GitHub authentication...")
            if run_gh_auth_login():
                typer.echo("✅ GitHub authentication successful!")
            else:
                typer.echo("❌ GitHub login failed")
                raise typer.Exit(1)
        else:
            typer.echo("   Please run: gh auth login")
            raise typer.Exit(1)


def get_organization_choice(orgs: list[str]) -> str:
    """Interactively select organization from list.

    Args:
        orgs: List of organization names

    Returns:
        Selected organization name or empty string for personal account
    """
    if not orgs:
        typer.echo("\n📋 No organizations found. Using personal account.")
        return ""

    typer.echo("\n📋 Your GitHub organizations:")
    for i, org in enumerate(orgs, 1):
        typer.echo(f"   {i}. {org}")
    typer.echo("   0. No organization (use personal account)")

    while True:
        choice = typer.prompt("\nSelect organization number", default="0")
        try:
            choice_num = int(choice)
            if choice_num == 0:
                return ""
            elif 1 <= choice_num <= len(orgs):
                return orgs[choice_num - 1]
            else:
                typer.echo("Invalid choice. Please try again.")
        except ValueError:
            typer.echo("Please enter a number.")


def get_validated_input(
    prompt: str,
    validator: callable,
    error_prefix: str = "",
    optional: bool = True,
    hide_input: bool = False,
) -> str:
    """Get and validate user input.

    Args:
        prompt: Input prompt message
        validator: Validation function that raises ValidationError
        error_prefix: Prefix for error messages
        optional: Whether input is optional (can be empty)
        hide_input: Whether to hide input (for passwords)

    Returns:
        Validated input string
    """
    while True:
        value = typer.prompt(prompt, default="" if optional else ..., hide_input=hide_input)

        if not value and optional:
            return ""

        try:
            validator(value)
            return value
        except ValidationError as e:
            typer.echo(f"{error_prefix}{e}")
            if optional:
                typer.echo("   Press Enter to skip or enter a valid value")


def collect_organization_info(username: str) -> str:
    """Collect organization information.

    Args:
        username: GitHub username

    Returns:
        Selected organization or empty string
    """
    try:
        orgs = get_user_organizations()
        return get_organization_choice(orgs)
    except GitHubError:
        # Fallback to manual input
        return typer.prompt("\nDefault organization (optional)", default="")


def collect_slack_webhook() -> str:
    """Collect and validate Slack webhook URL.

    Returns:
        Validated Slack webhook URL or empty string
    """
    typer.echo("\n🔔 Slack Integration (optional)")
    typer.echo("   Enter webhook URL to receive sync failure notifications")

    return get_validated_input("Slack webhook URL (optional)", validate_slack_webhook_url, "   ")


def collect_github_token() -> str:
    """Collect and validate GitHub Personal Access Token.

    Returns:
        Validated GitHub token or empty string
    """
    typer.echo("\n🔑 GitHub Personal Access Token (선택사항)")
    typer.echo("   태그 동기화를 위해 필요한 권한:")
    typer.echo("   - repo (전체 저장소 접근)")
    typer.echo("   - workflow (워크플로우 파일 수정)")
    typer.echo("")
    typer.echo("   토큰 생성: https://github.com/settings/tokens/new")
    typer.echo("   토큰이 없으면 Enter를 누르세요 (태그 동기화가 작동하지 않을 수 있음)")

    while True:
        github_token = typer.prompt("GitHub Personal Access Token", default="", hide_input=True)
        if not github_token:
            typer.echo("   ⚠️  토큰 없이 계속합니다. 태그 동기화가 실패할 수 있습니다.")
            return ""
        elif validate_github_token(github_token):
            typer.echo("   ✓ 토큰이 유효합니다.")
            return github_token
        else:
            typer.echo("   ❌ 유효하지 않은 토큰입니다. 다시 시도하거나 Enter를 눌러 건너뛰세요.")


def collect_mirror_prefix() -> str:
    """Collect and validate mirror prefix.

    Returns:
        Validated mirror prefix
    """
    while True:
        default_prefix = typer.prompt("\nDefault mirror prefix", default="mirror-")
        try:
            validate_prefix(default_prefix)
            return default_prefix
        except ValidationError as e:
            typer.echo(f"   {e}")


def collect_init_inputs(username: str) -> InitConfig:
    """Collect all initialization inputs from user.

    Args:
        username: GitHub username

    Returns:
        InitConfig with all collected data
    """
    return InitConfig(
        username=username,
        default_org=collect_organization_info(username),
        slack_webhook_url=collect_slack_webhook(),
        github_token=collect_github_token(),
        default_prefix=collect_mirror_prefix(),
    )


def display_success_message(config: InitConfig) -> None:
    """Display success message with configuration summary.

    Args:
        config: InitConfig with all configuration data
    """
    typer.echo()
    typer.echo("✅ Configuration initialized successfully!")
    typer.echo(f"   GitHub username: {config.username}")
    if config.default_org:
        typer.echo(f"   Default organization: {config.default_org}")
    if config.slack_webhook_url:
        typer.echo(f"   Slack webhook: {mask_webhook_url(config.slack_webhook_url)}")
    if config.github_token:
        typer.echo(f"   GitHub token: {mask_token(config.github_token)}")
    typer.echo(f"   Mirror prefix: {config.default_prefix}")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("- Run 'cli-git info' to see your configuration")
    typer.echo("- Run 'cli-git private-mirror <repo-url>' to create your first mirror")


def check_existing_config(config_manager: ConfigManager, force: bool) -> bool:
    """Check if configuration already exists.

    Args:
        config_manager: ConfigManager instance
        force: Whether to force reinitialization

    Returns:
        True if should continue with initialization, False otherwise
    """
    config = config_manager.get_config()
    if config["github"]["username"] and not force:
        typer.echo("⚠️  Configuration already exists")
        typer.echo(f"   Current user: {config['github']['username']}")
        if config["github"]["default_org"]:
            typer.echo(f"   Default org: {config['github']['default_org']}")
        typer.echo("   Use --force to reinitialize")
        return False
    return True


def save_config(config_manager: ConfigManager, config: InitConfig) -> None:
    """Save configuration to file.

    Args:
        config_manager: ConfigManager instance
        config: InitConfig to save
    """
    updates = {
        "github": {
            "username": config.username,
            "default_org": config.default_org,
            "slack_webhook_url": config.slack_webhook_url,
            "github_token": config.github_token,
        },
        "preferences": {"default_prefix": config.default_prefix},
    }
    config_manager.update_config(updates)


def init_command(
    force: Annotated[bool, typer.Option("--force", "-f", help="Force reinitialization")] = False,
) -> None:
    """Initialize cli-git configuration with GitHub account information."""
    # Step 1: Ensure GitHub authentication
    ensure_github_auth()

    # Step 2: Get current GitHub username
    try:
        username = get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    # Step 3: Check existing configuration
    config_manager = ConfigManager()
    if not check_existing_config(config_manager, force):
        return

    # Step 4: Collect all inputs
    config = collect_init_inputs(username)

    # Step 5: Save configuration
    save_config(config_manager, config)

    # Step 6: Display success message
    display_success_message(config)
