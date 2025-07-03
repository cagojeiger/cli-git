"""Tests for git operations module."""

import subprocess
from pathlib import Path
from unittest.mock import call, patch

from cli_git.commands.git_operations import (
    clone_repository,
    commit_changes,
    push_to_mirror,
    push_workflow_branch,
    setup_remotes,
)


class TestCloneRepository:
    """Tests for clone_repository function."""

    @patch("cli_git.commands.git_operations.run_git_command")
    def test_clone_repository_success(self, mock_run_git):
        """Test successful repository cloning."""
        upstream_url = "https://github.com/user/repo.git"
        target_path = Path("/tmp/repo")

        clone_repository(upstream_url, target_path)

        mock_run_git.assert_called_once_with(f"clone {upstream_url} {target_path}")


class TestSetupRemotes:
    """Tests for setup_remotes function."""

    @patch("cli_git.commands.git_operations.run_git_command")
    def test_setup_remotes_success(self, mock_run_git):
        """Test successful remote setup."""
        repo_path = Path("/tmp/repo")
        mirror_url = "https://github.com/user/mirror.git"

        setup_remotes(repo_path, mirror_url)

        expected_calls = [
            call("remote rename origin upstream", cwd=repo_path),
            call(f"remote add origin {mirror_url}", cwd=repo_path),
        ]
        mock_run_git.assert_has_calls(expected_calls)


class TestPushToMirror:
    """Tests for push_to_mirror function."""

    @patch("cli_git.commands.git_operations.run_git_command")
    def test_push_to_mirror_success(self, mock_run_git):
        """Test successful push to mirror."""
        repo_path = Path("/tmp/repo")

        push_to_mirror(repo_path)

        expected_calls = [
            call("push origin --all", cwd=repo_path),
            call("push origin --tags", cwd=repo_path),
        ]
        mock_run_git.assert_has_calls(expected_calls)


class TestCommitChanges:
    """Tests for commit_changes function."""

    @patch("cli_git.commands.git_operations.run_git_command")
    def test_commit_changes_success(self, mock_run_git):
        """Test successful commit."""
        repo_path = Path("/tmp/repo")
        message = "Add workflow file"

        commit_changes(repo_path, message)

        expected_calls = [
            call("add -A", cwd=repo_path),
            call(f'commit -m "{message}"', cwd=repo_path),
        ]
        mock_run_git.assert_has_calls(expected_calls)


class TestPushWorkflowBranch:
    """Tests for push_workflow_branch function."""

    @patch("cli_git.commands.git_operations.get_default_branch")
    @patch("cli_git.commands.git_operations.run_git_command")
    def test_push_workflow_branch_default_success(self, mock_run_git, mock_get_branch):
        """Test successful push to default branch."""
        repo_path = Path("/tmp/repo")
        mock_get_branch.return_value = "main"

        push_workflow_branch(repo_path)

        mock_get_branch.assert_called_once_with(repo_path)
        mock_run_git.assert_called_once_with("push origin main", cwd=repo_path)

    @patch("cli_git.commands.git_operations.get_default_branch")
    @patch("cli_git.commands.git_operations.run_git_command")
    def test_push_workflow_branch_fallback_main(self, mock_run_git, mock_get_branch):
        """Test fallback to main branch when default detection fails."""
        repo_path = Path("/tmp/repo")
        mock_get_branch.side_effect = subprocess.CalledProcessError(1, "git")

        # First call (main) succeeds
        mock_run_git.side_effect = [None]

        push_workflow_branch(repo_path)

        mock_get_branch.assert_called_once_with(repo_path)
        mock_run_git.assert_called_once_with("push origin main", cwd=repo_path)

    @patch("cli_git.commands.git_operations.get_default_branch")
    @patch("cli_git.commands.git_operations.run_git_command")
    def test_push_workflow_branch_fallback_master(self, mock_run_git, mock_get_branch):
        """Test fallback to master branch when main fails."""
        repo_path = Path("/tmp/repo")
        mock_get_branch.side_effect = subprocess.CalledProcessError(1, "git")

        # First call (main) fails, second call (master) succeeds
        mock_run_git.side_effect = [
            subprocess.CalledProcessError(1, "git"),  # main fails
            None,  # master succeeds
        ]

        push_workflow_branch(repo_path)

        expected_calls = [
            call("push origin main", cwd=repo_path),
            call("push origin master", cwd=repo_path),
        ]
        mock_run_git.assert_has_calls(expected_calls)

    @patch("cli_git.commands.git_operations.get_default_branch")
    @patch("cli_git.commands.git_operations.run_git_command")
    def test_push_workflow_branch_fallback_head(self, mock_run_git, mock_get_branch):
        """Test ultimate fallback to HEAD when all branches fail."""
        repo_path = Path("/tmp/repo")
        mock_get_branch.side_effect = subprocess.CalledProcessError(1, "git")

        # All specific branches fail, fallback to HEAD
        mock_run_git.side_effect = [
            subprocess.CalledProcessError(1, "git"),  # main fails
            subprocess.CalledProcessError(1, "git"),  # master fails
            None,  # HEAD succeeds
        ]

        push_workflow_branch(repo_path)

        expected_calls = [
            call("push origin main", cwd=repo_path),
            call("push origin master", cwd=repo_path),
            call("push origin HEAD", cwd=repo_path),
        ]
        mock_run_git.assert_has_calls(expected_calls)
