"""Data models for update operations."""

from dataclasses import dataclass


@dataclass
class MirrorUpdateResult:
    """Result of mirror update operation."""

    success_count: int = 0
    total_count: int = 0
    failed_mirrors: list[str] = None

    def __post_init__(self):
        if self.failed_mirrors is None:
            self.failed_mirrors = []
