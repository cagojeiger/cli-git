"""Tests for ConfigManager."""

from unittest.mock import patch

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

    def test_save_and_get_repo_completion_cache(self, tmp_path):
        """Test saving and retrieving repository completion cache."""
        manager = ConfigManager(tmp_path / ".cli-git")

        # Test data
        repos = [
            {
                "nameWithOwner": "testuser/repo1",
                "description": "Test repo 1",
                "is_mirror": True,
                "updatedAt": "2025-01-01T00:00:00Z",
            },
            {
                "nameWithOwner": "testuser/repo2",
                "description": "Test repo 2",
                "is_mirror": False,
                "updatedAt": "2025-01-02T00:00:00Z",
            },
        ]

        # Save cache
        manager.save_repo_completion_cache(repos)

        # Retrieve cache
        cached_repos = manager.get_repo_completion_cache()

        assert cached_repos is not None
        assert len(cached_repos) == 2
        assert cached_repos[0]["nameWithOwner"] == "testuser/repo1"
        assert cached_repos[0]["is_mirror"] is True
        assert cached_repos[1]["nameWithOwner"] == "testuser/repo2"
        assert cached_repos[1]["is_mirror"] is False

    def test_repo_completion_cache_expiry(self, tmp_path):
        """Test that repository completion cache expires after max_age."""
        import time

        manager = ConfigManager(tmp_path / ".cli-git")

        # Save cache
        repos = [{"nameWithOwner": "testuser/repo1", "is_mirror": True}]

        # Mock time for save operation
        current_time = time.time()
        with patch("time.time", return_value=current_time):
            manager.save_repo_completion_cache(repos)

        # Get cache immediately - should work
        cached = manager.get_repo_completion_cache(max_age=10)
        assert cached is not None
        assert len(cached) == 1

        # Mock time to simulate cache aging
        with patch("time.time") as mock_time:
            # First call returns current time + 20 for age calculation
            # Second call returns timestamp from cache data
            mock_time.side_effect = [current_time + 20, current_time]

            # Get cache with 10 second max age - should be None
            cached = manager.get_repo_completion_cache(max_age=10)
            assert cached is None

            # Reset side_effect for next test
            mock_time.side_effect = [current_time + 20, current_time]

            # Get cache with 30 second max age - should still work
            cached = manager.get_repo_completion_cache(max_age=30)
            assert cached is not None

    def test_save_and_get_scanned_mirrors(self, tmp_path):
        """Test saving and retrieving scanned mirrors cache."""
        manager = ConfigManager(tmp_path / ".cli-git")

        # Test data
        mirrors = [
            {
                "name": "testuser/mirror1",
                "mirror": "https://github.com/testuser/mirror1",
                "upstream": "https://github.com/upstream/repo1",
                "description": "Mirror 1",
            },
            {
                "name": "testuser/mirror2",
                "mirror": "https://github.com/testuser/mirror2",
                "upstream": "",
                "description": "",
            },
        ]

        # Save mirrors
        manager.save_scanned_mirrors(mirrors)

        # Retrieve cached mirrors
        cached = manager.get_scanned_mirrors()
        assert cached is not None
        assert len(cached) == 2
        assert cached[0]["name"] == "testuser/mirror1"

    def test_scanned_mirrors_cache_expiry(self, tmp_path):
        """Test that scanned mirrors cache expires after max_age."""
        import time

        manager = ConfigManager(tmp_path / ".cli-git")

        # Save cache
        mirrors = [{"name": "testuser/mirror1"}]

        # Mock time for save operation
        current_time = time.time()
        with patch("time.time", return_value=current_time):
            manager.save_scanned_mirrors(mirrors)

        # Test with time mocking
        with patch("time.time") as mock_time:
            # First call returns current time + 600 for age calculation
            mock_time.side_effect = [current_time + 600, current_time]

            # Default max_age is 30 minutes - should work
            cached = manager.get_scanned_mirrors()
            assert cached is not None

            # Reset side_effect for next test
            mock_time.side_effect = [current_time + 3600, current_time]

            # After 1 hour - should be None
            cached = manager.get_scanned_mirrors()
            assert cached is None
