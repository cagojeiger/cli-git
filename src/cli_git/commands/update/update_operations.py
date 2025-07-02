"""Core operations for updating mirror repositories."""

import subprocess

import typer

from cli_git.commands.modules.workflow_updater import update_workflow_file
from cli_git.commands.update.update_models import MirrorUpdateResult
from cli_git.core.workflow import generate_sync_workflow
from cli_git.utils.gh import GitHubError
from cli_git.utils.git import extract_repo_info


def extract_mirror_repo_name(mirror: dict[str, any]) -> str | None:
    """Extract repository name from mirror data.

    Args:
        mirror: Mirror information dictionary

    Returns:
        Repository name in owner/repo format or None if extraction fails
    """
    repo_name = mirror.get("name")
    if repo_name:
        return repo_name

    # Extract from URL
    try:
        _, repo_part = extract_repo_info(mirror["mirror"])
        owner = mirror["mirror"].split("/")[-2]
        return f"{owner}/{repo_part}"
    except Exception:
        return None


def check_mirror_sync_exists(repo_name: str) -> bool:
    """Check if mirror-sync.yml exists in repository.

    Args:
        repo_name: Repository name in owner/repo format

    Returns:
        True if mirror-sync.yml exists, False otherwise
    """
    check = subprocess.run(
        ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
        capture_output=True,
    )
    return check.returncode == 0


def update_mirror_secrets(
    repo_name: str, upstream_url: str | None, github_token: str, slack_webhook_url: str
) -> None:
    """Update repository secrets for mirror.

    Args:
        repo_name: Repository name in owner/repo format
        upstream_url: Upstream repository URL (optional)
        github_token: GitHub Personal Access Token
        slack_webhook_url: Slack webhook URL for notifications
    """
    # Import from parent module to ensure test patches work
    from .. import update_mirrors

    if upstream_url:
        typer.echo("  Getting upstream branch info...")
        upstream_branch = update_mirrors.get_upstream_default_branch(upstream_url)

        typer.echo("  Updating repository secrets...")
        update_mirrors.add_repo_secret(repo_name, "UPSTREAM_URL", upstream_url)
        update_mirrors.add_repo_secret(repo_name, "UPSTREAM_DEFAULT_BRANCH", upstream_branch)
    else:
        typer.echo("  ✓ Existing mirror detected")
        typer.echo("  Preserving current upstream configuration")

    # Update additional secrets
    if github_token:
        update_mirrors.add_repo_secret(repo_name, "GH_TOKEN", github_token)
        typer.echo("    ✓ GitHub token added")

    if slack_webhook_url:
        update_mirrors.add_repo_secret(repo_name, "SLACK_WEBHOOK_URL", slack_webhook_url)
        typer.echo("    ✓ Slack webhook added")


def update_mirror_workflow(
    repo_name: str, upstream_url: str | None, upstream_branch: str | None = None
) -> bool:
    """Update workflow file for mirror.

    Args:
        repo_name: Repository name in owner/repo format
        upstream_url: Upstream repository URL (optional)
        upstream_branch: Upstream default branch (optional)

    Returns:
        True if workflow was updated, False if already up to date
    """
    typer.echo("  Updating workflow file...")

    workflow_content = generate_sync_workflow(
        upstream_url or "https://github.com/PLACEHOLDER/PLACEHOLDER",
        "0 0 * * *",  # Default schedule
        upstream_branch or "main",
    )

    workflow_updated = update_workflow_file(repo_name, workflow_content)

    if workflow_updated:
        typer.echo("    ✓ Workflow file updated")
    else:
        typer.echo("    ✓ Workflow file already up to date")

    return workflow_updated


def update_single_mirror(mirror: dict[str, any], github_token: str, slack_webhook_url: str) -> bool:
    """Update a single mirror repository.

    Args:
        mirror: Mirror information dictionary
        github_token: GitHub Personal Access Token
        slack_webhook_url: Slack webhook URL

    Returns:
        True if update succeeded, False otherwise
    """
    # Extract repository name
    repo_name = extract_mirror_repo_name(mirror)
    if not repo_name:
        typer.echo(f"\n❌ Invalid repository URL: {mirror.get('mirror', 'Unknown')}")
        return False

    typer.echo(f"\n🔄 Updating {repo_name}...")

    try:
        # Check if mirror-sync.yml exists
        if not check_mirror_sync_exists(repo_name):
            typer.echo(f"  ⚠️  Skipping {repo_name}: No mirror-sync.yml found")
            return False

        # Update secrets
        upstream_url = mirror.get("upstream")
        update_mirror_secrets(repo_name, upstream_url, github_token, slack_webhook_url)

        # Update workflow
        from .. import update_mirrors

        upstream_branch = (
            update_mirrors.get_upstream_default_branch(upstream_url) if upstream_url else None
        )
        update_mirror_workflow(repo_name, upstream_url, upstream_branch)

        typer.echo(f"  ✅ Successfully updated {repo_name}")
        return True

    except GitHubError as e:
        typer.echo(f"  ❌ Failed to update {repo_name}: {e}")
        return False
    except Exception as e:
        typer.echo(f"  ❌ Unexpected error updating {repo_name}: {e}")
        return False


def update_mirrors_batch(
    mirrors: list, github_token: str, slack_webhook_url: str
) -> MirrorUpdateResult:
    """Update the selected mirrors.

    Args:
        mirrors: List of mirror dictionaries
        github_token: GitHub Personal Access Token
        slack_webhook_url: Slack webhook URL

    Returns:
        MirrorUpdateResult with operation summary
    """
    result = MirrorUpdateResult(total_count=len(mirrors))

    for mirror in mirrors:
        if update_single_mirror(mirror, github_token, slack_webhook_url):
            result.success_count += 1
        else:
            repo_name = extract_mirror_repo_name(mirror) or "Unknown"
            result.failed_mirrors.append(repo_name)

    # Display summary
    typer.echo(
        f"\n📊 Update complete: {result.success_count}/{result.total_count} mirrors updated successfully"
    )

    if result.success_count < result.total_count:
        typer.echo("\n💡 For failed updates, you may need to:")
        typer.echo("   - Check repository permissions")
        typer.echo("   - Verify the repository exists")

    return result
