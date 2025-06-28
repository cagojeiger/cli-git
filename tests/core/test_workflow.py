"""Tests for GitHub Actions workflow generation."""

import yaml

from cli_git.core.workflow import generate_sync_workflow


class TestWorkflow:
    """Test cases for workflow generation."""

    def test_generate_sync_workflow_basic(self):
        """Test basic workflow generation."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Parse YAML
        workflow = yaml.safe_load(workflow_yaml)

        # Check basic structure
        assert workflow["name"] == "Mirror Sync"
        assert "schedule" in workflow["on"]
        assert "workflow_dispatch" in workflow["on"]
        assert workflow["on"]["schedule"][0]["cron"] == "0 0 * * *"

        # Check jobs
        assert "sync" in workflow["jobs"]
        sync_job = workflow["jobs"]["sync"]
        assert sync_job["runs-on"] == "ubuntu-latest"

        # Check steps
        steps = sync_job["steps"]
        assert len(steps) >= 2

        # Check checkout step
        checkout_step = steps[0]
        assert checkout_step["uses"] == "actions/checkout@v4"
        assert checkout_step["with"]["fetch-depth"] == 0

        # Check configure git step
        configure_step = steps[1]
        assert configure_step["name"] == "Configure git"

        # Check sync step
        sync_step = steps[2]
        assert sync_step["name"] == "Sync with rebase"
        assert "UPSTREAM_URL" in sync_step["env"]
        assert sync_step["env"]["UPSTREAM_URL"] == "${{ secrets.UPSTREAM_URL }}"
        assert "UPSTREAM_DEFAULT_BRANCH" in sync_step["env"]
        assert (
            sync_step["env"]["UPSTREAM_DEFAULT_BRANCH"] == "${{ secrets.UPSTREAM_DEFAULT_BRANCH }}"
        )

    def test_generate_sync_workflow_custom_schedule(self):
        """Test workflow generation with custom schedule."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 */6 * * *",  # Every 6 hours
            upstream_default_branch="main",
        )

        workflow = yaml.safe_load(workflow_yaml)
        assert workflow["on"]["schedule"][0]["cron"] == "0 */6 * * *"

    def test_sync_script_content(self):
        """Test that sync script contains correct commands."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Check for important commands in the script
        assert "git config user.name" in workflow_yaml
        assert "git config user.email" in workflow_yaml
        assert "git remote add upstream $UPSTREAM_URL" in workflow_yaml
        assert "git fetch upstream" in workflow_yaml
        assert "git rebase upstream/$DEFAULT_BRANCH" in workflow_yaml
        assert "git push origin $CURRENT_BRANCH --force-with-lease" in workflow_yaml
        assert "git push origin --tags" in workflow_yaml

    def test_conflict_handling(self):
        """Test that conflict handling logic is present."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Check for conflict handling
        assert "has_conflicts=true" in workflow_yaml
        assert "has_conflicts=false" in workflow_yaml
        assert "gh pr create" in workflow_yaml
        assert "notify-slack" in workflow_yaml
