"""Git operations for private mirror functionality."""

import subprocess
from pathlib import Path

from cli_git.utils.git import get_default_branch, run_git_command


def clone_repository(upstream_url: str, target_path: Path) -> None:
    """Clone a repository from upstream URL.

    Args:
        upstream_url: URL of the upstream repository
        target_path: Path where to clone the repository
    """
    run_git_command(f"clone {upstream_url} {target_path}")


def setup_remotes(repo_path: Path, mirror_url: str) -> None:
    """Setup git remotes for mirror repository.

    Args:
        repo_path: Path to the repository
        mirror_url: URL of the mirror repository
    """
    run_git_command("remote rename origin upstream", cwd=repo_path)
    run_git_command(f"remote add origin {mirror_url}", cwd=repo_path)


def push_to_mirror(repo_path: Path) -> None:
    """Push all branches and tags to mirror.

    Args:
        repo_path: Path to the repository
    """
    run_git_command("push origin --all", cwd=repo_path)
    run_git_command("push origin --tags", cwd=repo_path)


def commit_changes(repo_path: Path, message: str) -> None:
    """Commit all changes with given message.

    Args:
        repo_path: Path to the repository
        message: Commit message
    """
    run_git_command("add -A", cwd=repo_path)
    run_git_command(f'commit -m "{message}"', cwd=repo_path)


def push_workflow_branch(repo_path: Path) -> None:
    """Push workflow changes to the default branch.

    Tries to detect and push to the default branch.
    Falls back to common branch names if detection fails.

    Args:
        repo_path: Path to the repository
    """
    try:
        default_branch = get_default_branch(repo_path)
        run_git_command(f"push origin {default_branch}", cwd=repo_path)
    except subprocess.CalledProcessError:
        # Fallback to common branch names if detection fails
        for branch in ["main", "master"]:
            try:
                run_git_command(f"push origin {branch}", cwd=repo_path)
                break
            except subprocess.CalledProcessError:
                continue
        else:
            # If all fails, just push current branch
            run_git_command("push origin HEAD", cwd=repo_path)
