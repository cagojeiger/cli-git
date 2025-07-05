"""Tests for mirrorkeep file parsing and pattern matching."""

from pathlib import Path
from tempfile import TemporaryDirectory

from cli_git.core.mirrorkeep import (
    create_default_mirrorkeep,
    get_files_to_preserve,
    match_pattern,
    parse_mirrorkeep,
)


class TestMirrorkeepParser:
    """Test mirrorkeep file parsing functionality."""

    def test_parse_simple_patterns(self):
        """Test parsing simple file and directory patterns."""
        content = """
CLAUDE.md
.docs/
.vscode/settings.json
"""
        patterns = parse_mirrorkeep(content)
        assert patterns == ["CLAUDE.md", ".docs/", ".vscode/settings.json"]

    def test_parse_with_comments(self):
        """Test parsing with comments and empty lines."""
        content = """
# This is a comment
CLAUDE.md

# Another comment
.docs/
  # Indented comment
.vscode/

"""
        patterns = parse_mirrorkeep(content)
        assert patterns == ["CLAUDE.md", ".docs/", ".vscode/"]

    def test_parse_wildcards(self):
        """Test parsing wildcard patterns."""
        content = """
*.md
.github/workflows/custom-*.yml
.local/**
docs/**/*.pdf
"""
        patterns = parse_mirrorkeep(content)
        assert patterns == [
            "*.md",
            ".github/workflows/custom-*.yml",
            ".local/**",
            "docs/**/*.pdf",
        ]

    def test_parse_exclusions(self):
        """Test parsing exclusion patterns with ! prefix."""
        content = """
.docs/
!.docs/temp/
*.log
!debug.log
"""
        patterns = parse_mirrorkeep(content)
        # All patterns including exclusions
        assert patterns == [".docs/", "!.docs/temp/", "*.log", "!debug.log"]

    def test_parse_empty_file(self):
        """Test parsing empty content."""
        content = ""
        patterns = parse_mirrorkeep(content)
        assert patterns == []

    def test_parse_only_comments(self):
        """Test parsing file with only comments."""
        content = """
# Just comments
# Nothing else
"""
        patterns = parse_mirrorkeep(content)
        assert patterns == []


class TestPatternMatching:
    """Test file pattern matching functionality."""

    def test_match_exact_file(self):
        """Test matching exact file names."""
        assert match_pattern("CLAUDE.md", ["CLAUDE.md"]) is True
        assert match_pattern("README.md", ["CLAUDE.md"]) is False

    def test_match_directory(self):
        """Test matching directory patterns."""
        assert match_pattern(".docs/README.md", [".docs/"]) is True
        assert match_pattern(".docs/guide/intro.md", [".docs/"]) is True
        assert match_pattern("docs/README.md", [".docs/"]) is False

    def test_match_wildcards(self):
        """Test matching wildcard patterns."""
        # Single asterisk
        assert match_pattern("README.md", ["*.md"]) is True
        assert match_pattern("docs/guide.md", ["*.md"]) is False  # * doesn't match /

        # Double asterisk
        assert match_pattern("docs/guide.md", ["**/*.md"]) is True
        assert match_pattern("docs/api/reference.md", ["**/*.md"]) is True

        # Custom patterns
        assert (
            match_pattern(".github/workflows/custom-deploy.yml", [".github/workflows/custom-*.yml"])
            is True
        )
        assert (
            match_pattern(".github/workflows/test.yml", [".github/workflows/custom-*.yml"]) is False
        )

    def test_match_with_exclusions(self):
        """Test matching with exclusion patterns."""
        patterns = ["*.md", "!README.md", ".docs/", "!.docs/temp/"]

        # Included files
        assert match_pattern("CLAUDE.md", patterns) is True
        assert match_pattern(".docs/guide.md", patterns) is True

        # Excluded files
        assert match_pattern("README.md", patterns) is False
        assert match_pattern(".docs/temp/draft.md", patterns) is False

    def test_match_priority(self):
        """Test that exclusions take priority over inclusions."""
        patterns = ["*.log", "!error.log", "logs/", "!logs/debug/"]

        assert match_pattern("app.log", patterns) is True
        assert match_pattern("error.log", patterns) is False
        assert match_pattern("logs/app.log", patterns) is True
        assert match_pattern("logs/debug/trace.log", patterns) is False


class TestFilePreservation:
    """Test file preservation logic."""

    def test_get_files_to_preserve(self):
        """Test getting list of files to preserve."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create test files
            (root / "CLAUDE.md").write_text("# Claude")
            (root / "README.md").write_text("# Readme")
            (root / ".docs").mkdir()
            (root / ".docs" / "guide.md").write_text("# Guide")
            (root / ".docs" / "temp").mkdir()
            (root / ".docs" / "temp" / "draft.md").write_text("# Draft")
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('hello')")

            # Test with patterns
            patterns = ["CLAUDE.md", ".docs/", "!.docs/temp/"]
            files = get_files_to_preserve(root, patterns)

            # Convert to relative paths for easier testing
            relative_files = sorted([f.relative_to(root) for f in files])

            assert Path("CLAUDE.md") in relative_files
            assert Path(".docs/guide.md") in relative_files
            assert Path(".docs/temp/draft.md") not in relative_files
            assert Path("README.md") not in relative_files
            assert Path("src/main.py") not in relative_files

    def test_get_files_with_wildcards(self):
        """Test file preservation with wildcard patterns."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create test files
            (root / "README.md").write_text("# Readme")
            (root / "CLAUDE.md").write_text("# Claude")
            (root / "docs").mkdir()
            (root / "docs" / "guide.md").write_text("# Guide")
            (root / "test.py").write_text("print('test')")

            # Test with wildcard patterns
            patterns = ["*.md", "!README.md"]
            files = get_files_to_preserve(root, patterns)

            relative_files = sorted([f.relative_to(root) for f in files])

            assert Path("CLAUDE.md") in relative_files
            assert Path("README.md") not in relative_files
            assert Path("docs/guide.md") not in relative_files  # *.md doesn't match subdirs
            assert Path("test.py") not in relative_files


class TestDefaultMirrorkeep:
    """Test default .mirrorkeep content generation."""

    def test_create_default_mirrorkeep(self):
        """Test creating default .mirrorkeep content."""
        content = create_default_mirrorkeep()

        # Should contain essential patterns
        assert ".github/workflows/mirror-sync.yml" in content
        assert ".mirrorkeep" in content

        # Should contain helpful comments
        assert "#" in content
        assert "mirror" in content.lower()

        # Should be parseable
        patterns = parse_mirrorkeep(content)
        assert ".github/workflows/mirror-sync.yml" in patterns
        assert ".mirrorkeep" in patterns
