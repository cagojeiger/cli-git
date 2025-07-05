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

      - name: Identify and backup mirror-only files
        run: |
          # 백업 디렉토리 생성
          mkdir -p /tmp/mirror-backup

          # upstream 가져오기 (비교를 위해)
          git remote add upstream ${{{{ secrets.UPSTREAM_URL }}}} || true
          git fetch upstream --depth=1

          # upstream에 없고 미러에만 있는 파일 찾기
          echo "Finding mirror-only files..."
          comm -23 <(git ls-files | sort) \
                   <(git ls-tree -r upstream/HEAD --name-only | sort) \
                   > /tmp/mirror-backup/mirror-only-files.txt

          # 찾은 파일 개수 출력
          echo "Found $(wc -l < /tmp/mirror-backup/mirror-only-files.txt) mirror-only files"

          # 미러 전용 파일들 백업
          while IFS= read -r file; do
            if [ -f "$file" ]; then
              # 디렉토리 구조 유지하면서 백업
              mkdir -p "/tmp/mirror-backup/files/$(dirname "$file")"
              cp "$file" "/tmp/mirror-backup/files/$file"
            fi
          done < /tmp/mirror-backup/mirror-only-files.txt

          # 제거할 upstream 파일 목록 (미러에서는 필요없는 것들)
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
          # 미러 전용 파일들 복원
          if [ -s /tmp/mirror-backup/mirror-only-files.txt ]; then
            echo "Restoring mirror-only files..."
            while IFS= read -r file; do
              if [ -f "/tmp/mirror-backup/files/$file" ]; then
                # 디렉토리가 없으면 생성
                mkdir -p "$(dirname "$file")"
                cp "/tmp/mirror-backup/files/$file" "$file"
              fi
            done < /tmp/mirror-backup/mirror-only-files.txt
          fi

          # 불필요한 upstream 파일 제거
          echo "Removing unnecessary upstream files..."
          while IFS= read -r file; do
            rm -f "$file"
          done < /tmp/mirror-backup/remove-list.txt

          # 변경사항 확인 및 커밋
          git add -A
          if ! git diff --cached --quiet; then
            MIRROR_FILES=$(wc -l < /tmp/mirror-backup/mirror-only-files.txt)
            git commit -m "♻️ Sync from upstream + preserve $MIRROR_FILES mirror-only files"
          else
            echo "No changes to commit"
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
