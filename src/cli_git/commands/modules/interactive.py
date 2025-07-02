"""Interactive mirror selection functionality."""

from typing import Dict, List

import typer

from cli_git.utils.git import extract_repo_info


def select_mirrors_interactive(mirrors: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Interactively select mirrors to update.

    Args:
        mirrors: List of mirror dictionaries

    Returns:
        Selected mirrors
    """
    if not mirrors:
        return []

    _display_mirrors(mirrors)
    selection = _get_user_selection()

    return _process_selection(selection, mirrors)


def _display_mirrors(mirrors: List[Dict[str, str]]) -> None:
    """Display mirrors in a formatted list.

    Args:
        mirrors: List of mirror dictionaries
    """
    typer.echo("\n📋 Found mirror repositories:")
    typer.echo("=" * 60)

    for i, mirror in enumerate(mirrors, 1):
        mirror_name = _get_mirror_name(mirror)
        upstream_display = _get_upstream_display(mirror)

        typer.echo(f"\n  [{i}] 🔄 {mirror_name}")
        typer.echo(f"      └─ Mirrors: {upstream_display}")

    typer.echo("\n" + "=" * 60)
    typer.echo("\n💡 Options:")
    typer.echo("  • Enter numbers to select specific mirrors (e.g., 1,3,5)")
    typer.echo("  • Type 'all' to update all mirrors")
    typer.echo("  • Press Enter to update all (default)")
    typer.echo("  • Type 'none' or 'q' to cancel")


def _get_mirror_name(mirror: Dict[str, str]) -> str:
    """Extract mirror repository name.

    Args:
        mirror: Mirror dictionary

    Returns:
        Repository name
    """
    mirror_name = mirror.get("name", "")
    if mirror_name:
        return mirror_name

    # Try to extract from URL
    try:
        _, repo_part = extract_repo_info(mirror["mirror"])
        owner = mirror["mirror"].split("/")[-2]
        return f"{owner}/{repo_part}"
    except Exception:
        return "Unknown"


def _get_upstream_display(mirror: Dict[str, str]) -> str:
    """Get display name for upstream repository.

    Args:
        mirror: Mirror dictionary

    Returns:
        Upstream display name
    """
    upstream = mirror.get("upstream", "")

    if not upstream:
        return "Unknown"

    if "github.com/" not in upstream:
        return upstream

    try:
        parts = upstream.split("github.com/")[-1].split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return upstream
    except Exception:
        return upstream


def _get_user_selection() -> str:
    """Get user's selection input.

    Returns:
        User input string
    """
    return typer.prompt("\n📝 Your selection", default="all")


def _process_selection(selection: str, mirrors: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Process user selection and return selected mirrors.

    Args:
        selection: User input string
        mirrors: Available mirrors

    Returns:
        Selected mirrors
    """
    # Handle special cases
    if selection.lower() in ["all", ""]:
        typer.echo(f"\n✅ Selected all {len(mirrors)} mirrors")
        return mirrors

    if selection.lower() in ["none", "q", "quit", "exit"]:
        typer.echo("\n❌ Update cancelled")
        raise typer.Exit(0)

    # Parse number selection
    try:
        indices = _parse_numeric_selection(selection)
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


def _parse_numeric_selection(selection: str) -> List[int]:
    """Parse numeric selection string into list of indices.

    Args:
        selection: Selection string (e.g., "1,3-5,7")

    Returns:
        List of 0-based indices
    """
    indices = []

    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            # Handle range
            start, end = part.split("-")
            start, end = int(start.strip()), int(end.strip())
            indices.extend(range(start - 1, end))  # Convert to 0-based
        else:
            # Single number
            indices.append(int(part) - 1)  # Convert to 0-based

    return indices
