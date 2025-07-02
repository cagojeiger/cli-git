"""Cache management utilities for completion and mirror data."""

from typing import Any, Dict, List, Optional

from cli_git.utils.config import ConfigManager


class CacheManager:
    """Centralized cache management for mirror and completion data."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize cache manager.

        Args:
            config_manager: Optional ConfigManager instance
        """
        self.config_manager = config_manager or ConfigManager()

    def get_best_mirror_data(
        self, max_scanned_age: int = 1800, max_completion_age: int = 600
    ) -> Optional[List[Dict[str, Any]]]:
        """Get the best available mirror data from cache hierarchy.

        Args:
            max_scanned_age: Maximum age for scanned mirrors cache in seconds
            max_completion_age: Maximum age for repo completion cache in seconds

        Returns:
            List of mirror data from the best available cache, or None if no cache available
        """
        # Level 1: Scanned mirrors (highest priority)
        scanned_mirrors = self.config_manager.get_scanned_mirrors(max_age=max_scanned_age)
        if scanned_mirrors:
            return scanned_mirrors

        # Level 2: Repo completion cache
        cached_repos = self.config_manager.get_repo_completion_cache(max_age=max_completion_age)
        if cached_repos is not None:
            # Filter only mirrors
            return [repo for repo in cached_repos if repo.get("is_mirror", False)]

        # Level 3: Recent mirrors (fallback)
        return self.config_manager.get_recent_mirrors()

    def get_cached_mirrors_for_completion(self) -> List[Dict[str, Any]]:
        """Get cached mirror data specifically formatted for completion.

        Returns:
            List of mirror data formatted for autocompletion
        """
        mirrors = self.get_best_mirror_data()
        if not mirrors:
            return []

        # Normalize format for completion
        normalized = []
        for mirror in mirrors:
            if "name" in mirror:
                # Scanned mirrors or recent mirrors format
                normalized.append(
                    {
                        "name": mirror["name"],
                        "description": mirror.get("description", "Mirror repository"),
                        "upstream": mirror.get("upstream", ""),
                    }
                )
            elif "nameWithOwner" in mirror:
                # Repo completion cache format
                normalized.append(
                    {
                        "name": mirror["nameWithOwner"],
                        "description": mirror.get("description", "Mirror repository"),
                        "upstream": "",
                    }
                )

        return normalized

    def save_api_results_to_cache(self, repos_data: List[Dict[str, Any]]) -> None:
        """Save API results to appropriate cache.

        Args:
            repos_data: Repository data from GitHub API calls
        """
        if repos_data:
            self.config_manager.save_repo_completion_cache(repos_data)

    def invalidate_all_caches(self) -> None:
        """Invalidate all caches by removing cache files."""
        import os

        cache_files = [
            self.config_manager.scanned_mirrors_cache,
            self.config_manager.repo_completion_cache,
            self.config_manager.mirrors_cache,
        ]

        for cache_file in cache_files:
            try:
                if cache_file.exists():
                    os.remove(cache_file)
            except OSError:
                # Ignore removal errors
                pass
