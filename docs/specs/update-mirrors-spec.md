# update-mirrors 명령어 기술 스펙

## 개요
기존 미러 저장소들의 설정을 업데이트하고 동기화 상태를 관리하는 명령어입니다.

## 함수 시그니처

```python
def update_mirrors_command(
    repo: Annotated[
        Optional[str],
        typer.Option(
            "--repo", "-r",
            help="Specific repository to update (owner/repo). Use --scan to list available mirrors.",
            autocompletion=complete_repository,
        ),
    ] = None,
    scan: Annotated[
        bool,
        typer.Option("--scan", "-s", help="Scan and list mirror repositories (outputs repo names only)")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed information when scanning")
    ] = False,
) -> None
```

## 실행 모드

### 1. 스캔 모드 (`--scan`)
```python
def _handle_scan_option(
    config_manager: ConfigManager,
    config: dict,
    username: str,
    verbose: bool
) -> None
```

**파이프 친화적 출력** (기본값):
```bash
$ cli-git update-mirrors --scan
user/mirror-repo1
user/mirror-repo2
user/mirror-repo3
```

**상세 출력** (`--verbose`):
```bash
$ cli-git update-mirrors --scan --verbose
🔍 Scanning GitHub for mirror repositories...
  Using cached scan results (less than 30 minutes old)

✅ Found 3 mirror repositories:
======================================================================

  [1] 🔒 user/mirror-repo1
      📝 Mirror of upstream/project1
      🔗 Upstream: https://github.com/upstream/project1
      🕐 Updated: 2025-01-01 12:00

...
```

### 2. 특정 저장소 업데이트 (`--repo`)
```python
# 단일 저장소 직접 지정
mirrors = [{"mirror": f"https://github.com/{repo}", "upstream": "", "name": repo}]
```

### 3. 대화형 선택 (기본값)
```python
# 캐시에서 미러 목록 로드 후 대화형 선택
mirrors = select_mirrors_interactive(cached_mirrors)
```

## 캐시 시스템

### 캐시 우선순위
1. **scanned_mirrors** (30분 TTL) - 최고 우선순위
2. **recent_mirrors** (무제한) - 폴백
3. **실시간 스캔** - 최종 수단

### 캐시 데이터 구조
```python
ScannedMirrorsCache = {
    "timestamp": float,  # Unix timestamp
    "mirrors": List[MirrorData]
}

MirrorData = {
    "name": str,           # "owner/repo"
    "mirror": str,         # "https://github.com/owner/repo"
    "upstream": str,       # 원본 저장소 URL (빈 문자열 가능)
    "description": str,    # 저장소 설명
    "is_private": bool,    # 프라이빗 여부
    "updated_at": str,     # ISO 8601 형식
}
```

## 업데이트 프로세스

### 1. 미러 검색 단계
```python
def _find_mirrors_to_update(
    repo: Optional[str],
    config_manager: ConfigManager,
    config: dict,
    username: str,
) -> list
```

**검색 순서**:
1. 특정 저장소 지정 시 → 바로 반환
2. `scanned_mirrors` 캐시 확인
3. `recent_mirrors` 폴백
4. 실시간 GitHub 스캔

### 2. 미러 업데이트 단계
```python
def _update_mirrors(mirrors: list, github_token: str, slack_webhook_url: str) -> None
```

**각 미러에 대해 수행**:
1. **워크플로우 파일 존재 확인**
   ```bash
   gh api repos/{repo}/contents/.github/workflows/mirror-sync.yml
   ```

2. **Upstream URL 처리**
   - 캐시에 upstream이 있으면: 시크릿 업데이트
   - 캐시에 upstream이 없으면: 기존 설정 보존

3. **시크릿 업데이트**
   ```python
   # 필수 시크릿
   if upstream_url:
       add_repo_secret(repo_name, "UPSTREAM_URL", upstream_url)
       add_repo_secret(repo_name, "UPSTREAM_DEFAULT_BRANCH", upstream_branch)

   # 선택적 시크릿
   if github_token:
       add_repo_secret(repo_name, "GH_TOKEN", github_token)

   if slack_webhook_url:
       add_repo_secret(repo_name, "SLACK_WEBHOOK_URL", slack_webhook_url)
   ```

4. **워크플로우 파일 업데이트**
   ```python
   workflow_content = generate_sync_workflow(
       upstream_url or "https://github.com/PLACEHOLDER/PLACEHOLDER",
       "0 0 * * *",  # 기본 스케줄
       upstream_branch if upstream_url else "main",
   )

   workflow_updated = update_workflow_file(repo_name, workflow_content)
   ```

## 워크플로우 업데이트 메커니즘

### 파일 변경 감지
```python
def update_workflow_file(repo_name: str, workflow_content: str) -> bool:
    """
    Returns:
        True: 파일이 업데이트됨
        False: 파일이 이미 최신 상태
    """
```

**프로세스**:
1. 임시 디렉토리에서 저장소 클론
2. 기존 워크플로우 파일 내용과 비교
3. 변경사항이 있는 경우에만 커밋/푸시

### Git 인증 처리
```bash
# Personal Access Token을 사용한 인증
git remote set-url origin https://x-access-token:${GH_TOKEN}@github.com/{repo}
```

## 스캔 모듈 (`scan_for_mirrors`)

### 함수 시그니처
```python
def scan_for_mirrors(
    username: str,
    org: Optional[str] = None,
    prefix: Optional[str] = None  # Deprecated
) -> List[Dict[str, str]]
```

### 스캔 프로세스
1. **저장소 목록 조회**
   ```bash
   gh repo list {owner} --limit 1000 --json fullName,url,description,isPrivate,updatedAt
   ```

2. **미러 여부 확인**
   ```bash
   gh api repos/{repo}/contents/.github/workflows/mirror-sync.yml
   ```

3. **Upstream URL 추출**
   - 워크플로우 파일에서 주석으로 된 upstream URL 파싱
   - 형식: `# UPSTREAM_URL: https://github.com/upstream/repo`

## 자동완성 지원

### Repository 자동완성
```python
def complete_repository(incomplete: str) -> List[Union[str, Tuple[str, str]]]
```

**우선순위**:
1. `scanned_mirrors` 캐시
2. `repo_completion` 캐시
3. `recent_mirrors` 캐시
4. GitHub API 실시간 호출

**반환 형식**:
```python
[
    ("user/mirror-repo1", "🔄 Mirror of upstream/project1"),
    ("user/mirror-repo2", "🔄 Mirror repository"),
]
```

## 파이프라인 사용 예시

### 모든 미러 업데이트
```bash
# 파이프 친화적 출력을 xargs와 연계
cli-git update-mirrors --scan | xargs -I {} cli-git update-mirrors --repo {}
```

### 선택적 업데이트
```bash
# 특정 패턴의 미러만 업데이트
cli-git update-mirrors --scan | grep "backend" | xargs -I {} cli-git update-mirrors --repo {}
```

### 병렬 처리
```bash
# GNU parallel 사용
cli-git update-mirrors --scan | parallel -j 4 cli-git update-mirrors --repo {}
```

## 에러 처리

### 복구 가능한 에러
1. **워크플로우 파일 없음**
   ```
   ⚠️  Skipping user/repo: No mirror-sync.yml found
   ```

2. **API 호출 실패**
   ```
   ❌ Failed to update user/repo: API rate limit exceeded
   ```

3. **Git 작업 실패**
   ```
   ❌ Unexpected error updating user/repo: git push failed
   ```

### 에러 복구 전략
- **부분 실패**: 다음 저장소 계속 처리
- **전체 요약**: 성공/실패 개수 표시
- **재시도 가이드**: 개별 저장소 재시도 방법 안내

## 성능 최적화

### 캐시 활용
- **API 호출 최소화**: 30분 TTL로 반복 스캔 방지
- **배치 처리 없음**: 순차적 처리로 안정성 확보

### 네트워크 최적화
- **필요시에만 업데이트**: 파일 변경 감지로 불필요한 Git 작업 방지
- **타임아웃 설정**: GitHub API 호출에 합리적 타임아웃

### 메모리 관리
- **스트리밍 없음**: 작은 크기의 JSON 데이터만 처리
- **임시 파일 정리**: `tempfile.TemporaryDirectory` 사용

## 모니터링 및 로깅

### 진행 상황 표시
```
🔄 Updating user/mirror-repo1...
  ✓ Existing mirror detected
  Preserving current upstream configuration
    ✓ GitHub token added
    ✓ Slack webhook added
  Updating workflow file...
    ✓ Workflow file already up to date
  ✅ Successfully updated user/mirror-repo1
```

### 요약 정보
```
📊 Update complete: 3/5 mirrors updated successfully

💡 For failed updates, you may need to:
   - Check repository permissions
   - Verify the repository exists
   - Try updating individually with --repo option
```
