"""Configuration management for cli-git."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import tomlkit
from tomlkit import comment, document, nl, table


class ConfigManager:
    """Manages cli-git configuration files."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize ConfigManager.

        Args:
            config_dir: Path to configuration directory.
                       Defaults to ~/.cli-git
        """
        self.config_dir = config_dir or Path.home() / ".cli-git"
        self.config_file = self.config_dir / "settings.toml"
        self.cache_dir = self.config_dir / "cache"
        self.mirrors_cache = self.cache_dir / "recent_mirrors.json"

        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

        # Create default config if not exists
        if not self.config_file.exists():
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        doc = document()

        # Add header comment
        doc.add(comment("cli-git configuration file"))
        doc.add(comment("Generated automatically - feel free to edit"))
        doc.add(nl())

        # GitHub section
        github = table()
        github.add(comment("GitHub account information"))
        github["username"] = ""
        github["default_org"] = ""
        github["slack_webhook_url"] = ""
        doc["github"] = github
        doc.add(nl())

        # Preferences section
        prefs = table()
        prefs.add(comment("User preferences"))
        prefs["default_schedule"] = "0 0 * * *"
        prefs["default_prefix"] = "mirror-"
        prefs["analysis_template"] = "backend"
        doc["preferences"] = prefs

        # Write with restricted permissions
        self.config_file.write_text(tomlkit.dumps(doc))
        os.chmod(self.config_file, 0o600)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        content = self.config_file.read_text()
        return tomlkit.loads(content)

    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration while preserving structure and comments.

        Args:
            updates: Dictionary of updates to apply
        """
        content = self.config_file.read_text()
        doc = tomlkit.loads(content)

        # Apply updates
        for section, values in updates.items():
            if section not in doc:
                doc[section] = table()

            for key, value in values.items():
                doc[section][key] = value

        # Write back with preserved permissions
        self.config_file.write_text(tomlkit.dumps(doc))
        os.chmod(self.config_file, 0o600)

    def add_recent_mirror(self, mirror_info: Dict[str, str]) -> None:
        """Add a mirror to recent mirrors cache.

        Args:
            mirror_info: Dictionary containing mirror information
        """
        mirrors = self.get_recent_mirrors()
        mirrors.insert(0, mirror_info)

        # Keep only 10 most recent
        mirrors = mirrors[:10]

        # Save to cache
        self.mirrors_cache.write_text(json.dumps(mirrors, indent=2))

    def get_recent_mirrors(self) -> List[Dict[str, str]]:
        """Get list of recently created mirrors."""
        if not self.mirrors_cache.exists():
            return []

        try:
            content = self.mirrors_cache.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
