"""Update existing mirror repositories with current settings.

This module now imports from the refactored update submodules.
"""

import subprocess

import typer

# Re-export dependencies that tests might need
from cli_git.commands.modules.scan import scan_for_mirrors
from cli_git.commands.modules.workflow_updater import update_workflow_file

# Re-export other commonly used functions for backward compatibility
from cli_git.commands.update import (
    MirrorUpdateResult,
    check_mirror_sync_exists,
    check_update_prerequisites,
    display_scan_results,
    extract_mirror_repo_name,
    find_mirrors_to_update,
    handle_scan_option,
    update_mirror_secrets,
    update_mirrors_batch,
    update_single_mirror,
)

# Re-export the main command from the new update workflow module
from cli_git.commands.update.update_workflow import update_mirrors_command
from cli_git.utils.config import ConfigManager
from cli_git.utils.gh import (
    add_repo_secret,
    check_gh_auth,
    get_current_username,
    get_upstream_default_branch,
)

# Create aliases for renamed functions to maintain backward compatibility
_handle_scan_option = handle_scan_option
_display_scan_results = display_scan_results
_find_mirrors_to_update = find_mirrors_to_update
_update_mirrors = update_mirrors_batch

__all__ = [
    "update_mirrors_command",
    "MirrorUpdateResult",
    "check_mirror_sync_exists",
    "extract_mirror_repo_name",
    "update_mirror_secrets",
    "update_single_mirror",
    "check_update_prerequisites",
    "handle_scan_option",
    "find_mirrors_to_update",
    "display_scan_results",
    "update_mirrors_batch",
    "scan_for_mirrors",
    "subprocess",
    "typer",
    "_handle_scan_option",
    "_display_scan_results",
    "_find_mirrors_to_update",
    "_update_mirrors",
    "update_workflow_file",
    "check_gh_auth",
    "get_current_username",
    "add_repo_secret",
    "get_upstream_default_branch",
    "ConfigManager",
]
