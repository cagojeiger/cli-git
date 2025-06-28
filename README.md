# cli-git

현대적인 Git 작업을 위한 Python CLI 도구

## 설치

```bash
# pipx 설치 (권장)
pip install pipx
pipx ensurepath
pipx install cli-git

# 또는 소스에서 설치
git clone https://github.com/cagojeiger/cli-git.git
cd cli-git
pipx install -e . --force
```

## 사용법

```bash
# 초기 설정
gh auth login
cli-git init

# 프라이빗 미러 생성
cli-git private-mirror https://github.com/owner/repo

# 자동완성 설치
cli-git completion
```
