"""Tests for clean_github_directory functionality."""

from pathlib import Path
from tempfile import TemporaryDirectory

from cli_git.commands.private_mirror import clean_github_directory


class TestCleanGitHubDirectory:
    """Test cases for cleaning .github directory."""

    def test_clean_github_directory_exists(self):
        """Test removing .github directory when it exists."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            github_dir = repo_path / ".github"
            workflows_dir = github_dir / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create test files
            (workflows_dir / "ci.yml").write_text("name: CI\n")
            (github_dir / "CODEOWNERS").write_text("* @owner\n")
            (github_dir / "pull_request_template.md").write_text("# PR Template\n")

            # Clean .github directory
            result = clean_github_directory(repo_path)

            # Verify
            assert result is True
            assert not github_dir.exists()

    def test_clean_github_directory_not_exists(self):
        """Test when .github directory doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Clean .github directory
            result = clean_github_directory(repo_path)

            # Verify
            assert result is False

    def test_clean_github_directory_with_subdirs(self):
        """Test removing .github with multiple subdirectories."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            github_dir = repo_path / ".github"

            # Create multiple subdirectories
            (github_dir / "workflows").mkdir(parents=True)
            (github_dir / "ISSUE_TEMPLATE").mkdir(parents=True)
            (github_dir / "actions" / "setup").mkdir(parents=True)

            # Create files
            (github_dir / "workflows" / "ci.yml").write_text("name: CI\n")
            (github_dir / "ISSUE_TEMPLATE" / "bug.md").write_text("# Bug\n")
            (github_dir / "actions" / "setup" / "action.yml").write_text("name: Setup\n")

            # Clean .github directory
            result = clean_github_directory(repo_path)

            # Verify
            assert result is True
            assert not github_dir.exists()

    def test_clean_github_directory_handle_errors(self):
        """Test error handling during directory removal."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            github_dir = repo_path / ".github"
            github_dir.mkdir()

            # Create a file
            (github_dir / "test.yml").write_text("test")

            # Make directory read-only to simulate error
            import os
            import stat

            # Remove write permissions
            os.chmod(github_dir, stat.S_IRUSR | stat.S_IXUSR)

            try:
                # Should handle error gracefully
                result = clean_github_directory(repo_path)

                # Should return False on error
                assert result is False
            finally:
                # Restore permissions for cleanup
                os.chmod(github_dir, stat.S_IRWXU)
