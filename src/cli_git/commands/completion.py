"""Shell completion installation command."""

import os
import subprocess
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


def completion_install_command() -> None:
    """Install shell completion for cli-git."""
    shell = detect_shell()

    if shell == "unknown":
        typer.echo("❌ Could not detect shell type")
        typer.echo("   Please install completion manually:")
        typer.echo("   cli-git --install-completion")
        raise typer.Exit(1)

    typer.echo(f"🔍 Detected shell: {shell}")

    # Use typer's built-in completion installation
    try:
        # Get the completion script
        result = subprocess.run(
            ["cli-git", "--show-completion", shell],
            capture_output=True,
            text=True,
            check=True,
        )
        completion_script = result.stdout

        # Determine where to install
        if shell == "bash":
            completion_file = Path.home() / ".bashrc"
            marker = "# cli-git completion"
        elif shell == "zsh":
            completion_file = Path.home() / ".zshrc"
            marker = "# cli-git completion"
        elif shell == "fish":
            completion_dir = Path.home() / ".config" / "fish" / "completions"
            completion_dir.mkdir(parents=True, exist_ok=True)
            completion_file = completion_dir / "cli-git.fish"
            marker = None
        else:
            raise typer.Exit(1)

        # Install completion
        if shell in ["bash", "zsh"]:
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
                f.write(completion_script)
                f.write(f"\n# End {marker}\n")

            typer.echo(f"✅ Completion installed to {completion_file}")
            typer.echo(f"   Restart your shell or run: source {completion_file}")

        elif shell == "fish":
            # Write completion file
            completion_file.write_text(completion_script)
            typer.echo(f"✅ Completion installed to {completion_file}")
            typer.echo("   Completion will be available in new shell sessions")

    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to generate completion: {e}")
        typer.echo("   Try running: cli-git --install-completion")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error installing completion: {e}")
        raise typer.Exit(1)
