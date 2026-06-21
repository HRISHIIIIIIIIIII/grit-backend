"""Pure timezone-sweep boundary logic.

A single Celery Beat entry runs ``sweep`` every 15 minutes. For each user we
convert the UTC window to their LOCAL wall-clock time and check which trigger
boundaries fell inside the window:

- local ~00:00       -> STREAK_RECOMPUTE (evaluate "yesterday")
- local ~20:00       -> STREAK_PROTECTION (if today is still open)
- local Sun ~18:00   -> WEEKLY_REVIEW
- local 1st ~00:00   -> MONTHLY_REVIEW

These functions are pure (no DB, no Celery) so the fan-out is unit-testable.
"""

from __future__ import annotations

from datetime import datetime, time

from app.core.time import local_now

STREAK_RECOMPUTE = "streak_recompute"
STREAK_PROTECTION = "streak_protection"
WEEKLY_REVIEW = "weekly_review"
MONTHLY_REVIEW = "monthly_review"

_SUNDAY = 6


def due_triggers(prev_local: datetime, now_local: datetime) -> set[str]:
    """Which triggers fired in the local window ``(prev_local, now_local]``.

    Both arguments are naive local wall-clock datetimes.
    """
    triggers: set[str] = set()
    # A 15-min window spans at most two local dates.
    for day in {prev_local.date(), now_local.date()}:
        midnight = datetime.combine(day, time(0, 0))
        if prev_local < midnight <= now_local:
            triggers.add(STREAK_RECOMPUTE)
            if day.day == 1:
                triggers.add(MONTHLY_REVIEW)

        eight_pm = datetime.combine(day, time(20, 0))
        if prev_local < eight_pm <= now_local:
            triggers.add(STREAK_PROTECTION)

        if day.weekday() == _SUNDAY:
            six_pm = datetime.combine(day, time(18, 0))
            if prev_local < six_pm <= now_local:
                triggers.add(WEEKLY_REVIEW)

    return triggers


def plan_sweep(
    users_tz: list[tuple[int, str]], prev_utc: datetime, now_utc: datetime
) -> list[tuple[int, str]]:
    """Map each user to the per-user tasks that should be enqueued this window.

    ``users_tz`` is a list of (user_id, timezone). Returns (user_id, trigger) pairs.
    """
    plan: list[tuple[int, str]] = []
    for user_id, tz in users_tz:
        prev_local = local_now(tz, now=prev_utc).replace(tzinfo=None)
        now_local = local_now(tz, now=now_utc).replace(tzinfo=None)
        for trigger in sorted(due_triggers(prev_local, now_local)):
            plan.append((user_id, trigger))
    return plan
