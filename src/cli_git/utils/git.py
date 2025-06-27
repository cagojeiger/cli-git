"""Git command utilities."""

import re
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
    full_cmd = ["git"] + cmd.split()

    result = subprocess.run(full_cmd, capture_output=True, text=True, cwd=cwd)

    if result.returncode != 0:
        error = subprocess.CalledProcessError(
            result.returncode, full_cmd, output=result.stdout, stderr=result.stderr
        )
        raise error

    return result.stdout.strip()


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
