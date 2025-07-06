"""Integration tests for mirrorkeep workflow behavior."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


class TestMirrorkeepWorkflow:
    """Test mirrorkeep integration with workflow."""

    def test_backup_nonexistent_files(self):
        """Test backup behavior when patterns match no files."""
        # This tests the shell script logic that would run in GitHub Actions

        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create .mirrorkeep with non-existent patterns
            mirrorkeep_content = """
# Files that don't exist
non-existent.txt
missing-dir/
*.xyz
"""
            (root / ".mirrorkeep").write_text(mirrorkeep_content)

            # Simulate the find command used in workflow
            # find . -path "./pattern" -type f 2>/dev/null
            result = subprocess.run(
                ["find", str(root), "-path", f"{root}/non-existent.txt", "-type", "f"],
                capture_output=True,
                text=True,
            )

            # Should not find anything, but shouldn't error
            assert result.returncode == 0
            assert result.stdout.strip() == ""

    def test_restore_modified_files(self):
        """Test that modified files are preserved during sync."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backup_dir = root / "backup"
            backup_dir.mkdir()

            # Create original file
            (root / "README.md").write_text("Original content from upstream")

            # Simulate user modification
            (root / "README.md").write_text("My custom content")

            # Simulate backup process
            backup_file = backup_dir / "README.md"
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            backup_file.write_text((root / "README.md").read_text())

            # Simulate reset (would normally be git reset --hard)
            (root / "README.md").write_text("Original content from upstream")

            # Simulate restore
            (root / "README.md").write_text(backup_file.read_text())

            # Verify custom content is preserved
            assert (root / "README.md").read_text() == "My custom content"

    def test_pattern_matching_warnings(self):
        """Test that we can detect when patterns match no files."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create .mirrorkeep
            mirrorkeep_content = """
existing.txt
non-existent.txt
"""
            (root / ".mirrorkeep").write_text(mirrorkeep_content)
            (root / "existing.txt").write_text("content")

            # Track which patterns matched files
            patterns = ["existing.txt", "non-existent.txt"]
            matched_patterns = set()

            for pattern in patterns:
                result = subprocess.run(
                    ["find", str(root), "-name", pattern, "-type", "f"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    matched_patterns.add(pattern)

            # We can detect which patterns didn't match
            unmatched = set(patterns) - matched_patterns
            assert "non-existent.txt" in unmatched
            assert "existing.txt" not in unmatched

    def test_complex_directory_structure(self):
        """Test backup/restore with complex directory structures."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create complex structure
            (root / ".github").mkdir()
            (root / ".github" / "workflows").mkdir()
            (root / ".github" / "workflows" / "mirror-sync.yml").write_text("workflow")
            (root / ".github" / "workflows" / "custom-test.yml").write_text("custom")
            (root / ".docs").mkdir()
            (root / ".docs" / "guide.md").write_text("guide")

            # Patterns from .mirrorkeep
            patterns = [
                ".github/workflows/mirror-sync.yml",
                ".github/workflows/custom-*.yml",
                ".docs/",
            ]

            # Test that all expected files would be backed up
            expected_files = [
                ".github/workflows/mirror-sync.yml",
                ".github/workflows/custom-test.yml",
                ".docs/guide.md",
            ]

            found_files = []
            for pattern in patterns:
                if pattern.endswith("/"):
                    # Directory pattern
                    cmd = ["find", str(root), "-path", f"{root}/{pattern[:-1]}", "-type", "d"]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        # Find all files in directory
                        dir_path = Path(result.stdout.strip())
                        for f in dir_path.rglob("*"):
                            if f.is_file():
                                found_files.append(str(f.relative_to(root)))
                elif "*" in pattern:
                    # Wildcard pattern - simplified for test
                    parent = Path(pattern).parent
                    name_pattern = Path(pattern).name
                    search_dir = root / parent
                    if search_dir.exists():
                        for f in search_dir.glob(name_pattern):
                            if f.is_file():
                                found_files.append(str(f.relative_to(root)))
                else:
                    # Exact file
                    file_path = root / pattern
                    if file_path.exists() and file_path.is_file():
                        found_files.append(pattern)

            # Verify all expected files were found
            for expected in expected_files:
                assert any(expected in f for f in found_files), f"Expected {expected} not found"

    def test_recursive_directory_backup(self):
        """Test that directory patterns backup files recursively."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create deeply nested structure
            (root / ".docs").mkdir()
            (root / ".docs" / "level1").mkdir()
            (root / ".docs" / "level1" / "level2").mkdir()
            (root / ".docs" / "level1" / "level2" / "level3").mkdir()

            # Create files at each level
            (root / ".docs" / "root.md").write_text("root")
            (root / ".docs" / "level1" / "file1.md").write_text("level1")
            (root / ".docs" / "level1" / "level2" / "file2.md").write_text("level2")
            (root / ".docs" / "level1" / "level2" / "level3" / "file3.md").write_text("level3")

            # Test shell script that should backup all files recursively
            script = """
            pattern=".docs/"
            if [ "${pattern: -1}" = "/" ]; then
                dir_pattern="${pattern%/}"
                find . -path "./$dir_pattern" -type d 2>/dev/null | while read -r dir; do
                    find "$dir" -type f 2>/dev/null
                done
            fi
            """

            result = subprocess.run(
                ["bash", "-c", script], cwd=str(root), capture_output=True, text=True
            )

            # Should find all files at all levels
            assert ".docs/root.md" in result.stdout
            assert ".docs/level1/file1.md" in result.stdout
            assert ".docs/level1/level2/file2.md" in result.stdout
            assert ".docs/level1/level2/level3/file3.md" in result.stdout
