# cli-git

현대적인 Git 작업을 위한 Python CLI 도구

## 기능

- **프라이빗 미러링**: 오픈소스 리포지토리를 프라이빗 미러로 생성
- **자동 동기화**: GitHub Actions를 통한 rebase 기반 자동 동기화
- **Slack 알림**: 동기화 충돌 시 Slack 알림
- **자동완성**: 쉘 자동완성 지원 (Bash, Zsh, Fish)
- **입력값 검증**: 모든 입력값에 대한 실시간 검증
- **조직 지원**: GitHub 조직에 미러 생성
- **원본 워크플로우 비활성화**: 원본 CI/CD가 미러에서 실행되지 않도록 자동 처리

## 빠른 시작

### 설치

#### pipx 사용 (권장)

```bash
# pipx가 없다면 먼저 설치
pip install pipx
pipx ensurepath

# cli-git 설치
pipx install cli-git
```

#### 소스에서 설치

```bash
# 소스 코드 클론
git clone https://github.com/cagojeiger/cli-git.git
cd cli-git

# 개발 모드로 설치
pipx install -e . --force
```

### 초기 설정

```bash
# GitHub CLI 인증 (필수)
gh auth login

# cli-git 초기화
cli-git init
```

초기화 과정에서 설정할 수 있는 항목:
- **조직 선택**: 속한 GitHub 조직 목록에서 선택
- **Slack 알림**: 동기화 충돌 시 알림받을 Slack webhook URL
- **미러 prefix**: 기본 미러 이름 prefix (예: mirror-, fork-)

### 기본 사용법

```bash
# 버전 확인
cli-git --version

# 설정 확인
cli-git info

# 프라이빗 미러 생성
cli-git private-mirror https://github.com/facebook/react

# 조직에 미러 생성
cli-git private-mirror https://github.com/vuejs/vue --org mycompany

# 커스텀 이름으로 미러 생성
cli-git private-mirror https://github.com/angular/angular --repo my-angular

# 커스텀 prefix 사용
cli-git private-mirror https://github.com/sveltejs/svelte --prefix "fork-"

# 자동 동기화 없이 미러만 생성
cli-git private-mirror https://github.com/microsoft/vscode --no-sync
```

### 자동완성 설치

```bash
# 자동완성 설치
cli-git completion

# 쉘 재시작 또는 설정 파일 다시 로드
source ~/.bashrc  # Bash
source ~/.zshrc   # Zsh
```

## 주요 기능

### 1. 프라이빗 미러링

오픈소스 리포지토리를 프라이빗 미러로 복사하여 안전하게 분석하고 수정할 수 있습니다.

- 모든 브랜치와 태그 복사
- 원본 CI/CD 워크플로우 자동 비활성화
- 커스텀 이름 및 prefix 지원

### 2. 자동 동기화

GitHub Actions를 통해 업스트림 변경사항을 자동으로 동기화합니다.

- **Rebase 기반**: 깔끔한 히스토리 유지
- **충돌 없음**: main에 바로 push
- **충돌 발생**: PR 생성 후 Slack 알림
- **개인 변경사항 보존**: rebase를 통해 사용자의 커밋 유지

### 3. Slack 통합

동기화 중 충돌이 발생하면 Slack으로 알림을 받습니다.

- 충돌 감지 시에만 알림
- PR 링크 포함
- init 시 webhook URL 설정

### 4. 자동완성 및 검증

주요 옵션에 대한 자동완성과 입력값 검증을 제공합니다.

- `--org`: 속한 GitHub 조직 목록 (실제 접근 권한 검증)
- `--schedule`: 일반적인 cron 패턴 (유효한 형식 검증)
- `--prefix`: 자주 사용하는 prefix 패턴 (유효한 문자 검증)
- **URL 검증**: 유효한 GitHub 리포지토리 URL 형식 확인
- **리포지토리 이름 검증**: GitHub 명명 규칙 준수 확인

## 고급 사용법

### 동기화 스케줄 커스터마이징

```bash
# 매시간 동기화
cli-git private-mirror https://github.com/owner/repo --schedule "0 * * * *"

# 매주 일요일 자정 동기화
cli-git private-mirror https://github.com/owner/repo --schedule "0 0 * * 0"

# 하루 두 번 (자정, 정오)
cli-git private-mirror https://github.com/owner/repo --schedule "0 0,12 * * *"
```

### 워크플로우 비활성화

원본 리포지토리의 CI/CD 워크플로우는 자동으로 비활성화됩니다:

- `.github/workflows/` → `.github/workflows-disabled/`
- 참고용으로 보존
- 필요시 수동으로 복원 가능

### 미러 관리

```bash
# 설정 및 최근 미러 확인
cli-git info

# JSON 형태로 출력
cli-git info --json
```

## 문제 해결

### 1. GitHub CLI 인증 문제

```bash
# 인증 상태 확인
gh auth status

# 재인증
gh auth login
```

### 2. 동기화 충돌

동기화 중 충돌 발생 시:

1. Slack 알림 확인
2. PR에서 충돌 해결
3. PR 머지

### 3. 자동완성 문제

```bash
# 자동완성 재설치
cli-git completion

# 쉘 설정 파일 확인
cat ~/.bashrc | grep cli-git  # Bash
cat ~/.zshrc | grep cli-git   # Zsh
```

## 설정 파일

설정은 `~/.cli-git/settings.toml`에 저장됩니다:

```toml
# cli-git configuration file
# Generated automatically - feel free to edit

[github]
# GitHub account information
username = "your-username"
default_org = "your-org"
slack_webhook_url = "https://hooks.slack.com/..."

[preferences]
# User preferences
default_schedule = "0 0 * * *"
default_prefix = "mirror-"
analysis_template = "backend"
```

## 라이선스

MIT License - [LICENSE](LICENSE) 파일 참조
