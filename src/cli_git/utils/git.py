"""Git command utilities."""

import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def run_git_command(cmd: str, cwd: Optional[Path] = None) -> str:
    """Execute a git command and return output.

    Args:
        cmd: Git command to execute (without 'git' prefix)
        cwd: Working directory for the command

    Returns:
        Command output (stdout)

    Raises:
        subprocess.CalledProcessError: If command fails
    """
    full_cmd = ["git"] + shlex.split(cmd)

    result = subprocess.run(full_cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        error = subprocess.CalledProcessError(
            result.returncode, full_cmd, output=result.stdout, stderr=result.stderr
        )
        raise error

    return result.stdout.strip()


def get_default_branch(cwd: Optional[Path] = None) -> str:
    """Get the default branch of the current repository.

    Args:
        cwd: Working directory for the command

    Returns:
        Name of the default branch

    Raises:
        subprocess.CalledProcessError: If unable to determine default branch
    """
    try:
        # Try to get the default branch from upstream HEAD
        result = run_git_command("symbolic-ref refs/remotes/upstream/HEAD", cwd=cwd)
        # Extract branch name from refs/remotes/upstream/branch_name
        return result.split("/")[-1]
    except subprocess.CalledProcessError:
        pass

    try:
        # Fallback: get the first remote branch (usually the default)
        result = run_git_command("branch -r", cwd=cwd)
        lines = result.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("upstream/") and "HEAD" not in line:
                return line.split("/", 1)[1]
        # If no upstream branches, try origin
        for line in lines:
            line = line.strip()
            if line.startswith("origin/") and "HEAD" not in line:
                return line.split("/", 1)[1]
    except subprocess.CalledProcessError:
        pass

    # Final fallback to common default branch names
    for branch in ["main", "master", "develop"]:
        try:
            run_git_command(f"show-ref --verify --quiet refs/heads/{branch}", cwd=cwd)
            return branch
        except subprocess.CalledProcessError:
            continue

    raise subprocess.CalledProcessError(1, "git", "Unable to determine default branch")


def extract_repo_info(url: str) -> Tuple[str, str]:
    """Extract owner and repository name from a git URL.

    Args:
        url: Repository URL (HTTPS or SSH format)

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        ValueError: If URL format is invalid
    """
    # Remove trailing .git if present
    if url.endswith(".git"):
        url = url[:-4]

    # Try HTTPS pattern
    https_pattern = r"https?://[^/]+/([^/]+)/([^/]+)/?$"
    match = re.match(https_pattern, url)
    if match:
        return match.group(1), match.group(2)

    # Try SSH pattern
    ssh_pattern = r"git@[^:]+:([^/]+)/([^/]+)/?$"
    match = re.match(ssh_pattern, url)
    if match:
        return match.group(1), match.group(2)

    raise ValueError(f"Invalid repository URL: {url}")
