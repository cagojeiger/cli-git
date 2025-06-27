"""GitHub Actions workflow generation for mirror synchronization."""


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
    outputs:
      has_conflicts: ${{{{ steps.sync.outputs.has_conflicts }}}}
      pr_url: ${{{{ steps.pr.outputs.pr_url }}}}

    steps:
      - name: Checkout mirror repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{{{ secrets.GITHUB_TOKEN }}}}

      - name: Configure git
        run: |
          git config user.name "Mirror Bot"
          git config user.email "mirror-bot@users.noreply.github.com"

      - name: Sync with rebase
        id: sync
        env:
          UPSTREAM_URL: ${{{{ secrets.UPSTREAM_URL }}}}
          GH_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: |
          echo "Adding upstream remote..."
          git remote add upstream $UPSTREAM_URL || git remote set-url upstream $UPSTREAM_URL

          echo "Fetching from upstream..."
          git fetch upstream

          echo "Attempting rebase..."
          if git rebase upstream/main; then
            echo "✅ Rebase successful, pushing to main"
            git push origin main --force-with-lease
            echo "has_conflicts=false" >> $GITHUB_OUTPUT
          else
            echo "❌ Rebase conflicts detected"
            echo "has_conflicts=true" >> $GITHUB_OUTPUT
            git rebase --abort
          fi

      - name: Create PR if conflicts
        if: steps.sync.outputs.has_conflicts == 'true'
        id: pr
        env:
          GH_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: |
          # Create branch for conflict resolution
          BRANCH_NAME="sync/upstream-$(date +%Y%m%d-%H%M%S)"
          git checkout -b $BRANCH_NAME

          # Add upstream as remote and fetch
          git fetch upstream

          # Try merge instead of rebase for conflict resolution
          git merge upstream/main --no-edit || true

          # Commit the conflict state
          git add -A
          git commit -m "🔴 Merge conflict from upstream - manual resolution required" || true
          git push origin $BRANCH_NAME

          # Create PR
          PR_URL=$(gh pr create \\
            --title "🔴 [Conflict] Sync from upstream" \\
            --body "⚠️ Merge conflicts detected. Please resolve manually and merge." \\
            --base main \\
            --head $BRANCH_NAME)

          echo "pr_url=$PR_URL" >> $GITHUB_OUTPUT

      - name: Sync tags
        if: steps.sync.outputs.has_conflicts == 'false'
        run: |
          echo "Syncing tags..."
          git fetch upstream --tags
          git push origin --tags

  notify-slack:
    needs: sync
    if: needs.sync.outputs.has_conflicts == 'true' && secrets.SLACK_WEBHOOK_URL != ''
    runs-on: ubuntu-latest

    steps:
      - name: Send Slack notification
        uses: slackapi/slack-github-action@v2.0.0
        with:
          webhook: ${{{{ secrets.SLACK_WEBHOOK_URL }}}}
          webhook-type: incoming-webhook
          payload: |
            {{
              "text": "⚠️ Mirror sync conflict detected",
              "blocks": [
                {{
                  "type": "section",
                  "text": {{
                    "type": "mrkdwn",
                    "text": "*⚠️ Mirror Sync Conflict*\\nManual intervention required"
                  }}
                }},
                {{
                  "type": "section",
                  "text": {{
                    "type": "mrkdwn",
                    "text": "*Repository:* `${{{{ github.repository }}}}`\\n*PR:* <${{{{ needs.sync.outputs.pr_url }}}}|View Pull Request>"
                  }}
                }}
              ]
            }}
"""
    return workflow_yaml
