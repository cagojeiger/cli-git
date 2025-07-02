"""Create a private mirror of a public repository.

This module now imports from the refactored mirror submodules.
"""

from cli_git.commands.git_operations import push_workflow_branch

# Re-export other commonly used functions for backward compatibility
from cli_git.commands.mirror import (
    MirrorConfig,
    check_prerequisites,
    clean_github_directory,
    display_success_message,
    prepare_mirror_config,
    private_mirror_operation,
    resolve_mirror_parameters,
    save_mirror_info,
    setup_mirror_sync,
    validate_mirror_inputs,
)

# Re-export the main command from the new mirror workflow module
from cli_git.commands.mirror.mirror_workflow import private_mirror_command
from cli_git.utils.config import ConfigManager

# Re-export dependencies that tests might need
from cli_git.utils.gh import (
    check_gh_auth,
    create_private_repo,
    get_current_username,
    get_upstream_default_branch,
)
from cli_git.utils.git import extract_repo_info
from cli_git.utils.validators import validate_cron_schedule, validate_github_url

__all__ = [
    "private_mirror_command",
    "MirrorConfig",
    "clean_github_directory",
    "private_mirror_operation",
    "setup_mirror_sync",
    "check_prerequisites",
    "validate_mirror_inputs",
    "resolve_mirror_parameters",
    "prepare_mirror_config",
    "save_mirror_info",
    "display_success_message",
    "check_gh_auth",
    "validate_cron_schedule",
    "validate_github_url",
    "get_current_username",
    "get_upstream_default_branch",
    "push_workflow_branch",
    "create_private_repo",
    "ConfigManager",
    "extract_repo_info",
]
