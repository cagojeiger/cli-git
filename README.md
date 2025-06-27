# cli-git

현대적인 Git 작업을 위한 Python CLI 도구

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

### 기본 사용법

```bash
# 버전 확인
cli-git --version

# 도움말
cli-git --help
```

## 라이선스

MIT License - [LICENSE](LICENSE) 파일 참조
