# 캐싱 시스템 기술 스펙

## 개요
cli-git의 캐싱 시스템은 GitHub API 호출을 최소화하고 사용자 경험을 개선하기 위한 다층 캐시 구조를 제공합니다.

## 캐시 아키텍처

### 디렉토리 구조
```
~/.cli-git/
├── settings.toml           # 사용자 설정 (캐시 아님)
└── cache/
    ├── recent_mirrors.json      # 최근 생성한 미러 (FIFO)
    ├── scanned_mirrors.json     # 스캔된 미러 목록 (TTL 30분)
    └── repo_completion.json     # 저장소 자동완성 (TTL 10분)
```

### 캐시 관리자 클래스
```python
class ConfigManager:
    def __init__(self, config_dir: Path | None = None):
        self.cache_dir = config_dir or Path.home() / ".cli-git" / "cache"
        self.mirrors_cache = self.cache_dir / "recent_mirrors.json"
        self.scanned_mirrors_cache = self.cache_dir / "scanned_mirrors.json"
        self.repo_completion_cache = self.cache_dir / "repo_completion.json"
```

## 캐시 타입별 상세 스펙

### 1. recent_mirrors (최근 미러)

#### 용도
- 사용자가 최근에 생성한 미러 저장소 히스토리
- 자동완성에서 폴백 옵션으로 사용

#### 데이터 구조
```python
Recent_Mirrors = List[Dict[str, str]]

MirrorRecord = {
    "upstream": str,     # 원본 저장소 URL
    "mirror": str,       # 미러 저장소 URL
    "name": str,         # "owner/repo" 형식
    "created_at": str,   # ISO 8601 형식 (옵션)
    "schedule": str,     # 크론 스케줄 (옵션)
}
```

#### 관리 정책
```python
def add_recent_mirror(self, mirror_info: Dict[str, str]) -> None:
    """
    - FIFO 방식 (먼저 들어온 것이 먼저 나감)
    - 최대 10개 유지
    - TTL 없음 (수동 삭제까지 유지)
    - 새 항목은 맨 앞에 추가
    """
    mirrors = self.get_recent_mirrors()
    mirrors.insert(0, mirror_info)
    mirrors = mirrors[:10]  # 10개 제한
```

#### 사용 시점
- `private-mirror` 명령어 성공 시 추가
- `complete_repository` 에서 API 실패 시 폴백

### 2. scanned_mirrors (스캔된 미러)

#### 용도
- `update-mirrors --scan` 결과 캐시
- 자동완성에서 최우선 데이터 소스

#### 데이터 구조
```python
Scanned_Mirrors_Cache = {
    "timestamp": float,    # Unix timestamp
    "mirrors": List[MirrorData]
}

MirrorData = {
    "name": str,           # "owner/repo"
    "mirror": str,         # 저장소 URL
    "upstream": str,       # 원본 URL (빈 문자열 가능)
    "description": str,    # 저장소 설명
    "is_private": bool,    # 프라이빗 여부
    "updated_at": str,     # 마지막 업데이트 시간
}
```

#### TTL 정책
```python
def get_scanned_mirrors(self, max_age: int = 1800) -> Optional[List[Dict[str, str]]]:
    """
    - 기본 TTL: 30분 (1800초)
    - 시간 기반 만료 (LRU 없음)
    - 만료 시 None 반환
    """
    age = time.time() - cache_data.get("timestamp", 0)
    if age > max_age:
        return None
```

#### 사용 시점
- `scan_for_mirrors` 함수 실행 시 저장
- `update-mirrors --scan` 실행 시 저장
- `complete_repository` 에서 최우선 데이터 소스

### 3. repo_completion (저장소 자동완성)

#### 용도
- GitHub API로 조회한 모든 저장소 정보 (미러 여부 포함)
- 자동완성 성능 최적화

#### 데이터 구조
```python
Repo_Completion_Cache = {
    "timestamp": float,    # Unix timestamp
    "repos": List[RepoData]
}

RepoData = {
    "nameWithOwner": str,    # "owner/repo"
    "description": str,      # 저장소 설명
    "is_mirror": bool,       # 미러 여부 (중요!)
    "updatedAt": str,        # GitHub의 updatedAt
    "isArchived": bool,      # 아카이브 여부
}
```

#### TTL 정책
```python
def get_repo_completion_cache(self, max_age: int = 600) -> Optional[List[Dict[str, Any]]]:
    """
    - 기본 TTL: 10분 (600초)
    - 자동완성 성능을 위한 상대적으로 짧은 TTL
    - API 호출 비용과 실시간성의 균형
    """
```

#### 생성 과정
```python
# GitHub API 호출로 저장소 목록 조회
repos = fetch_repositories_from_github(owner)

# 각 저장소에 대해 미러 여부 확인
for repo in repos:
    is_mirror = check_mirror_workflow_exists(repo["nameWithOwner"])
    repo_data = {
        "nameWithOwner": repo["nameWithOwner"],
        "description": repo.get("description", ""),
        "is_mirror": is_mirror,
        "updatedAt": repo.get("updatedAt", ""),
    }
    all_repos_data.append(repo_data)

# 캐시에 저장
config_manager.save_repo_completion_cache(all_repos_data)
```

## 캐시 무효화 전략

### 자동 무효화
```python
# 시간 기반 무효화만 지원
age = time.time() - cache_data.get("timestamp", 0)
if age > max_age:
    return None  # 캐시 무효
```

### 수동 무효화
```bash
# 전체 캐시 삭제
rm -rf ~/.cli-git/cache/

# 특정 캐시만 삭제
rm ~/.cli-git/cache/scanned_mirrors.json
rm ~/.cli-git/cache/repo_completion.json
```

### 강제 새로고침
```bash
# 스캔 캐시 강제 새로고침
cli-git update-mirrors --scan

# 특정 저장소 정보 강제 업데이트
cli-git update-mirrors --repo owner/repo
```

## 성능 특성

### 캐시 히트율
- **scanned_mirrors**: 90%+ (일반적인 사용 패턴)
- **repo_completion**: 70-80% (자동완성 사용 빈도)
- **recent_mirrors**: 20-30% (새 사용자나 API 실패 시)

### 응답 시간
```python
Cache_Performance = {
    "scanned_mirrors": "< 10ms",      # JSON 파싱만
    "repo_completion": "< 20ms",      # 필터링 포함
    "recent_mirrors": "< 5ms",        # 단순 리스트
    "api_fallback": "1-3초"           # 네트워크 의존
}
```

### 메모리 사용량
```python
Cache_Size_Estimates = {
    "recent_mirrors": "< 1KB",        # 10개 항목
    "scanned_mirrors": "< 50KB",      # 일반적인 미러 개수
    "repo_completion": "< 500KB",     # 대량 저장소 포함
}
```

## 캐시 일관성

### 동시성 제어
- **파일 기반 캐시**: 동시 읽기 가능, 쓰기 시 덮어쓰기
- **원자적 쓰기**: `Path.write_text()` 사용으로 원자성 보장
- **락 메커니즘 없음**: 단일 사용자 도구 특성상 불필요

### 데이터 일관성
```python
# 캐시 간 일관성 보장 없음
# 각 캐시는 독립적으로 관리됨
# 사용자는 필요시 수동으로 캐시 삭제 가능
```

## 에러 처리

### 캐시 파일 손상
```python
try:
    content = cache_file.read_text()
    cache_data = json.loads(content)
    return cache_data.get("mirrors", [])
except (json.JSONDecodeError, FileNotFoundError, KeyError):
    return None  # 캐시 무효화, API 폴백
```

### 디스크 공간 부족
```python
# 캐시 저장 실패 시 무시하고 계속 진행
# 사용자에게 에러 메시지 표시하지 않음
# 다음 실행 시 API로 폴백
```

### 권한 문제
```python
# ~/.cli-git 디렉토리 생성 실패 시
# 임시 디렉토리 사용 또는 캐시 비활성화
# 기능은 정상 동작 (성능만 저하)
```

## 캐시 설정 옵션

### 환경변수 (향후 확장 가능)
```bash
# 캐시 디렉토리 변경
export CLI_GIT_CACHE_DIR="/custom/cache/path"

# TTL 설정 (초 단위)
export CLI_GIT_SCANNED_TTL=3600    # 1시간
export CLI_GIT_COMPLETION_TTL=300   # 5분

# 캐시 비활성화
export CLI_GIT_DISABLE_CACHE=1
```

### 설정 파일 (현재 미지원)
```toml
# 향후 ~/.cli-git/settings.toml에 추가 가능
[cache]
scanned_mirrors_ttl = 1800
repo_completion_ttl = 600
recent_mirrors_limit = 10
disable_cache = false
```

## 모니터링 및 디버깅

### 캐시 상태 확인
```bash
# 캐시 파일 존재 여부
ls -la ~/.cli-git/cache/

# 캐시 만료 시간 확인 (jq 필요)
jq '.timestamp' ~/.cli-git/cache/scanned_mirrors.json
```

### 디버그 정보
```python
# 향후 --debug 플래그 지원 가능
# 캐시 히트/미스 정보 출력
# API 호출 횟수 및 응답 시간 표시
```

### 캐시 통계 (향후 기능)
```python
# 캐시 사용 통계 수집
Cache_Stats = {
    "hits": int,           # 캐시 히트 횟수
    "misses": int,         # 캐시 미스 횟수
    "api_calls": int,      # API 호출 횟수
    "total_time_saved": float,  # 절약된 시간 (초)
}
```
