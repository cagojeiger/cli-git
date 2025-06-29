# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Instructions

1. **오캄의 면도날 (Occam's Razor)**:
   - 가장 단순한 해결책을 먼저 고려하라
   - 필요 이상으로 복잡하게 만들지 마라
   - "Entities should not be multiplied without necessity"
   - 새로운 기능 구현 시 항상 "더 간단한 방법은 없을까?" 자문하라
   - 예: 복잡한 브랜치 추적 로직 대신 GitHub Actions가 처리하도록 위임

2. **Planning Before Coding**: When the user requests a task, DO NOT immediately start writing code. First, create a detailed plan of how you will approach the work and ensure you deeply understand the user's intent. Immediate coding without planning often leads to misunderstanding the user's requirements. Think deeply about the task before implementation.

3. **Documentation Language**: All user-facing documentation (README, docs) must be written in Korean

4. **Code Quality**: Maintain >90% test coverage

5. **Code Refactoring**: If any file exceeds 500 lines, plan and implement refactoring to split it into smaller, focused modules

6. **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/) specification

7. **Docstring Style**: Follow [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for all docstrings

8. **Post-Code Completion**: After any code changes, always run these 3 commands in order:
   ```bash
   # 1. Update pre-commit hooks
   uv run pre-commit autoupdate

   # 2. Run all pre-commit hooks
   uv run pre-commit run --all-files

   # 3. Run tests
   uv run pytest
   ```
9. **CI Verification After Push**: When pushing to a branch with an open PR, always verify that all CI checks pass. Use `gh pr checks <PR_NUMBER>` to monitor status and `gh run view <RUN_ID> --log-failed` to debug failures. Ensure successful completion before considering the task complete.


## Project Overview

**cli-git** - A modern Python CLI tool for Git operations built with:
- **uv** for fast package management
- **typer** for CLI framework
- **TDD** (Test-Driven Development) methodology
- **Functional programming** paradigm

## Repository Structure

```
cli-git/
├── .docs/                     # Project documentation
├── .github/
│   └── workflows/
│       ├── slack-notifications.yml    # Slack notifications for failures
│       ├── test.yml           # CI testing pipeline
│       └── release.yml        # Automated PyPI releases (manual trigger)
├── config/                    # Configuration files
│   ├── ruff.toml             # Ruff linter config
│   ├── pytest.ini            # Pytest config
│   └── .coveragerc           # Coverage config
├── src/
│   └── cli_git/
│       ├── __init__.py       # Package init with version
│       ├── __main__.py       # Module entry point
│       ├── cli.py            # Main CLI implementation
│       └── commands/         # Subcommands directory
├── tests/                    # Test files (pytest)
├── .gitignore               # Python-specific ignores
├── LICENSE                  # MIT License
├── pyproject.toml          # Project configuration
└── uv.lock                 # Dependency lock file
```

## Development Commands

```bash
# Install dependencies
uv sync --all-extras --dev

# Update dependencies to latest versions
uv lock --upgrade

# Install pre-commit hooks (first time only)
uv run pre-commit install

# Run tests
uv run pytest -c config/pytest.ini

# Run a single test file
uv run pytest tests/test_version.py -v

# Run tests with coverage report
uv run pytest --cov --cov-report=term-missing

# Run tests for specific module with coverage
uv run pytest tests/test_cli.py --cov=cli_git.cli --cov-report=term-missing

# Run linters
uv run ruff check --config config/ruff.toml src tests
uv run black src tests
uv run isort src tests

# Fix linting issues
uv run ruff check --config config/ruff.toml src tests --fix
uv run black src tests
uv run isort src tests

# Run all pre-commit hooks
uv run pre-commit run --all-files

# Build package
uv build

# Run CLI locally
uv run cli-git --version

# Check for type errors (if mypy is added)
# uv run mypy src

# Generate coverage HTML report
uv run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

## Development Principles

### Test-Driven Development (TDD)
1. **Write tests first** - Always write failing tests before implementation
2. **Red-Green-Refactor** cycle:
   - Red: Write a failing test
   - Green: Write minimal code to pass
   - Refactor: Improve code while keeping tests green
3. **Test coverage** - Maintain >90% test coverage

### Functional Programming Style
1. **Pure functions** - Functions should have no side effects
2. **Immutability** - Avoid mutating data structures
3. **Function composition** - Build complex behavior from simple functions
4. **Higher-order functions** - Functions that accept/return other functions
5. **Avoid classes when functions suffice** - Prefer functions over classes

Example pattern from the codebase:
```python
# Pure function
def create_version_message(version: str) -> str:
    return f"cli-git version: {version}"

# Higher-order function
def display_message(message_creator: Callable[[str], str], version: str) -> None:
    typer.echo(message_creator(version))

# Function composition with partial application
display_version = partial(display_message, create_version_message)
```

## CI/CD Pipeline

### GitHub Actions Workflows
1. **test.yml** - Runs on PR/push:
   - Two separate jobs: pre-commit (Ubuntu only) and test (Ubuntu only)
   - Python 3.11 and 3.12
   - Pre-commit hooks run first, then tests
   - Test coverage reporting with Codecov

2. **release.yml** - Runs on main branch:
   - Semantic versioning based on commits
   - Automated PyPI publishing
   - TestPyPI validation before production

### Required Secrets
- `SLACK_WEBHOOK_URL` - For workflow failure notifications
- PyPI trusted publisher configuration (no API token needed)

## Conventional Commits

Commit format determines version bumps:
- `feat:` → Minor version (0.X.0)
- `fix:` → Patch version (0.0.X)
- `BREAKING CHANGE:` → Major version (X.0.0)
- `docs:` → No version bump
- `test:` → No version bump
- `chore:` → No version bump

## Adding New Features

1. Start with TDD:
   ```bash
   # 1. Write test first
   # 2. Run test to see it fail
   uv run pytest tests/test_new_feature.py -v
   # 3. Implement feature
   # 4. Run test to see it pass
   ```

2. Follow functional style:
   - Separate I/O from logic
   - Use type hints
   - Prefer composition over inheritance

3. Update tests and ensure coverage:
   ```bash
   uv run pytest --cov
   ```

## PyPI Publishing

The project uses semantic-release for automated versioning and publishing:
1. **Manual trigger only** - release.yml requires manual workflow dispatch
2. Version is automatically determined from commit messages
3. Package is built and tested on TestPyPI first
4. If successful, published to production PyPI

To set up PyPI publishing:
1. Create PyPI account
2. Add trusted publisher for GitHub Actions
3. Configure environment protection rules

## Code Quality Standards

- **Test Coverage**: Minimum 90% required (configured in config/pytest.ini)
- **Line Length**: 100 characters (black and isort configured)
- **Python Versions**: Support 3.11 and 3.12
- **Pre-commit**: Always run before committing (`uv run pre-commit run --all-files`)

## Context Management

When working on complex features or conducting deep analysis:
1. **Create context files**: Important insights and plans should be saved as `.context/00-*.md`
2. **Numbering system**: Use two-digit prefixes (00-99) to maintain order
3. **Content structure**: Each context file should include:
   - Clear title and purpose
   - Detailed analysis or plan
   - Technical considerations
   - Next steps
4. **Git ignored**: `.context/` directory is in .gitignore to keep these notes private
