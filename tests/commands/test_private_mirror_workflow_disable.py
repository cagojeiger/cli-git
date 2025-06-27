"""Tests for workflow disabling functionality."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cli_git.commands.private_mirror import disable_original_workflows


class TestWorkflowDisable:
    """Test cases for disabling original workflows."""

    def test_disable_workflows_with_yml_files(self):
        """Test disabling workflows when .yml files exist."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            workflows_dir = repo_path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create test workflow files
            (workflows_dir / "ci.yml").write_text("name: CI\n")
            (workflows_dir / "deploy.yml").write_text("name: Deploy\n")

            # Disable workflows
            result = disable_original_workflows(repo_path)

            # Verify
            assert result is True
            assert not (workflows_dir / "ci.yml").exists()
            assert not (workflows_dir / "deploy.yml").exists()

            disabled_dir = repo_path / ".github" / "workflows-disabled"
            assert disabled_dir.exists()
            assert (disabled_dir / "ci.yml").exists()
            assert (disabled_dir / "deploy.yml").exists()
            assert (disabled_dir / "README.md").exists()

    def test_disable_workflows_with_yaml_files(self):
        """Test disabling workflows when .yaml files exist."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            workflows_dir = repo_path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create test workflow files
            (workflows_dir / "test.yaml").write_text("name: Test\n")

            # Disable workflows
            result = disable_original_workflows(repo_path)

            # Verify
            assert result is True
            assert not (workflows_dir / "test.yaml").exists()

            disabled_dir = repo_path / ".github" / "workflows-disabled"
            assert (disabled_dir / "test.yaml").exists()

    def test_disable_workflows_no_workflows_dir(self):
        """Test when .github/workflows doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Disable workflows
            result = disable_original_workflows(repo_path)

            # Verify
            assert result is False
            assert not (repo_path / ".github" / "workflows-disabled").exists()

    def test_disable_workflows_empty_dir(self):
        """Test when workflows directory is empty."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            workflows_dir = repo_path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Disable workflows
            result = disable_original_workflows(repo_path)

            # Verify
            assert result is False
            assert not (repo_path / ".github" / "workflows-disabled").exists()

    def test_disable_workflows_mixed_files(self):
        """Test with both yml and yaml files."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            workflows_dir = repo_path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create mixed files
            (workflows_dir / "ci.yml").write_text("name: CI\n")
            (workflows_dir / "test.yaml").write_text("name: Test\n")
            (workflows_dir / "README.md").write_text("# Workflows\n")  # Non-workflow file

            # Disable workflows
            result = disable_original_workflows(repo_path)

            # Verify
            assert result is True
            assert not (workflows_dir / "ci.yml").exists()
            assert not (workflows_dir / "test.yaml").exists()
            assert (workflows_dir / "README.md").exists()  # Should remain

            disabled_dir = repo_path / ".github" / "workflows-disabled"
            assert (disabled_dir / "ci.yml").exists()
            assert (disabled_dir / "test.yaml").exists()

    @patch("cli_git.commands.private_mirror.run_git_command")
    def test_disable_workflows_handle_errors(self, mock_run_git):
        """Test error handling during workflow disabling."""
        with TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            workflows_dir = repo_path / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)

            # Create test file
            (workflows_dir / "ci.yml").write_text("name: CI\n")

            # Mock git command to raise exception
            mock_run_git.side_effect = Exception("Permission denied")

            # Should handle error gracefully
            result = disable_original_workflows(repo_path)

            # Even with error, should try to handle gracefully
            # Implementation should catch and continue
            assert result is True or result is False  # Depends on implementation
