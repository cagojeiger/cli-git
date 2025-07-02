"""Update existing mirror repositories with current settings."""

import json
import subprocess
from typing import Annotated, Dict, List, Optional

import typer

from cli_git.completion.completers import complete_repository
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

        # Get all repositories with more details
        result = subprocess.run(
            [
                "gh",
                "repo",
                "list",
                owner,
                "--limit",
                "1000",
                "--json",
                "nameWithOwner,url,description,isPrivate,updatedAt",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            typer.echo(f"    ⚠️  Could not access {owner}'s repositories")
            continue

        try:
            repos = json.loads(result.stdout)
        except json.JSONDecodeError:
            typer.echo(f"    ⚠️  Failed to parse repository data for {owner}")
            continue

        # Counter for progress
        checked = 0
        found = 0

        for repo in repos:
            repo_name = repo["nameWithOwner"]
            checked += 1

            # Check if mirror-sync.yml exists
            check = subprocess.run(
                ["gh", "api", f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Suppress stderr for cleaner output
            )

            if check.returncode == 0:
                found += 1
                # This is a mirror repository
                # Try to extract upstream info from workflow content
                upstream = ""
                try:
                    # Get workflow content
                    workflow_result = subprocess.run(
                        [
                            "gh",
                            "api",
                            f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml",
                            "-q",
                            ".content",
                        ],
                        capture_output=True,
                        text=True,
                    )
                    if workflow_result.returncode == 0:
                        # Decode base64 content
                        import base64

                        content = base64.b64decode(workflow_result.stdout.strip()).decode()

                        # Try to extract upstream URL from comments or environment variables
                        for line in content.split("\n"):
                            if "UPSTREAM_URL:" in line and "#" in line:
                                # Look for comments like # UPSTREAM_URL: https://github.com/owner/repo
                                comment_part = line.split("#", 1)[1].strip()
                                if "UPSTREAM_URL:" in comment_part:
                                    upstream = comment_part.split("UPSTREAM_URL:", 1)[1].strip()
                                    break
                except Exception:
                    pass  # If we can't get upstream, that's okay

                mirrors.append(
                    {
                        "mirror": repo["url"],
                        "upstream": upstream,
                        "name": repo_name,
                        "description": repo.get("description", ""),
                        "is_private": repo.get("isPrivate", False),
                        "updated_at": repo.get("updatedAt", ""),
                    }
                )

        if checked > 0:
            typer.echo(f"    ✓ Checked {checked} repositories, found {found} mirrors")

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

    typer.echo("\n📋 Found mirror repositories:")
    typer.echo("=" * 60)

    # Display mirrors with better formatting
    for i, mirror in enumerate(mirrors, 1):
        # Extract repository name
        mirror_name = mirror.get("name", "")
        if not mirror_name:
            if "/" in mirror["mirror"]:
                try:
                    _, repo_part = extract_repo_info(mirror["mirror"])
                    owner = mirror["mirror"].split("/")[-2]
                    mirror_name = f"{owner}/{repo_part}"
                except Exception:
                    mirror_name = "Unknown"
            else:
                mirror_name = "Unknown"

        # Extract upstream info
        upstream = mirror.get("upstream", "")
        if upstream and "github.com/" in upstream:
            try:
                parts = upstream.split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    upstream_display = f"{parts[0]}/{parts[1]}"
                else:
                    upstream_display = upstream
            except Exception:
                upstream_display = upstream
        else:
            upstream_display = upstream or "Unknown"

        # Display with formatting
        typer.echo(f"\n  [{i}] 🔄 {mirror_name}")
        typer.echo(f"      └─ Mirrors: {upstream_display}")

    typer.echo("\n" + "=" * 60)
    typer.echo("\n💡 Options:")
    typer.echo("  • Enter numbers to select specific mirrors (e.g., 1,3,5)")
    typer.echo("  • Type 'all' to update all mirrors")
    typer.echo("  • Press Enter to update all (default)")
    typer.echo("  • Type 'none' or 'q' to cancel")

    selection = typer.prompt("\n📝 Your selection", default="all")

    # Handle different input cases
    if selection.lower() in ["all", ""]:
        typer.echo(f"\n✅ Selected all {len(mirrors)} mirrors")
        return mirrors

    if selection.lower() in ["none", "q", "quit", "exit"]:
        typer.echo("\n❌ Update cancelled")
        raise typer.Exit(0)

    # Parse number selection
    try:
        # Handle ranges (e.g., "1-3" becomes "1,2,3")
        expanded_selection = []
        for part in selection.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-")
                    start, end = int(start.strip()), int(end.strip())
                    expanded_selection.extend(range(start, end + 1))
                except Exception:
                    typer.echo(f"⚠️  Invalid range: {part}")
                    raise typer.Exit(1)
            else:
                expanded_selection.append(int(part))

        # Convert to 0-based indices and validate
        indices = [i - 1 for i in expanded_selection]
        selected = []
        invalid = []

        for idx in indices:
            if 0 <= idx < len(mirrors):
                selected.append(mirrors[idx])
            else:
                invalid.append(idx + 1)

        if invalid:
            typer.echo(f"\n⚠️  Invalid numbers ignored: {', '.join(map(str, invalid))}")

        if selected:
            typer.echo(f"\n✅ Selected {len(selected)} mirror(s)")
            return selected
        else:
            typer.echo("\n❌ No valid mirrors selected")
            raise typer.Exit(1)

    except ValueError:
        typer.echo("\n❌ Invalid selection format")
        typer.echo("   Expected: numbers (1,2,3) or ranges (1-3) or 'all'")
        raise typer.Exit(1)


def update_mirrors_command(
    repo: Annotated[
        Optional[str],
        typer.Option(
            "--repo",
            "-r",
            help="Specific repository to update (owner/repo)",
            autocompletion=complete_repository,
        ),
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

    # Handle scan option separately - just scan and display, don't update
    if scan:
        typer.echo("\n🔍 Scanning GitHub for mirror repositories...")
        org = config["github"].get("default_org")
        mirrors = scan_for_mirrors(username, org)

        if not mirrors:
            typer.echo("\n❌ No mirror repositories found")
            typer.echo(
                "\n💡 Make sure you have mirror repositories with .github/workflows/mirror-sync.yml"
            )
            raise typer.Exit(0)

        # Display found mirrors
        typer.echo(f"\n✅ Found {len(mirrors)} mirror repositories:")
        typer.echo("=" * 70)

        for i, mirror in enumerate(mirrors, 1):
            mirror_name = mirror.get("name", "Unknown")
            is_private = mirror.get("is_private", False)
            description = mirror.get("description", "")
            updated_at = mirror.get("updated_at", "")

            # Format visibility
            visibility = "🔒" if is_private else "🌐"

            typer.echo(f"\n  [{i}] {visibility} {mirror_name}")

            # Show description if available
            if description:
                typer.echo(f"      📝 {description}")

            # Try to get upstream info
            upstream = mirror.get("upstream", "")
            if upstream and upstream != "":
                typer.echo(f"      🔗 Upstream: {upstream}")
            else:
                typer.echo("      🔗 Upstream: (configured via secrets)")

            # Show last updated
            if updated_at:
                try:
                    # Parse and format date
                    from datetime import datetime

                    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                    typer.echo(f"      🕐 Updated: {formatted_date}")
                except Exception:
                    pass

        typer.echo("\n" + "=" * 70)
        typer.echo("\n💡 To update these mirrors:")
        typer.echo("   • Update all: cli-git update-mirrors --all")
        typer.echo("   • Update specific: cli-git update-mirrors --repo <name>")
        typer.echo("   • Interactive selection: cli-git update-mirrors")

        # Exit after displaying scan results
        raise typer.Exit(0)

    # Find mirrors to update
    typer.echo("\n🔍 Finding mirrors to update...")

    if repo:
        # Specific repository
        mirrors = [{"mirror": f"https://github.com/{repo}", "upstream": "", "name": repo}]
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
