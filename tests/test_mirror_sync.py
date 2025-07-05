"""Tests for mirror sync workflow generation."""

import pytest

from cli_git.core.workflow import generate_sync_workflow


class TestMirrorSyncWorkflow:
    """Test cases for mirror sync workflow."""

    def test_workflow_basic_structure(self):
        """Test that workflow has correct basic structure."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Check basic workflow elements
        assert "name: Mirror Sync" in workflow
        assert "schedule:" in workflow
        assert "cron: '0 2 * * *'" in workflow
        assert "workflow_dispatch:" in workflow

        # Check permissions
        assert "permissions:" in workflow
        assert "contents: write" in workflow

        # Check main steps
        assert "Checkout mirror repository" in workflow
        assert "Identify and backup mirror-only files" in workflow
        assert "Complete sync from upstream" in workflow
        assert "Apply mirror customizations" in workflow
        assert "Push changes" in workflow
        assert "Sync tags" in workflow

    def test_workflow_uses_secrets(self):
        """Test that workflow properly references secrets."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Check secret references
        assert "${{ secrets.GH_TOKEN }}" in workflow
        assert "${{ secrets.UPSTREAM_URL }}" in workflow
        assert "${{ secrets.UPSTREAM_DEFAULT_BRANCH }}" in workflow

    def test_mirror_file_preservation_logic(self):
        """Test that workflow includes logic to preserve mirror-only files."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Check mirror file detection
        assert "comm -23" in workflow
        assert "mirror-only-files.txt" in workflow

        # Check backup logic
        assert "mkdir -p /tmp/mirror-backup" in workflow
        assert "while IFS= read -r file" in workflow

        # Check restore logic
        assert "Restoring mirror-only files" in workflow

        # Check file removal logic
        assert "operator.yml" in workflow
        assert "registry-push.yml" in workflow

    def test_workflow_handles_edge_cases(self):
        """Test workflow handles edge cases properly."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="develop",  # Non-main branch
        )

        # Check branch detection logic
        assert "git ls-remote --symref upstream HEAD" in workflow
        assert "${DEFAULT_BRANCH:-$UPSTREAM_DEFAULT_BRANCH}" in workflow

        # Check error handling
        assert "if [ -s /tmp/mirror-backup/mirror-only-files.txt ]" in workflow
        assert "No changes to commit" in workflow

    def test_workflow_commit_message(self):
        """Test that workflow generates informative commit messages."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Check commit message includes file count
        assert "MIRROR_FILES=$(wc -l < /tmp/mirror-backup/mirror-only-files.txt)" in workflow
        assert "preserve $MIRROR_FILES mirror-only files" in workflow

    def test_workflow_force_push_safety(self):
        """Test that workflow uses safe force push."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Should use force-with-lease for safety
        assert "--force-with-lease" in workflow
        # Tags can use regular force
        assert "push origin --tags --force" in workflow

    def test_slack_notification_conditional(self):
        """Test that Slack notifications are conditional."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Check Slack webhook is checked before use
        assert "if: env.SLACK_WEBHOOK_URL != ''" in workflow
        assert "SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}" in workflow

    @pytest.mark.parametrize(
        "schedule,expected",
        [
            ("0 2 * * *", "cron: '0 2 * * *'"),
            ("*/15 * * * *", "cron: '*/15 * * * *'"),
            ("0 0 * * 0", "cron: '0 0 * * 0'"),
        ],
    )
    def test_workflow_schedule_variations(self, schedule, expected):
        """Test workflow handles different schedule formats."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule=schedule,
            upstream_default_branch="main",
        )

        assert expected in workflow

    def test_workflow_yaml_escaping(self):
        """Test that special characters are properly escaped."""
        workflow = generate_sync_workflow(
            upstream_url="https://github.com/example/upstream.git",
            schedule="0 2 * * *",
            upstream_default_branch="main",
        )

        # Check GitHub expressions are properly formatted
        assert "${{ secrets" in workflow  # GitHub secrets syntax
        assert "${{ github" in workflow  # GitHub context syntax

        # Check shell variables are not over-escaped
        assert "$(wc -l" in workflow  # Shell command substitution
        assert "${DEFAULT_BRANCH" in workflow  # Shell variable


class TestWorkflowIntegration:
    """Integration tests for the workflow in a real Git environment."""

    @pytest.mark.integration
    def test_workflow_in_git_environment(self, tmp_path):
        """Test workflow logic in an actual Git environment."""
        # This would require actual Git operations
        # Marked as integration test to be run separately
        pass
