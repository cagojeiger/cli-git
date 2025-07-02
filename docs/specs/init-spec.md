# init 명령어 기술 스펙

## 개요
초기 설정을 수행하여 사용자 환경을 구성하는 명령어입니다.

## 함수 시그니처

```python
def init_command(
    org: Annotated[
        Optional[str],
        typer.Option("--org", "-o", help="Default organization name")
    ] = None,
    schedule: Annotated[
        Optional[str],
        typer.Option("--schedule", "-s", help="Default sync schedule (cron format)")
    ] = None,
    prefix: Annotated[
        Optional[str],
        typer.Option("--prefix", "-p", help="Default repository prefix")
    ] = None,
    slack_webhook_url: Annotated[
        Optional[str],
        typer.Option("--slack-webhook-url", help="Slack webhook URL for notifications")
    ] = None,
    github_token: Annotated[
        Optional[str],
        typer.Option("--github-token", help="GitHub Personal Access Token")
    ] = None,
) -> None
```

## 실행 흐름

### 1. 전제 조건 확인
```python
# GitHub CLI 인증 상태 확인
check_gh_auth() -> bool
```

### 2. 사용자 정보 수집
```python
# 현재 GitHub 사용자명 가져오기
get_current_username() -> str

# 사용자 조직 목록 가져오기 (대화형 선택용)
get_user_organizations() -> List[str]
```

### 3. 대화형 입력 처리
- 조직 선택 (자동완성 지원)
- 스케줄 입력 (기본값 제공)
- 프리픽스 설정
- Slack 웹훅 URL (선택사항)
- GitHub 토큰 (선택사항)

## 설정 파일 구조

### 파일 위치
`~/.cli-git/settings.toml`

### 파일 권한
`0o600` (소유자만 읽기/쓰기)

### 데이터 구조
```toml
# cli-git configuration file
# Generated automatically - feel free to edit

[github]
# GitHub account information
username = "user123"
default_org = "mycompany"
slack_webhook_url = "https://hooks.slack.com/services/..."
github_token = "ghp_xxxxxxxxxxxxxxxxxxxx"

[preferences]
# User preferences
default_schedule = "0 0 * * *"
default_prefix = "mirror-"
analysis_template = "backend"
```

## 외부 의존성

### GitHub CLI 호출
```bash
# 인증 상태 확인
gh auth status

# 사용자 정보 조회
gh api user

# 조직 목록 조회
gh api user/orgs
```

### 파일 시스템 작업
```python
# 디렉토리 생성
Path.mkdir(exist_ok=True)

# 파일 생성/업데이트
Path.write_text(content)

# 권한 설정
os.chmod(file_path, 0o600)
```

## 데이터 검증

### GitHub 토큰 검증
```python
def validate_github_token(token: str) -> bool:
    """
    GitHub API 호출로 토큰 유효성 검증
    - 형식: ghp_로 시작하는 40자 문자열
    - 권한: repo, workflow 권한 필요
    """
```

### Slack 웹훅 URL 검증
```python
def validate_slack_webhook(url: str) -> bool:
    """
    Slack 웹훅 URL 형식 검증
    - 형식: https://hooks.slack.com/services/...
    - 길이: 최소 50자
    """
```

### 크론 스케줄 검증
```python
def validate_cron_schedule(schedule: str) -> bool:
    """
    크론 표현식 검증
    - 형식: 5개 필드 (분 시 일 월 요일)
    - 예: "0 0 * * *"
    """
```

## 에러 처리

### 에러 케이스
1. **GitHub CLI 미인증**
   - 메시지: "🔐 GitHub CLI is not authenticated"
   - 해결방법: "gh auth login" 안내

2. **네트워크 오류**
   - GitHub API 호출 실패
   - 조직 목록 조회 실패

3. **권한 오류**
   - 설정 파일 생성 실패
   - 디렉토리 생성 실패

4. **입력 검증 오류**
   - 잘못된 GitHub 토큰
   - 잘못된 크론 표현식
   - 잘못된 Slack 웹훅 URL

### 복구 전략
- **API 실패**: 기본값으로 계속 진행
- **파일 권한 오류**: 명확한 에러 메시지
- **검증 실패**: 재입력 요청

## 성능 특성

### 실행 시간
- 정상 케이스: 2-5초
- GitHub API 응답 시간에 의존

### 메모리 사용량
- 최대 10MB (조직 목록 로드 시)
- 대부분 1MB 이하

### 네트워크 요청
- 최대 3회 API 호출
  1. 사용자 정보 조회
  2. 조직 목록 조회
  3. 토큰 검증 (선택사항)

## 자동완성 지원

### 조직 선택
```python
complete_organization(incomplete: str) -> List[Tuple[str, str]]
```

### 스케줄 선택
```python
complete_schedule(incomplete: str) -> List[Tuple[str, str]]
```

### 프리픽스 선택
```python
complete_prefix(incomplete: str) -> List[Tuple[str, str]]
```

## 테스트 케이스

### 단위 테스트
- 설정 파일 생성
- 입력 검증 함수
- 에러 처리

### 통합 테스트
- GitHub API 모킹
- 파일 시스템 모킹
- 사용자 입력 모킹

### 보안 테스트
- 파일 권한 확인
- 민감 정보 마스킹
