"""Tests for GitHub Actions workflow generation."""

import yaml

from cli_git.core.workflow import generate_sync_workflow


class TestWorkflow:
    """Test cases for workflow generation."""

    def test_generate_sync_workflow_basic(self):
        """Test basic workflow generation."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo", schedule="0 0 * * *"
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

        # Check sync step
        sync_step = steps[1]
        assert sync_step["name"] == "Sync with upstream"
        assert "UPSTREAM_URL" in sync_step["env"]
        assert sync_step["env"]["UPSTREAM_URL"] == "${{ secrets.UPSTREAM_URL }}"

    def test_generate_sync_workflow_custom_schedule(self):
        """Test workflow generation with custom schedule."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo", schedule="0 */6 * * *"  # Every 6 hours
        )

        workflow = yaml.safe_load(workflow_yaml)
        assert workflow["on"]["schedule"][0]["cron"] == "0 */6 * * *"

    def test_sync_script_content(self):
        """Test that sync script contains correct commands."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo", schedule="0 0 * * *"
        )

        # Check for important commands in the script
        assert "git config user.name" in workflow_yaml
        assert "git config user.email" in workflow_yaml
        assert "git remote add upstream $UPSTREAM_URL" in workflow_yaml
        assert "git fetch upstream" in workflow_yaml
        assert "git checkout main" in workflow_yaml
        assert "git merge upstream/main --ff-only" in workflow_yaml
        assert "git push origin main" in workflow_yaml
        assert "git push origin --tags" in workflow_yaml

    def test_branch_sync_logic(self):
        """Test that branch synchronization logic is present."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo", schedule="0 0 * * *"
        )

        # Check for branch sync loop
        assert "for branch in $(git branch -r | grep upstream | grep -v HEAD)" in workflow_yaml
        assert "local_branch=${branch#upstream/}" in workflow_yaml
        assert "git checkout -B $local_branch $branch" in workflow_yaml
        assert "git push origin $local_branch" in workflow_yaml
