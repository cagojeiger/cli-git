"""Configuration classes for mirror operations."""

from dataclasses import dataclass


@dataclass
class MirrorConfig:
    """Configuration for mirror operation."""

    upstream_url: str
    target_name: str
    username: str
    org: str | None = None
    schedule: str = "0 0 * * *"
    no_sync: bool = False
    slack_webhook_url: str | None = None
    github_token: str | None = None
