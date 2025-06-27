"""GitHub Actions workflow generation."""


def generate_sync_workflow(upstream_url: str, schedule: str) -> str:
    """Generate GitHub Actions workflow for mirror synchronization.

    Args:
        upstream_url: URL of the upstream repository
        schedule: Cron schedule for synchronization

    Returns:
        YAML content for the workflow file
    """
    workflow_yaml = f"""name: Mirror Sync
'on':
  schedule:
    - cron: '{schedule}'
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Sync with upstream
        env:
          UPSTREAM_URL: ${{{{ secrets.UPSTREAM_URL }}}}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          # Add upstream remote
          git remote add upstream $UPSTREAM_URL
          git fetch upstream

          # Sync main branch
          git checkout main
          git merge upstream/main --ff-only || exit 0
          git push origin main

          # Sync all branches
          for branch in $(git branch -r | grep upstream | grep -v HEAD); do
            local_branch=${{branch#upstream/}}
            git checkout -B $local_branch $branch || continue
            git push origin $local_branch
          done

          # Sync tags
          git push origin --tags
"""
    return workflow_yaml
