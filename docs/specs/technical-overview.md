# cli-git 기술 스펙

## 아키텍처

### 핵심 기술 스택
- **CLI Framework**: Typer (FastAPI 기반)
- **패키지 관리**: uv (Rust 기반 고속 패키지 매니저)
- **Python 버전**: 3.11+
- **빌드 시스템**: pyproject.toml (PEP 621)

### 코드 품질 도구
- **Linter**: ruff (Rust 기반 고속 린터)
- **Formatter**: black
- **Import Sorter**: isort
- **테스트**: pytest
- **타입 검사**: 타입 힌트 (mypy는 미사용)

### 외부 의존성
- **GitHub API**: gh CLI를 통한 간접 호출
- **Git**: 시스템 git 명령어 직접 호출
- **Shell**: subprocess를 통한 명령어 실행

## 프로젝트 구조

```
src/cli_git/
├── __init__.py          # 버전 정보
├── __main__.py          # 모듈 진입점
├── cli.py               # 메인 CLI 애플리케이션
├── commands/            # 명령어 구현
│   ├── modules/         # 공통 모듈
│   │   ├── interactive.py    # 대화형 선택
│   │   ├── scan.py          # 저장소 스캔
│   │   └── workflow_updater.py # 워크플로우 업데이트
│   ├── completion.py    # 자동완성 설치
│   ├── info.py          # 정보 표시
│   ├── init.py          # 초기 설정
│   ├── private_mirror.py # 프라이빗 미러 생성
│   └── update_mirrors.py # 미러 업데이트
├── completion/          # 자동완성 로직
│   └── completers.py    # 완성 함수들
├── core/               # 핵심 비즈니스 로직
│   └── workflow.py     # GitHub Actions 워크플로우
└── utils/              # 유틸리티
    ├── config.py       # 설정 관리
    ├── gh.py           # GitHub API 래퍼
    ├── git.py          # Git 유틸리티
    └── validators.py   # 입력 검증
```

## 데이터 흐름

### 1. 사용자 입력 처리
```
사용자 명령어 → Typer 파싱 → 타입 검증 → 명령어 함수 실행
```

### 2. GitHub API 호출 패턴
```
Python 함수 → subprocess → gh CLI → GitHub REST API → JSON 응답
```

### 3. 설정 및 캐시 관리
```
~/.cli-git/
├── settings.toml        # TOML 형식 설정 파일
└── cache/
    ├── recent_mirrors.json      # 최근 미러 10개
    ├── scanned_mirrors.json     # 스캔된 미러 (30분 TTL)
    └── repo_completion.json     # 자동완성 캐시 (10분 TTL)
```

## 캐싱 전략

### 캐시 계층 구조
1. **Level 1**: scanned_mirrors (가장 빠름, 30분 TTL)
2. **Level 2**: repo_completion (빠름, 10분 TTL)
3. **Level 3**: recent_mirrors (로컬 히스토리, 무제한)
4. **Level 4**: GitHub API (느림, 실시간)

### 캐시 정책
- **LRU 없음**: 시간 기반 만료만 사용
- **크기 제한**: recent_mirrors만 10개 제한
- **수동 무효화**: 파일 삭제로만 가능

## 성능 최적화

### API 호출 최소화
- 다층 캐시 구조
- 배치 요청 없음 (순차 처리)
- 결과 개수 제한 (20개)

### 메모리 사용량
- 대용량 데이터 스트리밍 없음
- JSON 파일 전체 로드
- 캐시 파일 크기 < 1MB

### 함수형 프로그래밍 스타일
- 순수 함수 우선 사용
- 부작용 명시적 분리
- 고차 함수 활용 (partial, compose)

## 에러 처리 전략

### 예외 계층
```python
Exception
├── GitHubError          # GitHub API 관련 오류
├── ValidationError      # 입력 검증 오류
└── ConfigError          # 설정 파일 오류
```

### 에러 복구 정책
- **GitHub API 실패**: 캐시로 폴백
- **설정 파일 손상**: 기본값으로 재생성
- **네트워크 오류**: 명확한 에러 메시지 출력

## 보안 고려사항

### 민감 정보 처리
- GitHub 토큰: 600 권한으로 설정 파일 저장
- 임시 파일: 즉시 삭제
- 로그: 민감 정보 마스킹

### GitHub Actions 보안
- Personal Access Token 사용 (GITHUB_TOKEN 아님)
- 필요 최소 권한: repo, workflow
- 시크릿 업데이트만 수행 (읽기 없음)

## 테스트 전략

### 테스트 구조
- **Unit Tests**: 개별 함수 테스트
- **Integration Tests**: GitHub API 목킹
- **E2E Tests**: 없음 (GitHub API 제약)

### Mock 전략
- subprocess 호출 모킹
- 파일 시스템 작업 모킹
- 시간 의존성 모킹

### 커버리지 목표
- 최소 85% 코드 커버리지
- 모든 명령어 경로 테스트
- 에러 케이스 포함
