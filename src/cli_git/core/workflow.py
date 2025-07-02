"""GitHub Actions workflow generation for mirror synchronization."""

from pathlib import Path
from string import Template


def generate_sync_workflow(upstream_url: str, schedule: str, upstream_default_branch: str) -> str:
    """Generate GitHub Actions workflow for mirror synchronization.

    Args:
        upstream_url: URL of the upstream repository (kept for compatibility)
        schedule: Cron schedule for synchronization
        upstream_default_branch: Default branch of the upstream repository

    Returns:
        YAML content for the workflow file
    """
    # Load template file
    template_path = Path(__file__).parent.parent / "templates" / "mirror-sync.yml"

    try:
        template_content = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Fallback to inline template if file not found
        template_content = _get_fallback_template()

    # Use Python's Template for simple substitution
    template = Template(template_content)

    return template.substitute(schedule=schedule, upstream_default_branch=upstream_default_branch)


def _get_fallback_template() -> str:
    """Fallback template in case the external file is not found.

    Returns:
        Basic workflow template as string
    """
    return """name: Mirror Sync
'on':
  schedule:
    - cron: '$schedule'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout mirror repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GH_TOKEN }}

      - name: Configure git
        run: |
          git config user.name "Mirror Bot"
          git config user.email "mirror-bot@users.noreply.github.com"

      - name: Sync with upstream
        env:
          UPSTREAM_URL: ${{ secrets.UPSTREAM_URL }}
          UPSTREAM_DEFAULT_BRANCH: ${{ secrets.UPSTREAM_DEFAULT_BRANCH }}
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
        run: |
          git remote add upstream $UPSTREAM_URL || git remote set-url upstream $UPSTREAM_URL
          git fetch upstream
          git rebase upstream/$UPSTREAM_DEFAULT_BRANCH
          git push origin --force-with-lease

      - name: Sync tags
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
        run: |
          git fetch upstream --tags
          git push origin --tags --force"""
