"""Shell completion installation command."""

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import typer


def detect_shell() -> str:
    """Detect the current shell.

    Returns:
        Shell name (bash, zsh, fish, or unknown)
    """
    shell = os.environ.get("SHELL", "").lower()
    if "bash" in shell:
        return "bash"
    elif "zsh" in shell:
        return "zsh"
    elif "fish" in shell:
        return "fish"
    else:
        return "unknown"


class ShellCompletionHandler(ABC):
    """Abstract base class for shell completion handlers."""

    @abstractmethod
    def get_completion_path(self) -> Path:
        """Get the path where completion should be installed."""
        pass

    @abstractmethod
    def install_completion(self, script: str) -> None:
        """Install the completion script."""
        pass

    @abstractmethod
    def get_success_message(self) -> str:
        """Get success message to display after installation."""
        pass


class BashCompletionHandler(ShellCompletionHandler):
    """Handler for Bash shell completion."""

    def get_completion_path(self) -> Path:
        return Path.home() / ".bashrc"

    def install_completion(self, script: str) -> None:
        completion_file = self.get_completion_path()
        marker = "# cli-git completion"

        # Check if already installed
        if completion_file.exists():
            content = completion_file.read_text()
            if marker in content:
                typer.echo("✅ Completion already installed")
                typer.echo(f"   To update, remove the {marker} section from {completion_file}")
                return

        # Append to shell config
        with open(completion_file, "a") as f:
            f.write(f"\n{marker}\n")
            f.write(script)
            f.write(f"\n# End {marker}\n")

    def get_success_message(self) -> str:
        completion_file = self.get_completion_path()
        return f"✅ Completion installed to {completion_file}\n   Restart your shell or run: source {completion_file}"


class ZshCompletionHandler(ShellCompletionHandler):
    """Handler for Zsh shell completion."""

    def get_completion_path(self) -> Path:
        return Path.home() / ".zshrc"

    def install_completion(self, script: str) -> None:
        completion_file = self.get_completion_path()
        marker = "# cli-git completion"

        # Check if already installed
        if completion_file.exists():
            content = completion_file.read_text()
            if marker in content:
                typer.echo("✅ Completion already installed")
                typer.echo(f"   To update, remove the {marker} section from {completion_file}")
                return

        # Append to shell config
        with open(completion_file, "a") as f:
            f.write(f"\n{marker}\n")
            f.write(script)
            f.write(f"\n# End {marker}\n")

    def get_success_message(self) -> str:
        completion_file = self.get_completion_path()
        return f"✅ Completion installed to {completion_file}\n   Restart your shell or run: source {completion_file}"


class FishCompletionHandler(ShellCompletionHandler):
    """Handler for Fish shell completion."""

    def get_completion_path(self) -> Path:
        completion_dir = Path.home() / ".config" / "fish" / "completions"
        completion_dir.mkdir(parents=True, exist_ok=True)
        return completion_dir / "cli-git.fish"

    def install_completion(self, script: str) -> None:
        completion_file = self.get_completion_path()
        completion_file.write_text(script)

    def get_success_message(self) -> str:
        completion_file = self.get_completion_path()
        return f"✅ Completion installed to {completion_file}\n   Completion will be available in new shell sessions"


def get_shell_handler(shell: str) -> ShellCompletionHandler | None:
    """Get the appropriate shell handler for the given shell.

    Args:
        shell: Shell name (bash, zsh, fish)

    Returns:
        Shell handler instance or None if shell is not supported
    """
    handlers = {
        "bash": BashCompletionHandler(),
        "zsh": ZshCompletionHandler(),
        "fish": FishCompletionHandler(),
    }
    return handlers.get(shell)


def generate_completion_script(shell: str) -> str:
    """Generate completion script for the given shell.

    Args:
        shell: Shell name

    Returns:
        Completion script content

    Raises:
        subprocess.CalledProcessError: If script generation fails
    """
    result = subprocess.run(
        ["cli-git", "--show-completion", shell],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def validate_shell_support(shell: str) -> ShellCompletionHandler:
    """Validate shell and get handler.

    Args:
        shell: Detected shell name

    Returns:
        Shell completion handler

    Raises:
        typer.Exit: If shell is not supported
    """
    if shell == "unknown":
        typer.echo("❌ Could not detect shell type")
        typer.echo("   Please install completion manually:")
        typer.echo("   cli-git --install-completion")
        raise typer.Exit(1)

    handler = get_shell_handler(shell)
    if not handler:
        typer.echo(f"❌ Unsupported shell: {shell}")
        raise typer.Exit(1)

    return handler


def install_completion_with_handler(handler: ShellCompletionHandler, shell: str) -> None:
    """Install completion using the provided handler.

    Args:
        handler: Shell completion handler
        shell: Shell name

    Raises:
        typer.Exit: If installation fails
    """
    try:
        # Generate completion script
        completion_script = generate_completion_script(shell)

        # Install completion
        handler.install_completion(completion_script)

        # Show success message
        typer.echo(handler.get_success_message())

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to generate completion: {e}")
        typer.echo("   Try running: cli-git --install-completion")
        raise typer.Exit(1) from e
    except Exception as e:
        typer.echo(f"❌ Error installing completion: {e}")
        raise typer.Exit(1) from e


def completion_install_command() -> None:
    """Install shell completion for cli-git."""
    # Step 1: Detect shell
    shell = detect_shell()
    typer.echo(f"🔍 Detected shell: {shell}")

    # Step 2: Validate shell support and get handler
    handler = validate_shell_support(shell)

    # Step 3: Install completion
    install_completion_with_handler(handler, shell)
