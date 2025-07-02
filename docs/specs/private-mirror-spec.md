# private-mirror 명령어 기술 스펙

## 개요
공개 저장소를 프라이빗 미러로 복제하고 자동 동기화를 설정하는 명령어입니다.

## 함수 시그니처

```python
def private_mirror_command(
    upstream_url: str,  # 필수: 원본 저장소 URL
    name: Annotated[Optional[str], typer.Option("--name", "-n")] = None,
    org: Annotated[Optional[str], typer.Option("--org", "-o")] = None,
    prefix: Annotated[Optional[str], typer.Option("--prefix", "-p")] = None,
    schedule: Annotated[Optional[str], typer.Option("--schedule", "-s")] = None,
    visibility: Annotated[Optional[str], typer.Option("--visibility")] = None,
    slack_webhook_url: Annotated[Optional[str], typer.Option("--slack-webhook-url")] = None,
    github_token: Annotated[Optional[str], typer.Option("--github-token")] = None,
    skip_sync: Annotated[bool, typer.Option("--skip-sync")] = False,
    use_http: Annotated[bool, typer.Option("--use-http")] = False,
) -> None
```

## 실행 워크플로우

### 1. 입력 검증 단계
```python
# URL 형식 검증
validate_repository_url(upstream_url) -> bool

# GitHub CLI 인증 확인
check_gh_auth() -> bool

# 원본 저장소 접근 가능 여부 확인
check_repository_access(upstream_url) -> bool
```

### 2. 저장소 복제 단계
```python
# 임시 디렉토리에서 작업
with tempfile.TemporaryDirectory() as temp_dir:
    # 원본 저장소 복제 (모든 브랜치와 태그)
    git_clone_bare(upstream_url, temp_dir)

    # .github 디렉토리 제거 (원본 워크플로우 제거)
    remove_github_directory(temp_dir)
```

### 3. 미러 저장소 생성 단계
```python
# 타겟 저장소명 결정
target_name = determine_target_name(name, prefix, upstream_url)

# GitHub에서 저장소 생성
create_github_repository(
    name=target_name,
    org=org,
    visibility=visibility,  # "private" 기본값
    description=f"Private mirror of {upstream_url}"
)
```

### 4. 코드 푸시 단계
```python
# 원격 저장소 설정
git_remote_add_origin(mirror_url)

# 모든 브랜치와 태그 푸시
git_push_all_branches()
git_push_all_tags()
```

### 5. 자동 동기화 설정 단계
```python
if not skip_sync:
    # GitHub Actions 워크플로우 생성
    workflow_content = generate_sync_workflow(
        upstream_url=upstream_url,
        schedule=schedule,
        upstream_branch=get_upstream_default_branch(upstream_url)
    )

    # 워크플로우 파일 커밋
    commit_workflow_file(workflow_content)

    # 저장소 시크릿 설정
    setup_repository_secrets(
        repo_name=target_name,
        upstream_url=upstream_url,
        github_token=github_token,
        slack_webhook_url=slack_webhook_url
    )
```

## GitHub Actions 워크플로우 스펙

### 파일 위치
`.github/workflows/mirror-sync.yml`

### 워크플로우 구조
```yaml
name: Mirror Sync
on:
  schedule:
    - cron: '0 0 * * *'  # 기본: 매일 자정
  workflow_dispatch:

env:
  UPSTREAM_URL: ${{ secrets.UPSTREAM_URL }}
  GH_TOKEN: ${{ secrets.GH_TOKEN }}
  SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Mirror Repository
        run: |
          # 원본 저장소에서 변경사항 fetch
          # 미러 저장소로 push
          # 태그 동기화 (GH_TOKEN 사용)

      - name: Notify Slack
        if: failure()
        run: |
          # 실패 시 Slack 알림
```

### 필수 시크릿
```python
REPOSITORY_SECRETS = {
    "UPSTREAM_URL": str,              # 원본 저장소 URL
    "UPSTREAM_DEFAULT_BRANCH": str,   # 원본 기본 브랜치
    "GH_TOKEN": str,                  # Personal Access Token
    "SLACK_WEBHOOK_URL": str,         # Slack 웹훅 URL (선택)
}
```

## 데이터 구조

### 미러 정보 캐시
```python
MirrorInfo = {
    "upstream": str,        # 원본 저장소 URL
    "mirror": str,          # 미러 저장소 URL
    "name": str,           # 저장소명 (owner/repo)
    "created_at": str,     # 생성 시간 (ISO 8601)
    "schedule": str,       # 동기화 스케줄
    "has_sync": bool,      # 자동 동기화 여부
}
```

### 설정 파일 업데이트
```toml
# ~/.cli-git/cache/recent_mirrors.json에 추가
[
  {
    "upstream": "https://github.com/upstream/repo",
    "mirror": "https://github.com/user/mirror-repo",
    "name": "user/mirror-repo",
    "created_at": "2025-01-01T00:00:00Z",
    "schedule": "0 0 * * *",
    "has_sync": true
  }
]
```

## 외부 의존성

### Git 명령어
```bash
# 베어 클론 (모든 브랜치/태그 포함)
git clone --bare <upstream_url> <temp_dir>

# 원격 저장소 추가
git remote add origin <mirror_url>

# 모든 브랜치 푸시
git push origin --all

# 모든 태그 푸시
git push origin --tags
```

### GitHub CLI 호출
```bash
# 저장소 생성
gh repo create <name> --private --description "..."

# 시크릿 설정
gh secret set UPSTREAM_URL --body "<url>" --repo <repo>

# API 호출
gh api repos/<owner>/<repo>/contents/.github/workflows/mirror-sync.yml
```

## 에러 처리

### 검증 단계 에러
1. **잘못된 URL 형식**
   ```
   ❌ Invalid repository URL format
   Expected: https://github.com/owner/repo
   ```

2. **접근 불가능한 저장소**
   ```
   ❌ Cannot access upstream repository
   Repository may be private or not exist
   ```

3. **GitHub CLI 미인증**
   ```
   ❌ GitHub CLI is not authenticated
   Please run: gh auth login
   ```

### 실행 단계 에러
1. **저장소 이름 충돌**
   ```
   ❌ Repository user/mirror-repo already exists
   Use --name option to specify different name
   ```

2. **권한 부족**
   ```
   ❌ Insufficient permissions to create repository
   Check organization membership and permissions
   ```

3. **네트워크 오류**
   ```
   ❌ Failed to clone repository: connection timeout
   Check network connection and try again
   ```

### 복구 전략
- **부분 실패**: 생성된 저장소 정리 후 재시도
- **권한 오류**: 조직 권한 확인 안내
- **네트워크 오류**: 재시도 제안

## 성능 특성

### 실행 시간
- 소형 저장소 (< 100MB): 30초 - 2분
- 대형 저장소 (> 1GB): 5분 - 30분
- 네트워크 속도에 의존

### 디스크 사용량
- 임시 디렉토리: 원본 저장소 크기의 1.5배
- 작업 완료 후 자동 정리

### 네트워크 사용량
- 다운로드: 원본 저장소 전체 크기
- 업로드: 원본 저장소 전체 크기
- API 호출: 5-10회

## 보안 고려사항

### 임시 파일 처리
```python
# 임시 디렉토리 자동 정리
with tempfile.TemporaryDirectory() as temp_dir:
    # 작업 수행
    pass  # 자동으로 디렉토리 삭제됨
```

### 시크릿 관리
- GitHub 시크릿으로 저장 (암호화됨)
- 로컬에는 시크릿 저장하지 않음
- 로그에 시크릿 노출 방지

### 토큰 권한
```
Required GitHub Token Permissions:
- repo (저장소 생성/관리)
- workflow (워크플로우 파일 생성)
```

## 테스트 전략

### 단위 테스트
- URL 검증 함수
- 이름 생성 로직
- 워크플로우 생성 함수

### 통합 테스트
- Git 명령어 모킹
- GitHub API 모킹
- 파일 시스템 모킹

### E2E 테스트
- 실제 GitHub 저장소 사용 (제한적)
- 테스트 조직에서만 수행
