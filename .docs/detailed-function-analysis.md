# 상세 함수/클래스 분석 보고서

## 요약
- **총 분석 파일**: 23개
- **총 함수 개수**: 86개
- **총 클래스 개수**: 3개
- **평균 함수 길이**: 약 25줄
- **가장 긴 함수**: `private_mirror_operation` (115줄)

## 1. Completion 모듈 (자동완성)

### 📁 `completion/completers.py` (472줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `_matches_incomplete` | `repo_name: str, incomplete: str` | `bool` | 22 | 문자열 매칭 | 없음 | 없음 | 낮음 |
| `_extract_mirror_name_from_url` | `mirror_url: str` | `str` | 11 | URL 파싱 | `extract_repo_name_from_url` | 없음 | 낮음 |
| `_create_completion_entry` | `repo_name: str, description: str, is_mirror: bool` | `Tuple[str, str]` | 21 | 완성 항목 생성 | 없음 | 없음 | 낮음 |
| `_get_completions_from_scanned_mirrors` | `incomplete: str, config_manager: ConfigManager` | `List[Tuple[str, str]]` | 29 | 스캔 캐시 조회 | `ConfigManager` | 캐시 읽기 | 중간 |
| `_get_completions_from_cache` | `incomplete: str, config_manager: ConfigManager` | `List[Tuple[str, str]]` | 45 | 완성 캐시 조회 | `ConfigManager` | 캐시 읽기 | 높음 |
| `_check_is_mirror` | `repo_name: str` | `bool` | 18 | 미러 확인 | `subprocess` | API 호출 | 중간 |
| `_determine_search_owners` | `incomplete: str, username: str, default_org: str` | `Tuple[List[str], str]` | 25 | 검색 대상 결정 | 없음 | 없음 | 중간 |
| `_fetch_repos_for_owner` | `owner: str, repo_part: str, incomplete: str` | `List[Dict[str, str]]` | 55 | 저장소 목록 조회 | `subprocess`, `json` | API 호출 | 높음 |
| `_get_completions_from_api` | `incomplete: str, config_manager: ConfigManager` | `List[Tuple[str, str]]` | 51 | API 기반 완성 | 다수 | API 호출, 캐시 쓰기 | 매우 높음 |
| `_get_fallback_completions` | `incomplete: str, config_manager: ConfigManager` | `List[Tuple[str, str]]` | 36 | 폴백 완성 | `ConfigManager` | 캐시 읽기 | 중간 |
| `_get_mirror_description` | `upstream: str` | `str` | 10 | 설명 생성 | `format_repo_description` | 없음 | 낮음 |
| `complete_organization` | `incomplete: str` | `List[Union[str, Tuple[str, str]]]` | 19 | 조직명 완성 | `get_user_organizations` | API 호출 | 낮음 |
| `complete_schedule` | `incomplete: str` | `List[Tuple[str, str]]` | 23 | 스케줄 완성 | 없음 | 없음 | 낮음 |
| `complete_prefix` | `incomplete: str` | `List[Tuple[str, str]]` | 36 | 접두사 완성 | `ConfigManager` | 설정 읽기 | 낮음 |
| `complete_repository` | `incomplete: str` | `List[Union[str, Tuple[str, str]]]` | 30 | 저장소 완성 | 다수 | 캐시/API | 높음 |

## 2. Commands 모듈

### 📁 `commands/private_mirror.py` (321줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `clean_github_directory` | `repo_path: Path` | `bool` | 28 | .github 디렉토리 제거 | `shutil` | 파일시스템 변경 | 낮음 |
| `private_mirror_operation` | 6개 매개변수 | `None` | **115** | 미러 생성 핵심 로직 | 다수 | Git 작업, API 호출 | **매우 높음** |
| `private_mirror_command` | 8개 매개변수 | `None` | 84 | CLI 명령어 래퍼 | 다수 | 다수 | 높음 |

### 📁 `commands/update_mirrors.py` (295줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `update_mirrors_command` | 6개 매개변수 | `None` | 68 | 미러 업데이트 명령어 | 다수 | 다수 | 중간 |
| `_handle_scan_option` | 3개 매개변수 | `list` | 36 | 스캔 옵션 처리 | `scan_for_mirrors` | API 호출 | 중간 |
| `_display_scan_results` | `mirrors: list` | `None` | 42 | 스캔 결과 표시 | `typer` | 콘솔 출력 | 낮음 |
| `_find_mirrors_to_update` | 3개 매개변수 | `list` | 38 | 업데이트 대상 찾기 | `ConfigManager` | 설정 읽기 | 중간 |
| `_update_mirrors` | 3개 매개변수 | `None` | 63 | 미러 업데이트 실행 | 다수 | API 호출 | 높음 |

### 📁 `commands/init.py` (179줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `mask_webhook_url` | `url: str` | `str` | 22 | URL 마스킹 | `urllib.parse` | 없음 | 낮음 |
| `init_command` | 4개 매개변수 | `None` | 134 | 설정 초기화 | 다수 | 설정 파일 생성 | 높음 |

### 📁 `commands/info.py` (108줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `info_command` | 2개 매개변수 | `None` | 95 | 정보 표시 | `ConfigManager` | 콘솔 출력 | 중간 |

### 📁 `commands/completion.py` (96줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `detect_shell` | 없음 | `str` | 16 | 셸 감지 | `os`, `subprocess` | 프로세스 실행 | 낮음 |
| `completion_install_command` | 없음 | `None` | 68 | 완성 설치 | `detect_shell` | 콘솔 출력 | 중간 |

## 3. Commands/Modules 서브모듈

### 📁 `modules/scan.py` (176줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `scan_for_mirrors` | 3개 매개변수 | `List[Dict[str, str]]` | 38 | 미러 스캔 | 다수 | API 호출 | 중간 |
| `_get_repositories` | 2개 매개변수 | `List[Dict]` | 49 | 저장소 목록 조회 | `subprocess` | API 호출 | 중간 |
| `_is_mirror_repo` | `repo_name: str` | `bool` | 15 | 미러 확인 | `subprocess` | API 호출 | 낮음 |
| `_extract_mirror_info` | `repo_data: Dict` | `Dict[str, str]` | 23 | 미러 정보 추출 | 다수 | API 호출 | 중간 |
| `_get_upstream_from_workflow` | `repo_name: str` | `str` | 28 | 업스트림 URL 추출 | `subprocess`, `yaml` | API 호출 | 중간 |

### 📁 `modules/interactive.py` (171줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `select_mirrors_interactive` | `mirrors: List[Dict[str, str]]` | `List[Dict[str, str]]` | 17 | 대화형 선택 | 다수 | 콘솔 I/O | 중간 |
| `_display_mirrors` | `mirrors: List[Dict[str, str]]` | `None` | 23 | 미러 표시 | `typer` | 콘솔 출력 | 낮음 |
| `_get_mirror_name` | `mirror: Dict[str, str]` | `str` | 21 | 미러 이름 추출 | 없음 | 없음 | 낮음 |
| `_get_upstream_display` | `mirror: Dict[str, str]` | `str` | 17 | 업스트림 표시 | 없음 | 없음 | 낮음 |
| `_get_user_selection` | 없음 | `str` | 8 | 사용자 입력 | `typer` | 콘솔 입력 | 낮음 |
| `_process_selection` | 2개 매개변수 | `List[Dict[str, str]]` | 46 | 선택 처리 | 다수 | 없음 | 높음 |
| `_parse_numeric_selection` | `selection: str` | `List[int]` | 21 | 숫자 파싱 | 없음 | 없음 | 중간 |

### 📁 `modules/workflow_updater.py` (131줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `update_workflow_file` | `repo: str, content: str` | `bool` | 70 | 워크플로우 업데이트 | `subprocess` | API 호출 | 높음 |
| `get_repo_secret_value` | `repo: str, secret_name: str` | `Optional[str]` | 48 | 시크릿 조회 | `subprocess` | API 호출 | 중간 |

## 4. Core 모듈

### 📁 `core/workflow.py` (295줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `generate_sync_workflow` | 3개 매개변수 | `str` | **290** | YAML 생성 | 없음 | 없음 | 낮음* |

*참고: 대부분이 템플릿 문자열

## 5. Utils 모듈

### 📁 `utils/config.py` (204줄)

| 클래스/함수 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|-------------|----------|-----------|---------|------|---------|---------|---------|
| `ConfigManager` | - | - | 191 | 설정 관리 클래스 | - | - | - |
| `__init__` | `config_dir: Optional[Path]` | `None` | 10 | 초기화 | `Path` | 파일 생성 | 낮음 |
| `_ensure_config_dir` | 없음 | `None` | 5 | 디렉토리 생성 | 없음 | 파일시스템 | 낮음 |
| `get_config` | 없음 | `dict` | 25 | 설정 읽기 | `toml` | 파일 읽기 | 중간 |
| `save_config` | `config: dict` | `None` | 6 | 설정 저장 | `toml` | 파일 쓰기 | 낮음 |
| `get_recent_mirrors` | 없음 | `list` | 15 | 최근 미러 조회 | 없음 | 파일 읽기 | 낮음 |
| `add_recent_mirror` | `mirror_info: dict` | `None` | 20 | 미러 추가 | 없음 | 파일 쓰기 | 중간 |
| `get_scanned_mirrors` | 없음 | `Optional[list]` | 25 | 스캔 캐시 조회 | `json` | 파일 읽기 | 중간 |
| `save_scanned_mirrors` | `mirrors: list` | `None` | 15 | 스캔 캐시 저장 | `json` | 파일 쓰기 | 낮음 |
| `get_repo_completion_cache` | 없음 | `Optional[list]` | 25 | 완성 캐시 조회 | `json` | 파일 읽기 | 중간 |
| `save_repo_completion_cache` | `repos: list` | `None` | 15 | 완성 캐시 저장 | `json` | 파일 쓰기 | 낮음 |

### 📁 `utils/gh.py` (208줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `GitHubError` | - | - | 4 | 예외 클래스 | - | - | - |
| `check_gh_auth` | 없음 | `bool` | 12 | 인증 확인 | `subprocess` | 프로세스 실행 | 낮음 |
| `run_gh_auth_login` | 없음 | `bool` | 12 | 로그인 실행 | `subprocess` | 프로세스 실행 | 낮음 |
| `get_current_username` | 없음 | `str` | 19 | 사용자명 조회 | `subprocess` | API 호출 | 중간 |
| `create_private_repo` | 4개 매개변수 | `str` | 32 | 저장소 생성 | `subprocess` | API 호출 | 높음 |
| `add_repo_secret` | 3개 매개변수 | `None` | 18 | 시크릿 추가 | `subprocess` | API 호출 | 중간 |
| `get_user_organizations` | 없음 | `list[str]` | 24 | 조직 목록 조회 | `subprocess` | API 호출 | 중간 |
| `get_upstream_default_branch` | `upstream_url: str` | `str` | 28 | 기본 브랜치 조회 | `subprocess` | API 호출 | 중간 |
| `validate_github_token` | `token: str` | `bool` | 23 | 토큰 검증 | `subprocess` | API 호출 | 중간 |
| `mask_token` | `token: str` | `str` | 12 | 토큰 마스킹 | 없음 | 없음 | 낮음 |

### 📁 `utils/validators.py` (292줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `ValidationError` | - | - | 4 | 예외 클래스 | - | - | - |
| `validate_organization` | `org: Optional[str]` | `Optional[str]` | 28 | 조직명 검증 | `re` | 없음 | 중간 |
| `validate_cron_schedule` | `schedule: str` | `str` | 50 | cron 검증 | 다수 | 없음 | 높음 |
| `_validate_cron_field` | 3개 매개변수 | `bool` | 68 | cron 필드 검증 | 없음 | 없음 | 높음 |
| `validate_github_url` | `url: str` | `str` | 30 | URL 검증 | `urllib.parse` | 없음 | 중간 |
| `validate_repository_name` | `name: str` | `str` | 41 | 저장소명 검증 | `re` | 없음 | 중간 |
| `validate_prefix` | `prefix: str` | `str` | 29 | 접두사 검증 | `re` | 없음 | 중간 |
| `validate_slack_webhook_url` | `url: str` | `str` | 24 | Slack URL 검증 | `urllib.parse` | 없음 | 중간 |

### 📁 `utils/git.py` (111줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `run_git_command` | 2개 매개변수 | `str` | 25 | Git 명령 실행 | `subprocess` | 프로세스 실행 | 중간 |
| `get_default_branch` | `cwd: Optional[Path]` | `str` | 46 | 기본 브랜치 조회 | `run_git_command` | Git 명령 | 높음 |
| `extract_repo_info` | `url: str` | `Tuple[str, str]` | 23 | URL 파싱 | `re` | 없음 | 중간 |

### 📁 `utils/github.py` (58줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `extract_repo_name_from_url` | `url: str` | `Optional[str]` | 32 | URL에서 저장소명 추출 | 없음 | 없음 | 중간 |
| `format_repo_description` | 2개 매개변수 | `str` | 18 | 설명 포맷팅 | `extract_repo_name_from_url` | 없음 | 낮음 |

## 6. CLI 엔트리 포인트

### 📁 `cli.py` (97줄)

| 함수명 | 매개변수 | 반환 타입 | 라인 수 | 책임 | 의존성 | 부작용 | 복잡도 |
|--------|----------|-----------|---------|------|---------|---------|---------|
| `create_version_message` | `version: str` | `str` | 8 | 버전 메시지 생성 | 없음 | 없음 | 낮음 |
| `display_message` | 2개 매개변수 | `None` | 8 | 메시지 표시 | `typer` | 콘솔 출력 | 낮음 |
| `exit_program` | `code: int` | `None` | 4 | 프로그램 종료 | `typer` | 프로세스 종료 | 낮음 |
| `version_callback` | `value: bool` | `None` | 10 | 버전 콜백 | 다수 | 콘솔 출력, 종료 | 낮음 |
| `main` | 2개 매개변수 | `None` | 17 | 메인 진입점 | `typer` | 없음 | 낮음 |

## 고복잡도 함수 목록 (우선 리팩토링 대상)

1. **`private_mirror_operation`** (115줄) - 분해 필요
   - Git 작업 분리
   - 워크플로우 생성 분리
   - 시크릿 설정 분리

2. **`generate_sync_workflow`** (290줄) - 템플릿 외부화 필요
   - YAML 템플릿을 별도 파일로
   - 동적 섹션만 함수로

3. **`_validate_cron_field`** (68줄) - 로직 단순화 필요
   - 복잡한 조건문 정리
   - 헬퍼 함수 분리

4. **`_fetch_repos_for_owner`** (55줄) - 책임 분리 필요
   - API 호출과 데이터 처리 분리
   - 미러 확인 로직 분리

5. **`_get_completions_from_api`** (51줄) - 단계별 분리 필요
   - 소유자 결정, API 호출, 캐싱 분리

## 중복 패턴 발견

1. **GitHub API 호출 패턴**
   - 여러 함수에서 `subprocess.run(["gh", ...])` 반복
   - 공통 래퍼 함수로 통합 가능

2. **캐시 읽기/쓰기 패턴**
   - ConfigManager의 여러 메서드에서 유사한 패턴
   - 제네릭 캐시 함수로 통합 가능

3. **에러 처리 패턴**
   - try-except 블록의 반복
   - 데코레이터 패턴 적용 가능

## 권장사항

### 1. 즉시 조치 필요
- `completers.py`를 4개 파일로 분리 (utils, cache, api, completers)
- `private_mirror_operation` 함수를 3-4개 함수로 분해
- `generate_sync_workflow`의 템플릿을 외부 파일로 이동

### 2. 중기 개선
- GitHub API 호출을 위한 공통 래퍼 클래스 생성
- 캐시 관리를 위한 제네릭 인터페이스 구현
- 복잡한 검증 로직 단순화

### 3. 장기 개선
- 함수형 프로그래밍 패턴 더 적극적으로 활용
- 의존성 주입 패턴 도입 고려
- 타입 힌트 개선 및 mypy 도입
