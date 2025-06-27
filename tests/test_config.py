"""Tests for ConfigManager."""

from cli_git.utils.config import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager."""

    def test_init_creates_config_dir(self, tmp_path):
        """Test that ConfigManager creates config directory."""
        config_dir = tmp_path / ".cli-git"
        ConfigManager(config_dir)

        assert config_dir.exists()
        assert config_dir.is_dir()
        assert (config_dir / "settings.toml").exists()

    def test_get_default_config(self, tmp_path):
        """Test default configuration values."""
        manager = ConfigManager(tmp_path / ".cli-git")
        config = manager.get_config()

        assert config["github"]["username"] == ""
        assert config["github"]["default_org"] == ""
        assert config["preferences"]["default_schedule"] == "0 0 * * *"

    def test_update_config(self, tmp_path):
        """Test updating configuration."""
        manager = ConfigManager(tmp_path / ".cli-git")

        # Update config
        updates = {"github": {"username": "testuser", "default_org": "testorg"}}
        manager.update_config(updates)

        # Verify updates
        config = manager.get_config()
        assert config["github"]["username"] == "testuser"
        assert config["github"]["default_org"] == "testorg"
        assert config["preferences"]["default_schedule"] == "0 0 * * *"

    def test_config_file_permissions(self, tmp_path):
        """Test that config file has correct permissions."""
        manager = ConfigManager(tmp_path / ".cli-git")
        config_file = manager.config_file

        # Check permissions (should be readable/writable by owner only)
        stat_info = config_file.stat()
        assert oct(stat_info.st_mode)[-3:] == "600"

    def test_preserve_comments_on_update(self, tmp_path):
        """Test that comments are preserved when updating config."""
        manager = ConfigManager(tmp_path / ".cli-git")

        # Read original content
        original_content = manager.config_file.read_text()
        assert "# GitHub account information" in original_content

        # Update config
        manager.update_config({"github": {"username": "newuser"}})

        # Check comments are preserved
        updated_content = manager.config_file.read_text()
        assert "# GitHub account information" in updated_content

    def test_add_recent_mirror(self, tmp_path):
        """Test adding recent mirror to cache."""
        manager = ConfigManager(tmp_path / ".cli-git")

        # Add mirror
        mirror_info = {
            "upstream": "https://github.com/owner/repo",
            "mirror": "https://github.com/user/repo-mirror",
            "created_at": "2025-01-01T00:00:00Z",
        }
        manager.add_recent_mirror(mirror_info)

        # Verify
        mirrors = manager.get_recent_mirrors()
        assert len(mirrors) == 1
        assert mirrors[0]["upstream"] == "https://github.com/owner/repo"

    def test_recent_mirrors_limit(self, tmp_path):
        """Test that recent mirrors are limited to 10."""
        manager = ConfigManager(tmp_path / ".cli-git")

        # Add 15 mirrors
        for i in range(15):
            mirror_info = {
                "upstream": f"https://github.com/owner/repo{i}",
                "mirror": f"https://github.com/user/repo{i}-mirror",
                "created_at": f"2025-01-{i+1:02d}T00:00:00Z",
            }
            manager.add_recent_mirror(mirror_info)

        # Should only keep 10 most recent
        mirrors = manager.get_recent_mirrors()
        assert len(mirrors) == 10
        assert mirrors[0]["upstream"] == "https://github.com/owner/repo14"  # Most recent
        assert mirrors[9]["upstream"] == "https://github.com/owner/repo5"  # 10th most recent
