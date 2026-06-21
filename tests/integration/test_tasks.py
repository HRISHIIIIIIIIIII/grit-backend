from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

# Import all models so metadata is complete.
import app.models  # noqa: F401
import pytest
from app.db.base import Base
from app.models.enums import HabitCategory, NotificationType
from app.models.habit import Habit, HabitCheckin
from app.models.notification import Notification
from app.models.streak import Streak
from app.models.user import User, UserSettings
from app.workers import tasks
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sync_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as session:
        yield session
    engine.dispose()


def _make_user(session: Session, tz: str = "Europe/Berlin") -> User:
    user = User(
        email="j@example.com",
        password_hash="x",
        display_name="Jordan",
        timezone=tz,
        settings=UserSettings(),
        streak=Streak(),
    )
    session.add(user)
    session.flush()
    return user


def _add_checkins(session: Session, user: User, days: list, tz_today) -> Habit:
    habit = Habit(user_id=user.id, name="Run", category=HabitCategory.FITNESS, xp_value=30)
    session.add(habit)
    session.flush()
    for d in days:
        session.add(HabitCheckin(habit_id=habit.id, user_id=user.id, local_date=d))
    session.flush()
    return habit


def test_streak_recompute_updates_cache(sync_session: Session) -> None:
    now = datetime(2026, 6, 21, 22, 5, tzinfo=UTC)  # Berlin 00:05 -> "today" = 22nd
    user = _make_user(sync_session)
    today = datetime(2026, 6, 22).date()
    days = [today - timedelta(days=i) for i in range(5)]  # 5-day run incl today
    _add_checkins(sync_session, user, days, today)

    tasks._run_streak_recompute(sync_session, user.id, now)
    sync_session.refresh(user.streak)
    assert user.streak.current_daily == 5


def test_streak_protection_notifies_when_today_open(sync_session: Session) -> None:
    now = datetime(2026, 6, 21, 18, 5, tzinfo=UTC)  # Berlin 20:05
    user = _make_user(sync_session)
    today = datetime(2026, 6, 21).date()
    # Active through yesterday only; today is still open.
    days = [today - timedelta(days=i) for i in range(1, 4)]
    _add_checkins(sync_session, user, days, today)
    # Seed the streak cache so current_daily > 0.
    user.streak.current_daily = 3
    sync_session.flush()

    tasks._run_streak_protection(sync_session, user.id, now)
    notes = sync_session.query(Notification).all()
    assert len(notes) == 1
    assert notes[0].type == NotificationType.STREAK_PROTECTION


def test_streak_protection_idempotent(sync_session: Session) -> None:
    now = datetime(2026, 6, 21, 18, 5, tzinfo=UTC)
    user = _make_user(sync_session)
    user.streak.current_daily = 3
    sync_session.flush()

    tasks._run_streak_protection(sync_session, user.id, now)
    tasks._run_streak_protection(sync_session, user.id, now)  # second call same day
    notes = sync_session.query(Notification).all()
    assert len(notes) == 1  # not double-sent


def test_protection_skipped_when_checked_in_today(sync_session: Session) -> None:
    now = datetime(2026, 6, 21, 18, 5, tzinfo=UTC)
    user = _make_user(sync_session)
    today = datetime(2026, 6, 21).date()
    _add_checkins(sync_session, user, [today], today)
    user.streak.current_daily = 1
    sync_session.flush()

    tasks._run_streak_protection(sync_session, user.id, now)
    assert sync_session.query(Notification).count() == 0


def test_sweep_enqueues_per_user(sync_session: Session) -> None:
    # Berlin user at 22:05 UTC -> local midnight -> streak_recompute enqueued.
    now = datetime(2026, 6, 21, 22, 5, tzinfo=UTC)
    _make_user(sync_session, tz="Europe/Berlin")

    calls: list[tuple[str, int]] = []
    plan = tasks._run_sweep(sync_session, now, lambda trigger, uid: calls.append((trigger, uid)))
    assert plan
    assert any(trigger == "streak_recompute" for trigger, _ in calls)


def test_weekly_review_notifies(sync_session: Session) -> None:
    now = datetime(2026, 6, 21, 16, 5, tzinfo=UTC)  # Berlin 18:05 Sunday
    user = _make_user(sync_session)
    today = datetime(2026, 6, 21).date()
    _add_checkins(sync_session, user, [today, today - timedelta(days=1)], today)

    tasks._run_review(sync_session, user.id, now, monthly=False)
    notes = sync_session.query(Notification).all()
    assert len(notes) == 1
    assert notes[0].type == NotificationType.REVIEW
