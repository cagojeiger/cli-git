"""Common services for business logic."""

from typing import Any, Callable, TypeVar

import typer

from cli_git.utils.gh import GitHubError

T = TypeVar("T")


class ErrorHandler:
    """Centralized error handling service."""

    @staticmethod
    def handle_github_error(operation_name: str, error: GitHubError) -> None:
        """Handle GitHub-related errors with consistent messaging.

        Args:
            operation_name: Name of the operation that failed
            error: The GitHub error that occurred
        """
        typer.echo(f"\n❌ Failed to {operation_name}: {error}")
        raise typer.Exit(1) from error

    @staticmethod
    def handle_unexpected_error(operation_name: str, error: Exception) -> None:
        """Handle unexpected errors with consistent messaging.

        Args:
            operation_name: Name of the operation that failed
            error: The unexpected error that occurred
        """
        typer.echo(f"\n❌ Unexpected error during {operation_name}: {error}")
        raise typer.Exit(1) from error

    @staticmethod
    def safe_execute(operation_name: str, func: Callable[[], T]) -> T:
        """Safely execute a function with error handling.

        Args:
            operation_name: Name of the operation for error messages
            func: Function to execute

        Returns:
            Result of the function

        Raises:
            typer.Exit: If an error occurs
        """
        try:
            return func()
        except GitHubError as e:
            ErrorHandler.handle_github_error(operation_name, e)
        except Exception as e:
            ErrorHandler.handle_unexpected_error(operation_name, e)


class ValidationService:
    """Common validation service."""

    @staticmethod
    def ensure_authenticated() -> None:
        """Ensure GitHub CLI is authenticated."""
        from cli_git.utils.gh import check_gh_auth

        if not check_gh_auth():
            typer.echo("❌ GitHub CLI is not authenticated")
            typer.echo("   Please run: gh auth login")
            raise typer.Exit(1)

    @staticmethod
    def ensure_configured(config: dict[str, Any]) -> None:
        """Ensure CLI is properly configured."""
        if not config["github"]["username"]:
            typer.echo("❌ Configuration not initialized")
            typer.echo("   Run 'cli-git init' first")
            raise typer.Exit(1)

    @staticmethod
    def validate_prerequisites(config_manager: Any) -> tuple[dict[str, Any], str]:
        """Validate all prerequisites and return config and username.

        Args:
            config_manager: ConfigManager instance

        Returns:
            Tuple of (config, username)

        Raises:
            typer.Exit: If prerequisites are not met
        """
        ValidationService.ensure_authenticated()

        config = config_manager.get_config()
        ValidationService.ensure_configured(config)

        def get_username():
            from cli_git.utils.gh import get_current_username

            return get_current_username()

        username = ErrorHandler.safe_execute("get current username", get_username)
        return config, username


class GitHubService:
    """Common GitHub operations service."""

    @staticmethod
    def create_repository(name: str, org: str | None = None) -> str:
        """Create a private GitHub repository.

        Args:
            name: Repository name
            org: Organization name (optional)

        Returns:
            Repository URL
        """

        def create_repo():
            from cli_git.utils.gh import create_private_repo

            return create_private_repo(name, org=org)

        return ErrorHandler.safe_execute("create repository", create_repo)

    @staticmethod
    def get_upstream_branch(upstream_url: str) -> str:
        """Get upstream default branch.

        Args:
            upstream_url: Upstream repository URL

        Returns:
            Default branch name
        """

        def get_branch():
            from cli_git.utils.gh import get_upstream_default_branch

            return get_upstream_default_branch(upstream_url)

        return ErrorHandler.safe_execute("get upstream branch", get_branch)

    @staticmethod
    def add_secret(repo_name: str, secret_name: str, secret_value: str) -> None:
        """Add a secret to a repository.

        Args:
            repo_name: Repository name (owner/repo)
            secret_name: Secret name
            secret_value: Secret value
        """

        def add_secret():
            from cli_git.utils.gh import add_repo_secret

            return add_repo_secret(repo_name, secret_name, secret_value)

        ErrorHandler.safe_execute(f"add secret {secret_name}", add_secret)
