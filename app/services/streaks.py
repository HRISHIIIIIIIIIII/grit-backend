"""Pure streak math — no database access.

The single source of truth for streaks is the user's check-in history. Given the
set of *active days* (local dates on which the user completed at least one habit)
these functions derive the current/longest daily streak, the freeze balance, and
the evolution stage. The DB-backed ``Streak`` row is just a cache of this.

Rules (per spec):
- Earn +1 freeze per 14 consecutive active days (cap 3).
- A missed day auto-consumes a freeze if one is available (streak survives), else
  the streak breaks.
- "Today" is treated as still open: if today has no check-in yet it neither breaks
  the streak nor consumes a freeze.
- Evolution stage by current length: Spark 1-6, Ember 7-20, Flame 21-45,
  Blaze 46-99, Inferno 100-364, Eternal 365+.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from app.models.enums import EvolutionStage

FREEZE_CAP = 3
FREEZE_EVERY = 14


@dataclass(frozen=True)
class StreakState:
    current_daily: int
    longest: int
    freeze_balance: int
    weekly_count: int
    monthly_count: int


def habit_current_streak(checkin_dates: Iterable[date], today: date) -> int:
    """Consecutive-day streak for a single habit, ending today or yesterday.

    A streak is "live" if the most recent check-in is today or yesterday; older
    gaps reset it to 0.
    """
    days = set(checkin_dates)
    if not days:
        return 0
    # Anchor at today if checked in today, else yesterday (today still open).
    if today in days:
        cursor = today
    elif (today - timedelta(days=1)) in days:
        cursor = today - timedelta(days=1)
    else:
        return 0
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def recompute_streak(active_dates: Iterable[date], today: date) -> StreakState:
    """Derive the full user streak state from active days up to ``today``."""
    days = set(active_dates)
    if not days:
        return StreakState(0, 0, 0, 0, 0)

    start = min(days)
    current = 0
    longest = 0
    freezes = 0
    toward_freeze = 0

    day = start
    one = timedelta(days=1)
    while day <= today:
        if day in days:
            current += 1
            toward_freeze += 1
            longest = max(longest, current)
            if toward_freeze == FREEZE_EVERY:
                freezes = min(FREEZE_CAP, freezes + 1)
                toward_freeze = 0
        elif day == today:
            # Today is still open — don't break or consume a freeze yet.
            pass
        elif current > 0 and freezes > 0:
            # Bridge a single missed day with a freeze; streak survives.
            freezes -= 1
        else:
            current = 0
            toward_freeze = 0
        day += one

    weekly_count = _count_in_iso_week(days, today)
    monthly_count = _count_in_month(days, today)
    return StreakState(
        current_daily=current,
        longest=longest,
        freeze_balance=freezes,
        weekly_count=weekly_count,
        monthly_count=monthly_count,
    )


def evolution_stage(current_daily: int) -> EvolutionStage:
    n = current_daily
    if n >= 365:
        return EvolutionStage.ETERNAL
    if n >= 100:
        return EvolutionStage.INFERNO
    if n >= 46:
        return EvolutionStage.BLAZE
    if n >= 21:
        return EvolutionStage.FLAME
    if n >= 7:
        return EvolutionStage.EMBER
    return EvolutionStage.SPARK


def _count_in_iso_week(days: set[date], today: date) -> int:
    year, week, _ = today.isocalendar()
    return sum(1 for d in days if d.isocalendar()[:2] == (year, week))


def _count_in_month(days: set[date], today: date) -> int:
    return sum(1 for d in days if (d.year, d.month) == (today.year, today.month))
