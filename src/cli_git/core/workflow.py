"""GitHub Actions workflow generation for mirror synchronization."""


def generate_sync_workflow(upstream_url: str, schedule: str, upstream_default_branch: str) -> str:
    """Generate GitHub Actions workflow for mirror synchronization.

    Args:
        upstream_url: URL of the upstream repository
        schedule: Cron schedule for synchronization
        upstream_default_branch: Default branch of the upstream repository

    Returns:
        YAML content for the workflow file
    """
    workflow_yaml = f"""name: Mirror Sync
'on':
  schedule:
    - cron: '{schedule}'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

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
          token: ${{{{ secrets.GH_TOKEN }}}}

      - name: Configure git
        run: |
          git config user.name "Mirror Bot"
          git config user.email "mirror-bot@users.noreply.github.com"

      - name: Sync with rebase
        id: sync
        env:
          UPSTREAM_URL: ${{{{ secrets.UPSTREAM_URL }}}}
          UPSTREAM_DEFAULT_BRANCH: ${{{{ secrets.UPSTREAM_DEFAULT_BRANCH }}}}
          GH_TOKEN: ${{{{ secrets.GH_TOKEN }}}}
        run: |
          echo "Adding upstream remote..."
          git remote add upstream $UPSTREAM_URL || git remote set-url upstream $UPSTREAM_URL

          echo "Fetching from upstream..."
          git fetch upstream

          # Get upstream default branch - prefer dynamic detection
          DETECTED_BRANCH=$(git ls-remote --symref upstream HEAD | awk '/^ref:/ {{sub(/refs\\/heads\\//, "", $2); print $2}}')

          if [ -n "$DETECTED_BRANCH" ]; then
            DEFAULT_BRANCH="$DETECTED_BRANCH"
            echo "Detected upstream branch: $DEFAULT_BRANCH"
          elif [ -n "$UPSTREAM_DEFAULT_BRANCH" ]; then
            DEFAULT_BRANCH="$UPSTREAM_DEFAULT_BRANCH"
            echo "Using configured upstream branch: $DEFAULT_BRANCH"
          else
            echo "ERROR: Could not determine upstream default branch"
            exit 1
          fi

          # Get current branch
          CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

          # Save current .github directory
          # Use mktemp for secure temporary directory
          if [ -n "${{{{ runner.temp }}}}" ]; then
            BACKUP_DIR=$(mktemp -d -p "${{{{ runner.temp }}}}" github-backup-XXXXXX)
          else
            BACKUP_DIR=$(mktemp -d /tmp/github-backup-XXXXXX)
          fi
          echo "Backup directory: $BACKUP_DIR"

          if [ -d .github ]; then
            cp -r .github "$BACKUP_DIR/"
          fi

          echo "Attempting rebase..."
          if git rebase upstream/$DEFAULT_BRANCH; then
            echo "✅ Rebase successful"

            # Restore our .github directory
            rm -rf .github
            if [ -d "$BACKUP_DIR/.github" ]; then
              cp -r "$BACKUP_DIR/.github" .
              git add .github
              git commit -m "Restore .github directory" || echo "No changes to .github directory"
            else
              echo "WARNING: No .github directory to restore"
            fi

            # Cleanup backup
            rm -rf "$BACKUP_DIR"

            git push origin $CURRENT_BRANCH --force-with-lease
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
          GH_TOKEN: ${{{{ secrets.GH_TOKEN }}}}
        run: |
          # Create branch for conflict resolution with unique name
          BRANCH_NAME="sync/upstream-$(date +%Y%m%d-%H%M%S)-${{{{ github.run_id }}}}"
          git checkout -b $BRANCH_NAME

          # Add upstream as remote and fetch
          git fetch upstream

          # Get upstream default branch - prefer dynamic detection
          DETECTED_BRANCH=$(git ls-remote --symref upstream HEAD | awk '/^ref:/ {{sub(/refs\\/heads\\//, "", $2); print $2}}')

          if [ -n "$DETECTED_BRANCH" ]; then
            DEFAULT_BRANCH="$DETECTED_BRANCH"
          elif [ -n "${{{{ secrets.UPSTREAM_DEFAULT_BRANCH }}}}" ]; then
            DEFAULT_BRANCH="${{{{ secrets.UPSTREAM_DEFAULT_BRANCH }}}}"
          else
            echo "ERROR: Could not determine upstream default branch"
            exit 1
          fi

          # Try merge instead of rebase for conflict resolution
          git merge upstream/$DEFAULT_BRANCH --no-edit || true

          # Commit the conflict state
          git add -A
          git commit -m "🔴 Merge conflict from upstream - manual resolution required" || true
          git push origin $BRANCH_NAME

          # Get the default branch of the current repository
          CURRENT_DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')

          # Create PR
          PR_URL=$(gh pr create \\
            --title "🔴 [Conflict] Sync from upstream" \\
            --body "⚠️ Merge conflicts detected. Please resolve manually and merge." \\
            --base $CURRENT_DEFAULT_BRANCH \\
            --head $BRANCH_NAME)

          echo "pr_url=$PR_URL" >> $GITHUB_OUTPUT

      - name: Sync tags
        if: steps.sync.outputs.has_conflicts == 'false'
        env:
          GH_TOKEN: ${{{{ secrets.GH_TOKEN }}}}
        run: |
          echo "Syncing tags..."

          # Configure git to use GH_TOKEN if available
          if [ -n "$GH_TOKEN" ]; then
            echo "Using GH_TOKEN for authentication"
            # 더 명시적으로 origin remote URL을 GH_TOKEN을 사용하도록 설정
            git remote set-url origin https://x-access-token:${{GH_TOKEN}}@github.com/${{{{ github.repository }}}}
          else
            echo "Warning: GH_TOKEN not found. Tag sync may fail if tags contain workflow files."
          fi

          git fetch upstream --tags
          git push origin --tags --force

  notify-slack-failure:
    needs: sync
    if: failure()
    runs-on: ubuntu-latest

    steps:
      - name: Check for Slack webhook
        id: check_webhook
        run: |
          if [[ -n "${{{{ secrets.SLACK_WEBHOOK_URL }}}}" ]]; then
            echo "has_webhook=true" >> $GITHUB_OUTPUT
          else
            echo "has_webhook=false" >> $GITHUB_OUTPUT
          fi

      - name: Send Slack notification for failure
        if: steps.check_webhook.outputs.has_webhook == 'true'
        uses: slackapi/slack-github-action@v2.0.0
        with:
          webhook: ${{{{ secrets.SLACK_WEBHOOK_URL }}}}
          webhook-type: incoming-webhook
          payload: |
            {{
              "text": "❌ Workflow Failed",
              "blocks": [
                {{
                  "type": "section",
                  "text": {{
                    "type": "mrkdwn",
                    "text": "❌ *Workflow Failed*"
                  }}
                }},
                {{
                  "type": "section",
                  "fields": [
                    {{
                      "type": "mrkdwn",
                      "text": "*Workflow:*\\nMirror Sync"
                    }},
                    {{
                      "type": "mrkdwn",
                      "text": "*Repository:*\\n${{{{ github.repository }}}}"
                    }}
                  ]
                }},
                {{
                  "type": "section",
                  "fields": [
                    {{
                      "type": "mrkdwn",
                      "text": "*Actor:*\\n${{{{ github.actor }}}}"
                    }},
                    {{
                      "type": "mrkdwn",
                      "text": "*Branch:*\\n${{{{ github.ref_name }}}}"
                    }}
                  ]
                }},
                {{
                  "type": "section",
                  "text": {{
                    "type": "mrkdwn",
                    "text": "*Workflow URL:*\\n<${{{{ github.server_url }}}}/${{{{ github.repository }}}}/actions/runs/${{{{ github.run_id }}}}|View Failed Workflow>"
                  }}
                }},
                {{
                  "type": "context",
                  "elements": [
                    {{
                      "type": "mrkdwn",
                      "text": "Click the link above to view the failed workflow details"
                    }}
                  ]
                }}
              ]
            }}

  notify-slack-conflict:
    needs: sync
    if: needs.sync.outputs.has_conflicts == 'true'
    runs-on: ubuntu-latest

    steps:
      - name: Check for Slack webhook
        id: check_webhook
        run: |
          if [[ -n "${{{{ secrets.SLACK_WEBHOOK_URL }}}}" ]]; then
            echo "has_webhook=true" >> $GITHUB_OUTPUT
          else
            echo "has_webhook=false" >> $GITHUB_OUTPUT
          fi

      - name: Send Slack notification for conflict
        if: steps.check_webhook.outputs.has_webhook == 'true'
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
