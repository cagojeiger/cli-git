"""Update existing mirror repositories with current settings."""

import json
import subprocess
from typing import Annotated, Dict, List, Optional

import typer

from cli_git.core.workflow import generate_sync_workflow
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import (
    GitHubError,
    add_repo_secret,
    check_gh_auth,
    get_current_username,
    get_upstream_default_branch,
)
from cli_git.utils.git import extract_repo_info


def get_repo_secret_value(repo: str, secret_name: str) -> Optional[str]:
    """Try to get a repository secret value (only works for UPSTREAM_URL via API).

    Args:
        repo: Repository name (owner/repo)
        secret_name: Name of the secret

    Returns:
        Secret value if retrievable, None otherwise
    """
    if secret_name != "UPSTREAM_URL":
        # Most secrets are not readable via API
        return None

    # Try to get workflow file and extract UPSTREAM_URL
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

        # Simple extraction - look for UPSTREAM_URL in env
        for line in content.split("\n"):
            if "UPSTREAM_URL:" in line and "secrets.UPSTREAM_URL" in line:
                # This confirms it uses UPSTREAM_URL, but we can't get the actual value
                # Return empty string to indicate it's a mirror
                return ""

    except Exception:
        pass

    return None


def update_workflow_via_api(repo: str, content: str) -> None:
    """Update workflow file using GitHub API.

    Args:
        repo: Repository name (owner/repo)
        content: New workflow content

    Raises:
        GitHubError: If update fails
    """
    import base64

    # 1. Try to get current file info (for SHA)
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/.github/workflows/mirror-sync.yml"],
        capture_output=True,
        text=True,
    )

    sha = None
    if result.returncode == 0:
        # File exists - extract SHA
        file_info = json.loads(result.stdout)
        sha = file_info.get("sha")

    # 2. Encode content
    encoded_content = base64.b64encode(content.encode()).decode()

    # 3. Update or create file
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/contents/.github/workflows/mirror-sync.yml",
        "-X",
        "PUT",
        "-f",
        "message=Update mirror sync workflow to latest version",
        "-f",
        f"content={encoded_content}",
    ]

    if sha:
        cmd.extend(["-f", f"sha={sha}"])

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise GitHubError(f"Failed to update workflow: {e.stderr}")


def scan_for_mirrors(username: str, org: Optional[str] = None) -> List[Dict[str, str]]:
    """Scan GitHub for mirror repositories created by cli-git.

    Args:
        username: GitHub username
        org: Organization name (optional)

    Returns:
        List of mirror dictionaries with 'mirror' and 'upstream' keys
    """
    mirrors = []

    # Determine owners to search
    owners = [username]
    if org:
        owners.append(org)

    for owner in owners:
        typer.echo(f"  Scanning {owner}...")

        # Get all repositories
        result = subprocess.run(
            ["gh", "repo", "list", owner, "--limit", "1000", "--json", "nameWithOwner,url"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            continue

        repos = json.loads(result.stdout)

        for repo in repos:
            repo_name = repo["nameWithOwner"]

            # Check if mirror-sync.yml exists
            check = subprocess.run(
                ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
                capture_output=True,
            )

            if check.returncode == 0:
                # This is likely a mirror - try to get upstream URL from workflow
                # Since we can't read secrets, we'll mark it as a potential mirror
                mirrors.append(
                    {
                        "mirror": repo["url"],
                        "upstream": "",  # Will be filled from existing secret
                        "name": repo_name,
                    }
                )

    return mirrors


def select_mirrors_interactive(mirrors: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Interactively select mirrors to update.

    Args:
        mirrors: List of mirror dictionaries

    Returns:
        Selected mirrors
    """
    if not mirrors:
        return []

    typer.echo("\n📋 Available mirrors:")
    for i, mirror in enumerate(mirrors, 1):
        repo_name = (
            extract_repo_info(mirror["mirror"])[1]
            if "/" in mirror["mirror"]
            else mirror.get("name", "unknown")
        )
        upstream = mirror.get("upstream", "Unknown")
        typer.echo(f"{i}. {repo_name}")
        if upstream:
            typer.echo(f"   Upstream: {upstream}")

    typer.echo("\nEnter numbers separated by commas (e.g., 1,3,5) or 'all':")
    selection = typer.prompt("Selection", default="all")

    if selection.lower() == "all":
        return mirrors

    try:
        indices = [int(x.strip()) - 1 for x in selection.split(",")]
        return [mirrors[i] for i in indices if 0 <= i < len(mirrors)]
    except (ValueError, IndexError):
        typer.echo("❌ Invalid selection")
        raise typer.Exit(1)


def update_mirrors_command(
    repo: Annotated[
        Optional[str],
        typer.Option("--repo", "-r", help="Specific repository to update (owner/repo)"),
    ] = None,
    all: Annotated[bool, typer.Option("--all", "-a", help="Update all mirrors from cache")] = False,
    scan: Annotated[bool, typer.Option("--scan", "-s", help="Scan GitHub for all mirrors")] = False,
) -> None:
    """Update mirror repositories with current settings."""
    # Check prerequisites
    if not check_gh_auth():
        typer.echo("❌ GitHub CLI is not authenticated")
        typer.echo("   Please run: gh auth login")
        raise typer.Exit(1)

    # Load current configuration
    config_manager = ConfigManager()
    config = config_manager.get_config()

    github_token = config["github"].get("github_token", "")
    slack_webhook_url = config["github"].get("slack_webhook_url", "")

    if not github_token:
        typer.echo("⚠️  No GitHub token found in configuration")
        typer.echo("   Run 'cli-git init' to add a GitHub token")
        typer.echo("   Continuing without GH_TOKEN (tag sync may fail)...")

    # Get current username
    try:
        username = get_current_username()
    except GitHubError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)

    # Find mirrors to update
    typer.echo("\n🔍 Finding mirrors to update...")

    if repo:
        # Specific repository
        mirrors = [{"mirror": f"https://github.com/{repo}", "upstream": "", "name": repo}]
    elif scan:
        # Scan GitHub for all mirrors
        org = config["github"].get("default_org")
        mirrors = scan_for_mirrors(username, org)
        if not mirrors:
            typer.echo("No mirror repositories found")
            raise typer.Exit(0)
    else:
        # Use cached mirrors
        mirrors = config_manager.get_recent_mirrors()
        if not mirrors:
            typer.echo("No mirrors found in cache")
            typer.echo("Use --scan to search GitHub for mirrors")
            raise typer.Exit(0)

        if not all:
            mirrors = select_mirrors_interactive(mirrors)

    # Update each mirror
    success_count = 0
    for mirror in mirrors:
        repo_name = mirror.get("name")
        if not repo_name:
            # Extract from URL
            try:
                _, repo_part = extract_repo_info(mirror["mirror"])
                owner = mirror["mirror"].split("/")[-2]
                repo_name = f"{owner}/{repo_part}"
            except Exception:
                typer.echo(f"\n❌ Invalid repository URL: {mirror['mirror']}")
                continue

        typer.echo(f"\n🔄 Updating {repo_name}...")

        try:
            # Get upstream URL (from cache or existing secret)
            upstream_url = mirror.get("upstream")

            # Check if mirror-sync.yml exists
            check = subprocess.run(
                ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
                capture_output=True,
            )
            if check.returncode != 0:
                typer.echo(f"  ⚠️  Skipping {repo_name}: No mirror-sync.yml found")
                continue

            if not upstream_url:
                # For existing mirrors without upstream in cache
                typer.echo("  ✓ Existing mirror detected")
                typer.echo("  Preserving current upstream configuration")
                # We'll update only GH_TOKEN and SLACK_WEBHOOK_URL
                # UPSTREAM_URL and UPSTREAM_DEFAULT_BRANCH will remain unchanged
            else:
                # We have upstream URL, so update everything
                typer.echo("  Getting upstream branch info...")
                upstream_branch = get_upstream_default_branch(upstream_url)

                # Update upstream-related secrets
                typer.echo("  Updating all repository secrets...")
                add_repo_secret(repo_name, "UPSTREAM_URL", upstream_url)
                add_repo_secret(repo_name, "UPSTREAM_DEFAULT_BRANCH", upstream_branch)

            # Update additional secrets
            if not upstream_url:
                typer.echo("  Updating additional secrets...")

            if github_token:
                add_repo_secret(repo_name, "GH_TOKEN", github_token)
                typer.echo("    ✓ GitHub token added")

            if slack_webhook_url:
                add_repo_secret(repo_name, "SLACK_WEBHOOK_URL", slack_webhook_url)
                typer.echo("    ✓ Slack webhook added")

            # Update workflow file
            typer.echo("  Updating workflow file...")

            if upstream_url:
                # We have full information, generate new workflow
                workflow_content = generate_sync_workflow(
                    upstream_url, "0 0 * * *", upstream_branch  # Default schedule
                )
            else:
                # No upstream URL, generate workflow with placeholders
                # The actual values will come from existing secrets
                workflow_content = generate_sync_workflow(
                    "https://github.com/PLACEHOLDER/PLACEHOLDER",  # Will use secret
                    "0 0 * * *",  # Default schedule
                    "main",  # Default branch, will use secret
                )

            update_workflow_via_api(repo_name, workflow_content)

            typer.echo(f"  ✅ Successfully updated {repo_name}")
            success_count += 1

        except GitHubError as e:
            typer.echo(f"  ❌ Failed to update {repo_name}: {e}")
        except Exception as e:
            typer.echo(f"  ❌ Unexpected error updating {repo_name}: {e}")

    # Summary
    typer.echo(f"\n📊 Update complete: {success_count}/{len(mirrors)} mirrors updated successfully")

    if success_count < len(mirrors):
        typer.echo("\n💡 For failed updates, you may need to:")
        typer.echo("   - Check repository permissions")
        typer.echo("   - Verify the repository exists")
        typer.echo("   - Try updating individually with --repo option")
