"""Pure schedule comparison; intervals are half open [start, end)."""

from datetime import time


def minutes(value: str) -> int:
    parsed = time.fromisoformat(value)
    return parsed.hour * 60 + parsed.minute


def find_schedule_conflicts(
    candidate: list[dict], existing: list[dict], min_break_minutes: int = 0
) -> list[dict]:
    """Return existing offerings with at least one conflicting meeting."""
    return [
        item
        for item in existing
        if any(
            a["day"] == b["day"]
            and minutes(a["start"]) < minutes(b["end"]) + min_break_minutes
            and minutes(b["start"]) < minutes(a["end"]) + min_break_minutes
            for a in candidate
            for b in item["schedule"]
        )
    ]
