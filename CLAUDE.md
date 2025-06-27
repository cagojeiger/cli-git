# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
├── .plan/                     # Development planning documents
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
   - Multi-OS testing (Ubuntu, Windows, macOS)
   - Python 3.11 and 3.12
   - Linting and formatting checks
   - Test coverage reporting

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
1. Commits to main trigger the release workflow
2. Version is automatically determined from commit messages
3. Package is built and tested on TestPyPI first
4. If successful, published to production PyPI

To set up PyPI publishing:
1. Create PyPI account
2. Add trusted publisher for GitHub Actions
3. Configure environment protection rules
