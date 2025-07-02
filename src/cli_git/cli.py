"""CLI entry point for cli-git."""

import sys
from collections.abc import Callable
from functools import partial
from typing import Annotated

import typer

from cli_git import __version__
from cli_git.commands.completion import completion_install_command
from cli_git.commands.info import info_command
from cli_git.commands.init import init_command
from cli_git.commands.private_mirror import private_mirror_command
from cli_git.commands.update_mirrors import update_mirrors_command


def create_version_message(version: str) -> str:
    """
    Create version message string.

    Pure function that formats the version message.
    """
    return f"cli-git version: {version}"


def display_message(message_creator: Callable[[str], str], version: str) -> None:
    """
    Display message using the provided message creator function.

    Higher-order function that accepts a message creator function.
    """
    typer.echo(message_creator(version))


def exit_program(code: int = 0) -> None:
    """Exit the program with the given code."""
    sys.exit(code)


def version_callback(value: bool) -> None:
    """
    Handle version option callback.

    Functional composition of display and exit operations.
    """
    if value:
        # Compose functions using partial application
        display_version = partial(display_message, create_version_message)
        display_version(__version__)
        exit_program()


# Create the main Typer app
app = typer.Typer(
    name="cli-git",
    help="A modern Python CLI tool for Git operations",
    no_args_is_help=True,
)


# Version option using functional approach
version_option = partial(
    typer.Option,
    "--version",
    "-v",
    callback=version_callback,
    is_eager=True,
    help="Show the version and exit",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool | None, version_option()] = None,
) -> None:
    """
    CLI main entry point.

    This callback runs before any command.
    """
    # If no subcommand is provided, just exit successfully
    if ctx.invoked_subcommand is None:
        pass  # Version is handled by the callback


# Register commands
app.command(name="init")(init_command)
app.command(name="info")(info_command)
app.command(name="private-mirror")(private_mirror_command)
app.command(name="completion")(completion_install_command)
app.command(name="update-mirrors")(update_mirrors_command)


if __name__ == "__main__":
    app()
