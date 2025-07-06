"""Tests for schedule generation utilities."""

import re
from unittest.mock import patch

from cli_git.utils.schedule import describe_schedule, generate_random_biweekly_schedule


class TestGenerateRandomBiweeklySchedule:
    """Test random bi-weekly schedule generation."""

    def test_generates_valid_cron_expression(self):
        """Test that generated schedule is a valid cron expression."""
        schedule = generate_random_biweekly_schedule()

        # Should have 5 fields
        parts = schedule.split()
        assert len(parts) == 5

        minute, hour, day, month, weekday = parts

        # Validate each field
        assert 0 <= int(minute) <= 59
        assert 0 <= int(hour) <= 23
        assert month == "*"
        assert weekday == "*"

        # Day should contain two comma-separated values
        assert "," in day
        days = day.split(",")
        assert len(days) == 2

        day1, day2 = map(int, days)
        assert 1 <= day1 <= 14
        assert 15 <= day2 <= 28

    def test_randomness(self):
        """Test that schedules are actually random."""
        # Generate multiple schedules
        schedules = [generate_random_biweekly_schedule() for _ in range(10)]

        # Should have some variety (not all identical)
        unique_schedules = set(schedules)
        assert len(unique_schedules) > 1

    @patch("random.randint")
    def test_deterministic_with_mock(self, mock_randint):
        """Test schedule generation with mocked random values."""
        # Mock specific random values
        mock_randint.side_effect = [
            7,  # day1
            21,  # day2
            14,  # hour
            30,  # minute
        ]

        schedule = generate_random_biweekly_schedule()
        assert schedule == "30 14 7,21 * *"

    def test_cron_format_compatibility(self):
        """Test that generated schedule is compatible with cron format."""
        schedule = generate_random_biweekly_schedule()

        # Basic cron regex pattern
        cron_pattern = r"^\d{1,2} \d{1,2} \d{1,2},\d{1,2} \* \*$"
        assert re.match(cron_pattern, schedule)


class TestDescribeSchedule:
    """Test schedule description generation."""

    def test_describe_biweekly_schedule(self):
        """Test description of bi-weekly schedule."""
        description = describe_schedule("30 14 7,21 * *")
        assert description == "매월 7일, 21일 14:30 UTC"

    def test_describe_daily_schedule(self):
        """Test description of daily schedule."""
        description = describe_schedule("0 0 * * *")
        assert description == "매일 0:00 UTC"

    def test_describe_with_single_digit_minute(self):
        """Test description with single-digit minute."""
        description = describe_schedule("5 14 7,21 * *")
        assert description == "매월 7일, 21일 14:05 UTC"

    def test_describe_invalid_schedule(self):
        """Test description of invalid schedule."""
        # Returns original if can't parse
        assert describe_schedule("invalid") == "invalid"
        assert describe_schedule("* * *") == "* * *"
        assert describe_schedule("") == ""

    def test_describe_complex_schedule(self):
        """Test description of complex schedule patterns."""
        # Complex patterns return as-is
        assert describe_schedule("0 */6 * * *") == "0 */6 * * *"
        assert describe_schedule("0 0 * * 1-5") == "0 0 * * 1-5"

    def test_describe_with_whitespace(self):
        """Test description with extra whitespace."""
        description = describe_schedule("  30   14   7,21   *   *  ")
        assert description == "매월 7일, 21일 14:30 UTC"

    def test_describe_handles_exceptions(self):
        """Test that describe_schedule handles exceptions gracefully."""
        # Should not raise, just return original
        assert describe_schedule(None) == None  # noqa: E711
        assert describe_schedule(123) == 123  # noqa: E501
