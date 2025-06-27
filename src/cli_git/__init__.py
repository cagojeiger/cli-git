"""cli-git: A modern Python CLI tool for Git operations."""

try:
    from importlib.metadata import version

    __version__ = version("cli-git")
except Exception:
    __version__ = "dev"
