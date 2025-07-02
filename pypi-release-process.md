# PyPI 릴리스 프로세스

이 문서는 `cli-git` 패키지를 PyPI와 TestPyPI에 배포하기 위한 완전한 가이드입니다.

## 목차

1. [사전 준비](#사전-준비)
2. [PyPI 계정 설정](#pypi-계정-설정)
3. [TestPyPI 계정 설정](#testpypi-계정-설정)
4. [GitHub Secrets 설정](#github-secrets-설정)
5. [릴리스 프로세스](#릴리스-프로세스)
6. [트러블슈팅](#트러블슈팅)

## 사전 준비

- PyPI 계정
- TestPyPI 계정
- GitHub 저장소 관리자 권한
- 2FA(Two-Factor Authentication) 설정

## PyPI 계정 설정

### 1. 계정 생성

1. [https://pypi.org/](https://pypi.org/) 접속
2. "Register" 클릭하여 계정 생성
3. 이메일 인증 완료

### 2. 2FA 활성화 (필수)

1. 계정 설정으로 이동
2. "Enable two-factor authentication" 선택
3. 인증 앱(Google Authenticator, Authy 등) 사용하여 설정

### 3. API 토큰 생성

1. 계정 설정 → "API tokens" 메뉴
2. "Add API token" 클릭
3. 토큰 설정:
   - **Token name**: `cli-git-github-actions`
   - **Scope**: "Entire account" 또는 특정 프로젝트 선택
4. 생성된 토큰을 안전한 곳에 저장 (한 번만 표시됨!)

## TestPyPI 계정 설정

### 1. 계정 생성

1. [https://test.pypi.org/](https://test.pypi.org/) 접속
2. PyPI와 동일한 방법으로 계정 생성 (별도 계정 필요)

### 2. API 토큰 생성

1. 계정 설정 → "API tokens" 메뉴
2. "Add API token" 클릭
3. 토큰 설정:
   - **Token name**: `cli-git-github-actions-test`
   - **Scope**: "Entire account"
4. 토큰 저장

## GitHub Secrets 설정

### 필요한 Secrets

1. **PYPI_API_TOKEN**: PyPI 배포용 토큰
2. **TEST_PYPI_API_TOKEN**: TestPyPI 배포용 토큰
3. **GH_TOKEN**: (선택사항) GitHub 작업용 토큰

### 설정 방법

1. GitHub 저장소 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. 각 토큰 추가:
   ```
   Name: PYPI_API_TOKEN
   Secret: pypi-토큰값 (pypi- 로 시작)
   ```
   ```
   Name: TEST_PYPI_API_TOKEN
   Secret: pypi-토큰값
   ```

## 릴리스 프로세스

### 1. 코드 변경 및 커밋

```bash
# 기능 개발
git add .
git commit -m "feat: 새로운 기능 추가"
```

### 2. 커밋 메시지 규칙

semantic-release가 버전을 자동으로 결정합니다:

- `feat:` → 마이너 버전 업 (0.X.0)
- `fix:` → 패치 버전 업 (0.0.X)
- `BREAKING CHANGE:` → 메이저 버전 업 (X.0.0)
- `docs:`, `test:`, `chore:` → 버전 변경 없음

### 3. main 브랜치에 푸시

```bash
git push origin main
```

### 4. GitHub Actions 모니터링

1. Actions 탭에서 "Release" 워크플로우 확인
2. 성공 시:
   - 새 버전 태그 생성
   - TestPyPI에 업로드
   - PyPI에 업로드 (rc/beta 제외)

### 5. 배포 확인

```bash
# PyPI에서 설치 테스트
pipx install cli-git --force

# TestPyPI에서 설치 테스트
pipx install --index-url https://test.pypi.org/simple/ cli-git --force
```

## 트러블슈팅

### 일반적인 오류

#### 1. "Invalid or non-existent authentication"

- API 토큰이 올바르게 설정되었는지 확인
- `pypi-` 접두사 포함 여부 확인

#### 2. "Version already exists"

- 이미 배포된 버전은 덮어쓸 수 없음
- 버전 번호를 올려서 다시 시도

#### 3. "Build failed"

- `uv sync` 실행하여 의존성 확인
- `uv run python -m build` 로컬에서 테스트

### 롤백 방법

PyPI는 배포된 버전을 삭제할 수 없으므로:

1. 문제가 있는 버전을 "yanked" 처리
2. 수정 후 새 버전으로 재배포

```bash
# PyPI 웹사이트에서 해당 버전 → "Yank" 버튼 클릭
```

### 수동 배포 (긴급 시)

```bash
# 로컬에서 수동 배포
uv run python -m build
uv run twine check dist/*
uv run twine upload dist/*
```

## 참고 링크

- [PyPI 공식 문서](https://pypi.org/help/)
- [TestPyPI 가이드](https://packaging.python.org/guides/using-testpypi/)
- [Twine 문서](https://twine.readthedocs.io/)
- [Semantic Release](https://python-semantic-release.readthedocs.io/)
