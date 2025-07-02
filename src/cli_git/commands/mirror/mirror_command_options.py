"""Command options for mirror operations."""

from dataclasses import dataclass
from typing import Annotated

import typer

from cli_git.completion.completers import complete_organization, complete_prefix, complete_schedule


@dataclass
class MirrorCommandOptions:
    """Options for private mirror command."""

    upstream: str
    repo: str | None = None
    org: str | None = None
    prefix: str | None = None
    schedule: str = "0 0 * * *"
    no_sync: bool = False

    @classmethod
    def from_typer_args(
        cls,
        upstream: Annotated[str, typer.Argument(help="Upstream repository URL")],
        repo: Annotated[
            str | None, typer.Option("--repo", "-r", help="Mirror repository name")
        ] = None,
        org: Annotated[
            str | None,
            typer.Option(
                "--org", "-o", help="Target organization", autocompletion=complete_organization
            ),
        ] = None,
        prefix: Annotated[
            str | None,
            typer.Option(
                "--prefix", "-p", help="Mirror name prefix", autocompletion=complete_prefix
            ),
        ] = None,
        schedule: Annotated[
            str,
            typer.Option(
                "--schedule",
                "-s",
                help="Sync schedule (cron format)",
                autocompletion=complete_schedule,
            ),
        ] = "0 0 * * *",
        no_sync: Annotated[
            bool, typer.Option("--no-sync", help="Disable automatic synchronization")
        ] = False,
    ) -> "MirrorCommandOptions":
        """Create options from typer arguments."""
        return cls(
            upstream=upstream,
            repo=repo,
            org=org,
            prefix=prefix,
            schedule=schedule,
            no_sync=no_sync,
        )
