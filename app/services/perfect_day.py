"""Pure perfect-day detection.

A "perfect day" is one where every scheduled, non-archived habit for that local
day has a check-in. It awards a one-time bonus (see ``gamification.XP_PERFECT_DAY``).
A day with no scheduled habits is not a perfect day.
"""

from __future__ import annotations

from collections.abc import Iterable


def is_perfect_day(scheduled_habit_ids: Iterable[int], checked_in_habit_ids: Iterable[int]) -> bool:
    scheduled = set(scheduled_habit_ids)
    if not scheduled:
        return False
    checked = set(checked_in_habit_ids)
    return scheduled <= checked
