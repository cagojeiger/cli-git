"""Mirrorkeep file parsing and pattern matching functionality."""

import fnmatch
from pathlib import Path
from typing import List


def parse_mirrorkeep(content: str) -> List[str]:
    """Parse .mirrorkeep file content and return list of patterns.

    Args:
        content: Content of .mirrorkeep file

    Returns:
        List of patterns (including exclusions with ! prefix)
    """
    patterns = []

    for line in content.strip().split("\n"):
        # Remove leading/trailing whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        patterns.append(line)

    return patterns


def match_pattern(file_path: str, patterns: List[str]) -> bool:
    """Check if a file path matches the given patterns.

    Args:
        file_path: Path to check (relative)
        patterns: List of patterns (may include exclusions with !)

    Returns:
        True if file matches and is not excluded
    """
    # Normalize path separators
    file_path = file_path.replace("\\", "/")

    # Separate inclusion and exclusion patterns
    includes = []
    excludes = []

    for pattern in patterns:
        if pattern.startswith("!"):
            excludes.append(pattern[1:])
        else:
            includes.append(pattern)

    # Check exclusions first (they take priority)
    for exclude in excludes:
        if _match_single_pattern(file_path, exclude):
            return False

    # Check inclusions
    for include in includes:
        if _match_single_pattern(file_path, include):
            return True

    return False


def _match_single_pattern(file_path: str, pattern: str) -> bool:
    """Match a single pattern against a file path.

    Handles:
    - Directory patterns (ending with /)
    - Wildcard patterns (*, **)
    - Exact matches
    """
    # Normalize pattern
    pattern = pattern.replace("\\", "/")

    # Directory pattern - matches any file under that directory
    if pattern.endswith("/"):
        return file_path.startswith(pattern) or file_path + "/" == pattern

    # Handle ** glob pattern
    if "**" in pattern:
        # Convert ** to match any number of directories
        # e.g., "docs/**/*.md" matches "docs/api/reference.md"
        import re

        # First replace ** with a placeholder to avoid conflicts
        regex_pattern = pattern.replace("**", "\x00")
        # Replace single * with [^/]* (matches anything except /)
        regex_pattern = regex_pattern.replace("*", "[^/]*")
        # Replace placeholder with .* (matches anything including /)
        regex_pattern = regex_pattern.replace("\x00", ".*")
        regex_pattern = "^" + regex_pattern + "$"
        return bool(re.match(regex_pattern, file_path))

    # For patterns without **, check if pattern contains /
    if "/" not in pattern:
        # Pattern is for files in root directory only
        # e.g., "*.md" should not match "docs/guide.md"
        if "/" in file_path:
            return False

    # Standard fnmatch for other patterns
    return fnmatch.fnmatch(file_path, pattern)


def get_files_to_preserve(root: Path, patterns: List[str]) -> List[Path]:
    """Get list of files that match the preservation patterns.

    Args:
        root: Root directory to search
        patterns: List of patterns from .mirrorkeep

    Returns:
        List of absolute paths to preserve
    """
    files_to_preserve = []

    # Walk through all files in the directory
    for path in root.rglob("*"):
        # Skip directories - we only preserve files
        if path.is_dir():
            continue

        # Get relative path for pattern matching
        try:
            relative_path = path.relative_to(root)
            relative_str = str(relative_path).replace("\\", "/")

            # Check if file matches patterns
            if match_pattern(relative_str, patterns):
                files_to_preserve.append(path)
        except ValueError:
            # Path is not relative to root, skip it
            continue

    return sorted(files_to_preserve)


def create_default_mirrorkeep() -> str:
    """Create default .mirrorkeep content.

    Returns:
        Default .mirrorkeep file content
    """
    return """# .mirrorkeep - Files to preserve during mirror sync
#
# This file uses gitignore syntax:
# - One pattern per line
# - Lines starting with # are comments
# - Lines starting with ! are exclusions
# - Patterns ending with / match directories
#
# HOW IT WORKS:
# 1. Before syncing with upstream, files matching these patterns are backed up
# 2. The repository is reset to match upstream (git reset --hard)
# 3. Backed up files are restored, preserving your local modifications
# 4. If a file doesn't exist, it's silently skipped (no error)
# 5. Modified files always take precedence over upstream versions
#
# Examples:
#   *.md              # All markdown files in root directory
#   .docs/**          # Everything under .docs/
#   !README.md        # Exclude README.md (upstream version will be used)
#   config.json       # Specific file (your version preserved)

# Essential files for mirror operation
.github/workflows/mirror-sync.yml
.mirrorkeep

# Optional: Add your custom patterns below
# CLAUDE.md
# .docs/**
# .claude/
# .local/**
# .vscode/
# .github/workflows/custom-*.yml
"""
