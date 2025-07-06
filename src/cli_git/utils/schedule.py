"""Schedule generation utilities for mirror synchronization."""

import random


def generate_random_biweekly_schedule() -> str:
    """Generate random schedule for approximately bi-weekly execution.

    Returns two random days per month with random times.
    This helps distribute GitHub Actions load and avoid
    simultaneous executions across multiple mirrors.

    Returns:
        Cron expression for bi-weekly random schedule
    """
    # Select two days approximately 14 days apart
    day1 = random.randint(1, 14)
    day2 = random.randint(15, 28)

    # Generate random times for the schedule
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)

    # GitHub Actions cron format: minute hour day month weekday
    # Format: "30 14 7,21 * *" (runs on 7th and 21st at 14:30)
    return f"{minute} {hour} {day1},{day2} * *"


def describe_schedule(cron_expression: str) -> str:
    """Generate human-readable description of a cron schedule.

    Args:
        cron_expression: Cron expression to describe

    Returns:
        Human-readable description
    """
    try:
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return cron_expression

        minute, hour, day, month, weekday = parts

        # Handle bi-weekly schedule (two days per month)
        if "," in day and month == "*" and weekday == "*":
            days = day.split(",")
            if len(days) == 2:
                return f"매월 {days[0]}일, {days[1]}일 {hour}:{minute.zfill(2)} UTC"

        # Handle daily schedule (only when hour/minute are simple values)
        if day == "*" and month == "*" and weekday == "*" and not any(c in hour for c in "*/,-"):
            return f"매일 {hour}:{minute.zfill(2)} UTC"

        # Handle other patterns - return as-is
        return cron_expression

    except Exception:
        return cron_expression
