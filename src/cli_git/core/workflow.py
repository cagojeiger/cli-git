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

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout mirror repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{{{ secrets.GH_TOKEN }}}}

      - name: Backup mirror configurations
        run: |
          # 미러 전용 파일 백업
          mkdir -p /tmp/mirror-backup

          # 현재 미러 워크플로우 백업
          if [ -f .github/workflows/mirror-sync.yml ]; then
            cp .github/workflows/mirror-sync.yml /tmp/mirror-backup/
          fi

          # 제거할 파일 목록 생성
          cat > /tmp/mirror-backup/remove-list.txt << EOF
          .github/workflows/operator.yml
          .github/workflows/registry-push.yml
          EOF

      - name: Complete sync from upstream
        env:
          UPSTREAM_URL: ${{{{ secrets.UPSTREAM_URL }}}}
          UPSTREAM_DEFAULT_BRANCH: ${{{{ secrets.UPSTREAM_DEFAULT_BRANCH }}}}
          GH_TOKEN: ${{{{ secrets.GH_TOKEN }}}}
        run: |
          # Git 설정
          git config user.name "Mirror Bot"
          git config user.email "mirror-bot@users.noreply.github.com"

          # Upstream 추가 및 가져오기
          git remote add upstream $UPSTREAM_URL || git remote set-url upstream $UPSTREAM_URL
          git fetch upstream

          # 기본 브랜치 감지
          DEFAULT_BRANCH=$(git ls-remote --symref upstream HEAD | awk '/^ref:/ {{sub(/refs\\/heads\\//, "", $2); print $2}}')
          DEFAULT_BRANCH=${{DEFAULT_BRANCH:-$UPSTREAM_DEFAULT_BRANCH}}

          # 완전히 upstream으로 리셋 (충돌 불가능)
          git reset --hard upstream/$DEFAULT_BRANCH

      - name: Apply mirror customizations
        run: |
          # 미러 워크플로우 복원
          if [ -f /tmp/mirror-backup/mirror-sync.yml ]; then
            mkdir -p .github/workflows
            cp /tmp/mirror-backup/mirror-sync.yml .github/workflows/
          fi

          # 불필요한 파일 제거
          while IFS= read -r file; do
            rm -f "$file"
          done < /tmp/mirror-backup/remove-list.txt

          # 변경사항 커밋
          git add -A
          if ! git diff --cached --quiet; then
            git commit -m "♻️ Sync from upstream + mirror customizations"
          fi

      - name: Push changes
        run: |
          git push origin main --force-with-lease

      - name: Sync tags
        env:
          GH_TOKEN: ${{{{ secrets.GH_TOKEN }}}}
        run: |
          # 태그 가져오기 및 푸시
          git fetch upstream --tags
          git push origin --tags --force

  notify-failure:
    needs: sync
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Send Slack notification
        if: env.SLACK_WEBHOOK_URL != ''
        env:
          SLACK_WEBHOOK_URL: ${{{{ secrets.SLACK_WEBHOOK_URL }}}}
        uses: slackapi/slack-github-action@v2.0.0
        with:
          webhook: ${{{{ env.SLACK_WEBHOOK_URL }}}}
          webhook-type: incoming-webhook
          payload: |
            {{
              "text": "❌ Mirror Sync Failed",
              "blocks": [
                {{
                  "type": "section",
                  "text": {{
                    "type": "mrkdwn",
                    "text": "❌ *Mirror Sync Failed*\\n*Repository:* `${{{{ github.repository }}}}`\\n*Workflow:* <${{{{ github.server_url }}}}/${{{{ github.repository }}}}/actions/runs/${{{{ github.run_id }}}}|View Details>"
                  }}
                }}
              ]
            }}
"""
    return workflow_yaml
