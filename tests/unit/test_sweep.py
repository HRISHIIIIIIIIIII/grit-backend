from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.workers.schedules import (
    MONTHLY_REVIEW,
    STREAK_PROTECTION,
    STREAK_RECOMPUTE,
    WEEKLY_REVIEW,
    due_triggers,
    plan_sweep,
)


def _window(y: int, mo: int, d: int, h: int, mi: int) -> tuple[datetime, datetime]:
    now = datetime(y, mo, d, h, mi)
    return now - timedelta(minutes=15), now


def test_midnight_triggers_streak_recompute() -> None:
    prev, now = _window(2026, 6, 21, 0, 5)  # crosses 00:00
    assert STREAK_RECOMPUTE in due_triggers(prev, now)


def test_eight_pm_triggers_protection() -> None:
    prev, now = _window(2026, 6, 21, 20, 5)
    triggers = due_triggers(prev, now)
    assert STREAK_PROTECTION in triggers
    assert STREAK_RECOMPUTE not in triggers


def test_first_of_month_midnight_adds_monthly_review() -> None:
    prev, now = _window(2026, 7, 1, 0, 5)
    triggers = due_triggers(prev, now)
    assert STREAK_RECOMPUTE in triggers
    assert MONTHLY_REVIEW in triggers


def test_sunday_six_pm_triggers_weekly_review() -> None:
    # 2026-06-21 is a Sunday.
    assert datetime(2026, 6, 21).weekday() == 6
    prev, now = _window(2026, 6, 21, 18, 5)
    assert WEEKLY_REVIEW in due_triggers(prev, now)


def test_non_sunday_six_pm_no_weekly_review() -> None:
    # 2026-06-22 is a Monday.
    prev, now = _window(2026, 6, 22, 18, 5)
    assert WEEKLY_REVIEW not in due_triggers(prev, now)


def test_quiet_window_no_boundary_returns_empty() -> None:
    prev, now = _window(2026, 6, 21, 10, 5)
    assert due_triggers(prev, now) == set()


def test_plan_sweep_fans_out_per_timezone() -> None:
    # At 22:05 UTC: Berlin (UTC+2 summer) local is 00:05 -> midnight crossed.
    # New York (UTC-4 summer) local is 18:05 -> on a Sunday, weekly review.
    now = datetime(2026, 6, 21, 22, 5, tzinfo=UTC)
    prev = now - timedelta(minutes=15)
    users = [(1, "Europe/Berlin"), (2, "America/New_York")]
    plan = plan_sweep(users, prev, now)

    berlin = {t for uid, t in plan if uid == 1}
    ny = {t for uid, t in plan if uid == 2}
    assert STREAK_RECOMPUTE in berlin
    assert WEEKLY_REVIEW in ny
    assert STREAK_RECOMPUTE not in ny
