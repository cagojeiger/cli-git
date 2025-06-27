# Development Guide

## Prerequisites

- Python 3.11 or 3.12
- uv (install with `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Git

## Initial Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/cli-git.git
cd cli-git

# Install dependencies
uv sync --all-extras --dev

# Verify installation
uv run cli-git --version
```

## Development Workflow

### 1. Test-Driven Development (TDD)

#### The TDD Cycle
```
┌─────────────┐
│  Write Test │ ──► RED (Test Fails)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│ Write Code  │ ──► GREEN (Test Passes)
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Refactor   │ ──► Still GREEN
└─────────────┘
```

#### Example TDD Flow

1. **Write a failing test**:
```python
# tests/test_new_feature.py
def test_parse_git_url():
    """Test parsing Git URLs into components."""
    from cli_git.utils import parse_git_url

    result = parse_git_url("git@github.com:user/repo.git")
    assert result == {
        "host": "github.com",
        "user": "user",
        "repo": "repo"
    }
```

2. **Run test to see it fail**:
```bash
uv run pytest tests/test_new_feature.py -v
# Expected: ImportError or AssertionError
```

3. **Write minimal code to pass**:
```python
# src/cli_git/utils.py
def parse_git_url(url: str) -> dict[str, str]:
    # Minimal implementation
    parts = url.split(":")
    host = parts[0].split("@")[1]
    user_repo = parts[1].replace(".git", "").split("/")
    return {
        "host": host,
        "user": user_repo[0],
        "repo": user_repo[1]
    }
```

4. **Run test to see it pass**:
```bash
uv run pytest tests/test_new_feature.py -v
# Expected: PASSED
```

5. **Refactor with confidence**:
```python
# Improved implementation
from typing import TypedDict
from functools import partial
import re

class GitURLComponents(TypedDict):
    host: str
    user: str
    repo: str

def extract_host(url: str) -> str:
    """Pure function to extract host."""
    return url.split("@")[1].split(":")[0]

def extract_user_repo(url: str) -> tuple[str, str]:
    """Pure function to extract user and repo."""
    path = url.split(":")[1].replace(".git", "")
    user, repo = path.split("/")
    return user, repo

def parse_git_url(url: str) -> GitURLComponents:
    """Parse Git URL into components using function composition."""
    host = extract_host(url)
    user, repo = extract_user_repo(url)
    return GitURLComponents(host=host, user=user, repo=repo)
```

### 2. Functional Programming Guidelines

#### Pure Functions
```python
# ❌ Impure - has side effects
def save_config(config: dict) -> None:
    with open("config.json", "w") as f:
        json.dump(config, f)
    print("Config saved!")  # Side effect

# ✅ Pure - no side effects
def serialize_config(config: dict) -> str:
    return json.dumps(config, indent=2)

def save_config(config: dict, writer: Callable[[str], None]) -> None:
    """I/O separated from logic."""
    serialized = serialize_config(config)
    writer(serialized)
```

#### Function Composition
```python
from functools import partial, reduce
from operator import add

# Compose functions
def compose(*funcs):
    """Compose functions right to left."""
    return reduce(lambda f, g: lambda x: f(g(x)), funcs)

# Example usage
process_data = compose(
    format_output,
    calculate_result,
    validate_input
)

result = process_data(raw_input)
```

#### Avoid Mutation
```python
# ❌ Mutating
def add_timestamp(data: dict) -> dict:
    data["timestamp"] = datetime.now()  # Mutates input
    return data

# ✅ Immutable
def add_timestamp(data: dict) -> dict:
    return {**data, "timestamp": datetime.now()}
```

### 3. Adding New Commands

1. **Create command module**:
```python
# src/cli_git/commands/status.py
from typing import List
from functools import partial

def format_status_line(file: str, status: str) -> str:
    """Pure function to format a status line."""
    return f"{status:>10} {file}"

def get_status_lines(files: List[tuple[str, str]]) -> List[str]:
    """Transform file list to formatted lines."""
    return [format_status_line(file, status) for file, status in files]
```

2. **Add CLI wrapper**:
```python
# src/cli_git/cli.py
@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v")
) -> None:
    """Show working tree status."""
    # I/O operations
    files = git_operations.get_changed_files()

    # Pure transformations
    lines = get_status_lines(files)

    # Output
    for line in lines:
        typer.echo(line)
```

### 4. Code Quality

#### Before committing:
```bash
# Run tests
uv run pytest

# Check code style
uv run ruff check src tests
uv run black --check src tests
uv run isort --check-only src tests

# Fix style issues
uv run ruff check src tests --fix
uv run black src tests
uv run isort src tests
```

#### Test Coverage
```bash
# Run with coverage
uv run pytest --cov

# Generate HTML report
uv run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

### 5. Debugging

#### Using Python Debugger
```python
# Add breakpoint in code
def complex_function(data):
    import pdb; pdb.set_trace()  # Breakpoint
    result = process(data)
    return result
```

#### VS Code Debugging
1. Create `.vscode/launch.json`:
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

### 6. Performance Testing

```python
# tests/test_performance.py
import pytest
from time import time

def test_performance_parse_large_input():
    """Ensure parsing stays under 100ms for large inputs."""
    large_input = generate_large_input()

    start = time()
    result = parse_function(large_input)
    duration = time() - start

    assert duration < 0.1  # 100ms threshold
```

## Common Patterns

### Result Type for Error Handling
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
        return Err("Division by zero")
    return Ok(a / b)
```

### Memoization for Expensive Operations
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n: int) -> int:
    """Cached computation."""
    # Complex calculation here
    return result
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're using `uv run` to execute commands
2. **Test failures**: Check if you're in the correct virtual environment
3. **Type errors**: Run `mypy src` to check type annotations

### Getting Help

1. Check existing tests for examples
2. Read the architecture documentation
3. Ask in GitHub issues
4. Review similar functional Python projects
