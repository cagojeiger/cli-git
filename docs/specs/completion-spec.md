# 자동완성 시스템 기술 스펙

## 개요
cli-git의 자동완성 시스템은 다층 캐시와 실시간 API 호출을 조합하여 빠르고 정확한 자동완성을 제공합니다.

## 전체 아키텍처

### 자동완성 제공자 함수들
```python
# src/cli_git/completion/completers.py

def complete_organization(incomplete: str) -> List[Union[str, Tuple[str, str]]]
def complete_schedule(incomplete: str) -> List[Tuple[str, str]]
def complete_prefix(incomplete: str) -> List[Tuple[str, str]]
def complete_repository(incomplete: str) -> List[Union[str, Tuple[str, str]]]  # 핵심 함수
```

## Repository 자동완성 (핵심)

### 함수 시그니처
```python
def complete_repository(incomplete: str) -> List[Union[str, Tuple[str, str]]]
```

### 다층 캐시 시스템

#### Level 1: scanned_mirrors 캐시 (최우선)
```python
scanned_mirrors = config_manager.get_scanned_mirrors()
if scanned_mirrors:
    # 30분 TTL, GitHub 스캔 결과
    # 가장 빠르고 정확한 미러 목록
    return process_scanned_mirrors(scanned_mirrors, incomplete)
```

#### Level 2: repo_completion 캐시
```python
cached_repos = config_manager.get_repo_completion_cache()
if cached_repos is not None:
    # 10분 TTL, 저장소 + 미러 여부 정보
    # API 호출 결과 캐시
    return process_completion_cache(cached_repos, incomplete)
```

#### Level 3: recent_mirrors 캐시
```python
recent_mirrors = config_manager.get_recent_mirrors()
# 무제한 TTL, 최근 생성한 미러 10개
# 로컬 히스토리 기반
```

#### Level 4: GitHub API 실시간 호출
```python
# 캐시 모두 실패 시 실시간 API 호출
owners = determine_search_owners(incomplete, username, default_org)
for owner in owners:
    repos = fetch_repositories_from_api(owner)
    # 모든 저장소에 대해 미러 여부 확인
```

### 입력 패턴 처리

#### 1. 전체 저장소명 입력 (`owner/repo`)
```python
if "/" in incomplete:
    # 소유자와 저장소명이 모두 포함된 경우
    # 정확한 매칭 수행
    if repo_name.lower().startswith(incomplete.lower()):
        completions.append((repo_name, description))
```

#### 2. 저장소명만 입력 (`repo`)
```python
else:
    # 저장소명만 입력된 경우
    # 모든 소유자의 저장소에서 검색
    _, name_only = repo_name.split("/")
    if name_only.lower().startswith(incomplete.lower()):
        completions.append((repo_name, description))
```

### 미러 여부 확인 로직

#### API 기반 확인
```python
def is_mirror_repository(repo_name: str) -> bool:
    """GitHub API로 mirror-sync.yml 파일 존재 확인"""
    result = subprocess.run([
        "gh", "api",
        f"repos/{repo_name}/contents/.github/workflows/mirror-sync.yml"
    ], capture_output=True)
    return result.returncode == 0
```

#### 캐시 기반 확인
```python
# repo_completion 캐시에서 미러 여부 확인
is_mirror = repo_data.get("is_mirror", False)
if not is_mirror:
    continue  # 미러가 아닌 저장소는 제외
```

### 설명 텍스트 생성

#### 미러 설명 포맷터
```python
def _get_mirror_description(upstream: str) -> str:
    """Upstream URL로부터 설명 텍스트 생성"""
    if upstream:
        if "github.com/" in upstream:
            # GitHub 저장소인 경우 간단한 형태로 표시
            upstream_name = extract_repo_name(upstream)
            return f"🔄 Mirror of {upstream_name}"
        else:
            # 다른 플랫폼인 경우 전체 URL 표시
            return f"🔄 Mirror of {upstream}"
    else:
        return "🔄 Mirror repository"
```

#### 캐시 기반 설명
```python
description = repo_data.get("description", "Mirror repository")
if not description:
    description = "Mirror repository"
return f"🔄 {description}"
```

## 성능 최적화 전략

### API 호출 최소화
1. **캐시 우선 사용**: 30분 이내 스캔 결과 재사용
2. **배치 처리**: 저장소 목록을 한 번에 가져온 후 개별 확인
3. **결과 제한**: 최대 20개 결과만 반환

### 메모리 효율성
```python
# 대용량 데이터 스트리밍 없음
# JSON 객체 전체 로드 후 처리
repos = json.loads(result.stdout)

# 결과 개수 제한으로 메모리 사용량 제어
return completions[:20]
```

### 응답 시간 최적화
```python
# 캐시 히트 시: < 50ms
# API 호출 시: 1-3초 (네트워크 의존)
```

## 기타 자동완성 기능

### Organization 자동완성
```python
def complete_organization(incomplete: str) -> List[Union[str, Tuple[str, str]]]:
    """사용자가 속한 조직 목록 자동완성"""
    try:
        orgs = get_user_organizations()  # gh api user/orgs
        return [(org, "GitHub Organization") for org in orgs
                if org.lower().startswith(incomplete.lower())]
    except GitHubError:
        return []
```

### Schedule 자동완성
```python
def complete_schedule(incomplete: str) -> List[Tuple[str, str]]:
    """미리 정의된 크론 스케줄 목록"""
    schedules = [
        ("0 * * * *", "Every hour"),
        ("0 0 * * *", "Every day at midnight UTC"),
        ("0 0 * * 0", "Every Sunday at midnight UTC"),
        ("0 0,12 * * *", "Twice daily (midnight and noon UTC)"),
        ("0 */6 * * *", "Every 6 hours"),
        ("0 0 1 * *", "First day of every month"),
    ]
    return [s for s in schedules if s[0].startswith(incomplete)]
```

### Prefix 자동완성
```python
def complete_prefix(incomplete: str) -> List[Tuple[str, str]]:
    """설정에서 기본 프리픽스 + 공통 프리픽스 목록"""
    config_manager = ConfigManager()
    config = config_manager.get_config()
    default_prefix = config["preferences"].get("default_prefix", "mirror-")

    prefixes = [
        (default_prefix, "Default prefix"),
        ("mirror-", "Standard mirror prefix"),
        ("fork-", "Fork prefix"),
        ("private-", "Private prefix"),
        ("backup-", "Backup prefix"),
        ("", "No prefix"),
    ]
    # 중복 제거 후 반환
```

## 에러 처리

### GitHub API 실패
```python
except GitHubError:
    # API 실패 시 캐시로 폴백
    try:
        recent_mirrors = config_manager.get_recent_mirrors()
        return process_cached_mirrors(recent_mirrors, incomplete)
    except Exception:
        return []  # 모든 것이 실패하면 빈 목록
```

### 네트워크 타임아웃
```python
# subprocess 호출에 내재된 타임아웃 사용
# 별도 타임아웃 설정 없음 (시스템 기본값 의존)
```

### 잘못된 캐시 데이터
```python
try:
    content = cache_file.read_text()
    cache_data = json.loads(content)
except (json.JSONDecodeError, FileNotFoundError, KeyError):
    return None  # 캐시 무효화
```

## 자동완성 설치

### Shell 지원
- **bash**: `~/.bashrc` 또는 `~/.bash_completion`
- **zsh**: `~/.zshrc`
- **fish**: `~/.config/fish/completions/`

### 설치 프로세스
```python
def completion_install_command() -> None:
    """자동완성 스크립트를 적절한 위치에 설치"""
    shell = detect_shell()  # $SHELL 환경변수에서 감지

    if shell == "bash":
        install_bash_completion()
    elif shell == "zsh":
        install_zsh_completion()
    elif shell == "fish":
        install_fish_completion()
    else:
        # 수동 설치 안내
        show_manual_installation_guide()
```

### 완성 스크립트 생성
```python
# Typer의 내장 완성 생성기 사용
completion_script = typer.main.get_completion_script()
```

## 테스트 전략

### 단위 테스트
- 각 완성 함수별 개별 테스트
- 다양한 입력 패턴 테스트
- 에러 케이스 테스트

### 통합 테스트
- 캐시 시스템 통합 테스트
- GitHub API 모킹 테스트
- 성능 벤치마크 테스트

### 모킹 전략
```python
@patch("subprocess.run")
@patch("cli_git.completion.completers.ConfigManager")
def test_complete_repository_basic(mock_config, mock_subprocess):
    # API 응답 모킹
    # 캐시 상태 모킹
    # 결과 검증
```
