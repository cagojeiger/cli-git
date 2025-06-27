# 개발 가이드

## 사전 요구사항

- Python 3.11 또는 3.12
- uv (설치: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Git

## 초기 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/cli-git.git
cd cli-git

# 의존성 설치
uv sync --all-extras --dev

# 설치 확인
uv run cli-git --version
```

## 개발 워크플로우

### 1. 테스트 주도 개발 (TDD)

#### TDD 사이클
```
┌─────────────┐
│ 테스트 작성 │ ──► RED (테스트 실패)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  코드 작성  │ ──► GREEN (테스트 통과)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  리팩토링   │ ──► 여전히 GREEN
└─────────────┘
```

#### TDD 플로우 예제

1. **실패하는 테스트 작성**:
```python
# tests/test_new_feature.py
def test_parse_git_url():
    """Git URL을 컴포넌트로 파싱하는 테스트."""
    from cli_git.utils import parse_git_url

    result = parse_git_url("git@github.com:user/repo.git")
    assert result == {
        "host": "github.com",
        "user": "user",
        "repo": "repo"
    }
```

2. **테스트 실행하여 실패 확인**:
```bash
uv run pytest tests/test_new_feature.py -v
# 예상: ImportError 또는 AssertionError
```

3. **통과하기 위한 최소한의 코드 작성**:
```python
# src/cli_git/utils.py
def parse_git_url(url: str) -> dict[str, str]:
    # 최소한의 구현
    parts = url.split(":")
    host = parts[0].split("@")[1]
    user_repo = parts[1].replace(".git", "").split("/")
    return {
        "host": host,
        "user": user_repo[0],
        "repo": user_repo[1]
    }
```

4. **테스트 실행하여 통과 확인**:
```bash
uv run pytest tests/test_new_feature.py -v
# 예상: PASSED
```

5. **자신있게 리팩토링**:
```python
# 개선된 구현
from typing import TypedDict
from functools import partial
import re

class GitURLComponents(TypedDict):
    host: str
    user: str
    repo: str

def extract_host(url: str) -> str:
    """호스트를 추출하는 순수 함수."""
    return url.split("@")[1].split(":")[0]

def extract_user_repo(url: str) -> tuple[str, str]:
    """사용자와 저장소를 추출하는 순수 함수."""
    path = url.split(":")[1].replace(".git", "")
    user, repo = path.split("/")
    return user, repo

def parse_git_url(url: str) -> GitURLComponents:
    """함수 합성을 사용하여 Git URL을 컴포넌트로 파싱."""
    host = extract_host(url)
    user, repo = extract_user_repo(url)
    return GitURLComponents(host=host, user=user, repo=repo)
```

### 2. 함수형 프로그래밍 가이드라인

#### 순수 함수
```python
# ❌ 불순 - 부작용이 있음
def save_config(config: dict) -> None:
    with open("config.json", "w") as f:
        json.dump(config, f)
    print("Config saved!")  # 부작용

# ✅ 순수 - 부작용 없음
def serialize_config(config: dict) -> str:
    return json.dumps(config, indent=2)

def save_config(config: dict, writer: Callable[[str], None]) -> None:
    """I/O를 로직에서 분리."""
    serialized = serialize_config(config)
    writer(serialized)
```

#### 함수 합성
```python
from functools import partial, reduce
from operator import add

# 함수 합성
def compose(*funcs):
    """함수를 오른쪽에서 왼쪽으로 합성."""
    return reduce(lambda f, g: lambda x: f(g(x)), funcs)

# 사용 예
process_data = compose(
    format_output,
    calculate_result,
    validate_input
)

result = process_data(raw_input)
```

#### 변경 방지
```python
# ❌ 변경함
def add_timestamp(data: dict) -> dict:
    data["timestamp"] = datetime.now()  # 입력을 변경
    return data

# ✅ 불변
def add_timestamp(data: dict) -> dict:
    return {**data, "timestamp": datetime.now()}
```

### 3. 새 명령어 추가

1. **명령어 모듈 생성**:
```python
# src/cli_git/commands/status.py
from typing import List
from functools import partial

def format_status_line(file: str, status: str) -> str:
    """상태 라인을 포맷하는 순수 함수."""
    return f"{status:>10} {file}"

def get_status_lines(files: List[tuple[str, str]]) -> List[str]:
    """파일 목록을 포맷된 라인으로 변환."""
    return [format_status_line(file, status) for file, status in files]
```

2. **CLI 래퍼 추가**:
```python
# src/cli_git/cli.py
@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v")
) -> None:
    """작업 트리 상태 표시."""
    # I/O 작업
    files = git_operations.get_changed_files()

    # 순수 변환
    lines = get_status_lines(files)

    # 출력
    for line in lines:
        typer.echo(line)
```

### 4. 코드 품질

#### 커밋하기 전에:
```bash
# 테스트 실행
uv run pytest

# 코드 스타일 검사
uv run ruff check src tests
uv run black --check src tests
uv run isort --check-only src tests

# 스타일 문제 수정
uv run ruff check src tests --fix
uv run black src tests
uv run isort src tests
```

#### 테스트 커버리지
```bash
# 커버리지와 함께 실행
uv run pytest --cov

# HTML 리포트 생성
uv run pytest --cov --cov-report=html
# 브라우저에서 htmlcov/index.html 열기
```

### 5. 디버깅

#### Python 디버거 사용
```python
# 코드에 중단점 추가
def complex_function(data):
    import pdb; pdb.set_trace()  # 중단점
    result = process(data)
    return result
```

#### VS Code 디버깅
1. `.vscode/launch.json` 생성:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug CLI",
            "type": "python",
            "request": "launch",
            "module": "cli_git",
            "args": ["--version"],
            "justMyCode": true
        }
    ]
}
```

### 6. 성능 테스트

```python
# tests/test_performance.py
import pytest
from time import time

def test_performance_parse_large_input():
    """대용량 입력 파싱이 100ms 미만인지 확인."""
    large_input = generate_large_input()

    start = time()
    result = parse_function(large_input)
    duration = time() - start

    assert duration < 0.1  # 100ms 임계값
```

## 일반적인 패턴

### 오류 처리를 위한 Result 타입
```python
from typing import Union, TypeVar, Generic

T = TypeVar("T")
E = TypeVar("E")

class Ok(Generic[T]):
    def __init__(self, value: T):
        self.value = value

class Err(Generic[E]):
    def __init__(self, error: E):
        self.error = error

Result = Union[Ok[T], Err[E]]

def safe_divide(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Err("0으로 나눌 수 없습니다")
    return Ok(a / b)
```

### 비용이 큰 작업을 위한 메모이제이션
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """캐시된 계산."""
    # 복잡한 계산
    return result
```

## 문제 해결

### 일반적인 문제

1. **임포트 오류**: `uv run`을 사용하여 명령어를 실행하는지 확인
2. **테스트 실패**: 올바른 가상 환경에 있는지 확인
3. **타입 오류**: `mypy src`를 실행하여 타입 주석 확인

### 도움 받기

1. 예제를 위해 기존 테스트 확인
2. 아키텍처 문서 읽기
3. GitHub 이슈에서 질문
4. 유사한 함수형 Python 프로젝트 검토
