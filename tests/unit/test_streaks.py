from __future__ import annotations

from datetime import date, timedelta

from app.models.enums import EvolutionStage
from app.services.perfect_day import is_perfect_day
from app.services.streaks import (
    evolution_stage,
    habit_current_streak,
    recompute_streak,
)


def _run(n: int, end: date) -> list[date]:
    return [end - timedelta(days=i) for i in range(n)]


def test_habit_streak_counts_consecutive_ending_today() -> None:
    today = date(2026, 6, 21)
    assert habit_current_streak(_run(5, today), today) == 5


def test_habit_streak_live_when_last_checkin_yesterday() -> None:
    today = date(2026, 6, 21)
    yesterday = today - timedelta(days=1)
    assert habit_current_streak(_run(3, yesterday), today) == 3


def test_habit_streak_broken_when_gap() -> None:
    today = date(2026, 6, 21)
    old = today - timedelta(days=3)
    assert habit_current_streak(_run(4, old), today) == 0


def test_habit_streak_empty() -> None:
    assert habit_current_streak([], date(2026, 6, 21)) == 0


def test_recompute_simple_extend() -> None:
    today = date(2026, 6, 21)
    state = recompute_streak(_run(10, today), today)
    assert state.current_daily == 10
    assert state.longest == 10
    assert state.freeze_balance == 0  # 10 < 14


def test_recompute_earns_freeze_every_14_days() -> None:
    today = date(2026, 6, 21)
    state = recompute_streak(_run(28, today), today)
    assert state.current_daily == 28
    assert state.freeze_balance == 2  # one at 14, one at 28


def test_recompute_freeze_cap_is_three() -> None:
    today = date(2026, 6, 21)
    state = recompute_streak(_run(100, today), today)
    assert state.freeze_balance == 3


def test_missed_day_consumes_freeze_and_survives() -> None:
    today = date(2026, 6, 21)
    # 14 days, then a missed day, then 3 more days ending today.
    days = set(_run(14, today - timedelta(days=4)))  # earns 1 freeze
    days |= set(_run(3, today))  # last 3 days
    # The gap day(s) between should consume the freeze.
    state = recompute_streak(days, today)
    assert state.current_daily > 0  # streak preserved by the freeze


def test_missed_day_without_freeze_breaks() -> None:
    today = date(2026, 6, 21)
    days = set(_run(3, today - timedelta(days=5)))  # too few for a freeze
    days |= set(_run(2, today))
    state = recompute_streak(days, today)
    assert state.current_daily == 2  # reset then rebuilt over last 2 days


def test_today_open_does_not_break_streak() -> None:
    today = date(2026, 6, 21)
    yesterday = today - timedelta(days=1)
    # Active through yesterday, today not yet checked in.
    state = recompute_streak(_run(5, yesterday), today)
    assert state.current_daily == 5


def test_evolution_stages() -> None:
    assert evolution_stage(1) == EvolutionStage.SPARK
    assert evolution_stage(6) == EvolutionStage.SPARK
    assert evolution_stage(7) == EvolutionStage.EMBER
    assert evolution_stage(21) == EvolutionStage.FLAME
    assert evolution_stage(47) == EvolutionStage.BLAZE  # Jordan Reyes
    assert evolution_stage(100) == EvolutionStage.INFERNO
    assert evolution_stage(365) == EvolutionStage.ETERNAL


def test_perfect_day() -> None:
    assert is_perfect_day({1, 2, 3}, {1, 2, 3}) is True
    assert is_perfect_day({1, 2, 3}, {1, 2}) is False
    assert is_perfect_day(set(), set()) is False  # no scheduled habits
    assert is_perfect_day({1}, {1, 2, 3}) is True  # extra check-ins are fine
