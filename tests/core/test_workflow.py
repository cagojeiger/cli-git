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
        assert sync_step["name"] == "Sync with reset"
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
        assert "git reset --hard upstream/$DEFAULT_BRANCH" in workflow_yaml
        assert "git push origin $CURRENT_BRANCH --force" in workflow_yaml
        assert "git push origin --tags" in workflow_yaml
        assert "GH_TOKEN" in workflow_yaml

    def test_no_conflict_with_reset(self):
        """Test that reset approach doesn't have conflict handling."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Check that conflict handling is removed
        assert "has_conflicts=true" not in workflow_yaml
        assert "has_conflicts=false" in workflow_yaml  # Always false with reset
        assert "gh pr create" not in workflow_yaml
        assert "notify-slack-conflict" not in workflow_yaml
        # But failure notification should still exist
        assert "notify-slack-failure" in workflow_yaml

    def test_gh_token_configuration(self):
        """Test that GH_TOKEN is properly configured for tag syncing."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Check GH_TOKEN usage in tag sync
        lines = workflow_yaml.split("\n")

        # Find the Sync tags section
        tag_sync_found = False
        gh_token_env_found = False
        for i, line in enumerate(lines):
            if "- name: Sync tags" in line:
                tag_sync_found = True
            if tag_sync_found and "GH_TOKEN: ${{ secrets.GH_TOKEN }}" in line:
                gh_token_env_found = True
                break

        assert tag_sync_found, "Sync tags section not found"
        assert gh_token_env_found, "GH_TOKEN environment variable not found in tag sync"
        assert 'if [ -n "$GH_TOKEN" ]; then' in workflow_yaml
        assert "x-access-token:${GH_TOKEN}@github.com" in workflow_yaml

    def test_sync_uses_reset_not_rebase(self):
        """Test that sync uses reset --hard instead of rebase."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Should use reset --hard
        assert "git reset --hard upstream/$DEFAULT_BRANCH" in workflow_yaml
        # Should NOT use rebase
        assert "git rebase upstream/$DEFAULT_BRANCH" not in workflow_yaml

    def test_backup_includes_custom_files_list(self):
        """Test that backup saves list of custom user files."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Should detect custom files
        assert 'find .github -type f ! -name "mirror-sync.yml"' in workflow_yaml
        # Should save list to file
        assert "$BACKUP_DIR/custom_files.txt" in workflow_yaml

    def test_restore_preserves_custom_files(self):
        """Test that restore process preserves user's custom files."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Should have custom file restore logic
        assert "Restoring custom files..." in workflow_yaml
        assert "while IFS= read -r file" in workflow_yaml
        assert "Restored: $file" in workflow_yaml

    def test_no_conflict_handling(self):
        """Test that conflict handling is removed since reset doesn't create conflicts."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Should NOT have conflict PR creation
        assert "Create PR if conflicts" not in workflow_yaml
        # Should NOT have slack notification for conflicts
        assert "notify-slack-conflict" not in workflow_yaml
        # Should NOT set has_conflicts=true
        assert "has_conflicts=true" not in workflow_yaml

    def test_force_push_after_reset(self):
        """Test that force push is used after reset."""
        workflow_yaml = generate_sync_workflow(
            upstream_url="https://github.com/owner/repo",
            schedule="0 0 * * *",
            upstream_default_branch="main",
        )

        # Should use force push (not force-with-lease)
        assert "git push origin $CURRENT_BRANCH --force" in workflow_yaml
        # Should NOT use force-with-lease which can fail after reset
        assert "--force-with-lease" not in workflow_yaml
