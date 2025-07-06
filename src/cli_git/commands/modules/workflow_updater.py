"""Workflow update functionality for mirror repositories."""

import subprocess
from typing import Optional

from cli_git.core.mirrorkeep import create_default_mirrorkeep
from cli_git.utils.gh import GitHubError


def update_workflow_file(repo: str, content: str) -> bool:
    """Update workflow file in repository.

    Args:
        repo: Repository name (owner/repo)
        content: New workflow content

    Returns:
        True if file was updated, False if no changes needed

    Raises:
        GitHubError: If update fails
    """
    # Use git commands instead of API for better reliability
    try:
        # Clone repository in a temporary directory
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clone the repo
            clone_result = subprocess.run(
                ["git", "clone", f"https://github.com/{repo}.git", tmpdir],
                capture_output=True,
                text=True,
            )

            if clone_result.returncode != 0:
                # Try with gh auth
                clone_result = subprocess.run(
                    ["gh", "repo", "clone", repo, tmpdir], capture_output=True, text=True
                )

                if clone_result.returncode != 0:
                    raise GitHubError(f"Failed to clone repository: {clone_result.stderr}")

            # Check if workflow file exists and compare content
            workflow_path = os.path.join(tmpdir, ".github", "workflows", "mirror-sync.yml")
            existing_content = ""
            if os.path.exists(workflow_path):
                with open(workflow_path, "r") as f:
                    existing_content = f.read()

            # Only update if content is different
            if existing_content == content:
                # No changes needed
                return False

            # Update workflow file
            os.makedirs(os.path.dirname(workflow_path), exist_ok=True)

            with open(workflow_path, "w") as f:
                f.write(content)

            # Save current directory before changing
            # IMPORTANT: Always restore the original directory to avoid side effects
            original_cwd = os.getcwd()

            try:
                # Commit and push
                os.chdir(tmpdir)

                subprocess.run(["git", "add", ".github/workflows/mirror-sync.yml"], check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Update mirror sync workflow to latest version"],
                    check=True,
                )
                subprocess.run(["git", "push"], check=True)

                return True
            finally:
                # Always restore the original directory
                os.chdir(original_cwd)

    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to update workflow: {e}")
    except Exception as e:
        raise GitHubError(f"Unexpected error updating workflow: {e}")


def get_repo_secret_value(repo: str, secret_name: str) -> Optional[str]:
    """Try to get a repository secret value.

    Note: Most secrets are write-only via API. This only works for
    extracting information from workflow files.

    Args:
        repo: Repository name (owner/repo)
        secret_name: Name of the secret

    Returns:
        Secret value if retrievable, None otherwise
    """
    if secret_name != "UPSTREAM_URL":
        # Most secrets are not readable via API
        return None

    # Try to get workflow file and look for upstream URL comments
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/contents/.github/workflows/mirror-sync.yml",
                "-q",
                ".content",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Decode base64 content
        import base64

        content = base64.b64decode(result.stdout.strip()).decode()

        # Look for upstream URL in comments
        for line in content.split("\n"):
            if "UPSTREAM_URL:" in line and "#" in line:
                comment_part = line.split("#", 1)[1].strip()
                if "UPSTREAM_URL:" in comment_part:
                    return comment_part.split("UPSTREAM_URL:", 1)[1].strip()

        # If UPSTREAM_URL is used in the workflow, return empty string to indicate it's a mirror
        if "secrets.UPSTREAM_URL" in content:
            return ""

    except Exception:
        pass

    return None


def create_mirrorkeep_if_missing(repo: str) -> bool:
    """Create .mirrorkeep file in repository if it doesn't exist.

    Args:
        repo: Repository name (owner/repo)

    Returns:
        True if file was created, False if already exists

    Raises:
        GitHubError: If operation fails
    """
    try:
        # Check if .mirrorkeep already exists
        check_result = subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/.mirrorkeep"],
            capture_output=True,
            text=True,
        )

        if check_result.returncode == 0:
            # File already exists
            return False

        # File doesn't exist, create it
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clone the repo
            clone_result = subprocess.run(
                ["gh", "repo", "clone", repo, tmpdir], capture_output=True, text=True
            )

            if clone_result.returncode != 0:
                raise GitHubError(f"Failed to clone repository: {clone_result.stderr}")

            # Create .mirrorkeep file
            mirrorkeep_path = os.path.join(tmpdir, ".mirrorkeep")
            mirrorkeep_content = create_default_mirrorkeep()

            with open(mirrorkeep_path, "w") as f:
                f.write(mirrorkeep_content)

            # Save current directory before changing
            # IMPORTANT: Always restore the original directory to avoid side effects
            original_cwd = os.getcwd()

            try:
                # Commit and push
                os.chdir(tmpdir)

                subprocess.run(["git", "add", ".mirrorkeep"], check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Add .mirrorkeep file for preserving custom files"],
                    check=True,
                )
                subprocess.run(["git", "push"], check=True)

                return True
            finally:
                # Always restore the original directory
                os.chdir(original_cwd)

    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to create .mirrorkeep: {e}")
    except Exception as e:
        raise GitHubError(f"Unexpected error creating .mirrorkeep: {e}")
