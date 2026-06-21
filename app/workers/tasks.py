"""Celery tasks (run SYNC, with their own sync session).

The sweep only ENQUEUES per-user tasks (fan-out, no heavy work). Each per-user
task is idempotent: it guards on a once-per-local-day notification marker so
overlapping windows or retries never double-send. The heavy logic lives in plain
``_run_*`` functions that take a session, so they're unit-testable without a broker.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.time import local_date, start_of_local_day_utc, utcnow
from app.db.sync_session import sync_session_scope
from app.models.enums import MentorTone, NotificationType
from app.models.habit import HabitCheckin
from app.models.notification import Notification
from app.models.streak import Streak
from app.models.user import User, UserSettings
from app.services import mentor
from app.services.notifications import in_quiet_hours, is_type_enabled
from app.services.streaks import recompute_streak
from app.workers.celery_app import celery_app
from app.workers.schedules import (
    MONTHLY_REVIEW,
    STREAK_PROTECTION,
    STREAK_RECOMPUTE,
    WEEKLY_REVIEW,
    plan_sweep,
)

SWEEP_WINDOW = timedelta(minutes=15)


# --- sync query helpers ---------------------------------------------------


def _user_with_settings(session: Session, user_id: int) -> tuple[User, UserSettings | None] | None:
    user = session.get(User, user_id)
    if user is None:
        return None
    settings = session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    ).scalar_one_or_none()
    return user, settings


def _active_dates(session: Session, user_id: int) -> set[date]:
    rows = session.execute(
        select(HabitCheckin.local_date).where(HabitCheckin.user_id == user_id).distinct()
    ).scalars()
    return set(rows)


def _checked_in_today(session: Session, user_id: int, today: date) -> bool:
    count = session.execute(
        select(func.count()).where(
            HabitCheckin.user_id == user_id, HabitCheckin.local_date == today
        )
    ).scalar_one()
    return int(count) > 0


def _already_notified_today(
    session: Session, user_id: int, ntype: NotificationType, today: date, tz: str
) -> bool:
    start = start_of_local_day_utc(tz, today)
    end = start_of_local_day_utc(tz, today + timedelta(days=1))
    row = session.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.type == ntype,
            Notification.created_at >= start,
            Notification.created_at < end,
        )
    ).first()
    return row is not None


def _emit(
    session: Session,
    user: User,
    settings: UserSettings | None,
    *,
    ntype: NotificationType,
    event: str,
    now: datetime,
    **context: object,
) -> Notification | None:
    """Create a notification in a sync session, honouring toggles + quiet hours."""
    if not is_type_enabled(settings, ntype):
        return None
    tone = settings.mentor_tone if settings else MentorTone.HARD
    message = mentor.generate_mentor_message(
        event, tone or MentorTone.HARD, name=user.display_name, **context
    )
    notification = Notification(
        user_id=user.id,
        type=ntype,
        title=message.title,
        body=message.body,
    )
    local_t = now  # already UTC; quiet-hours check uses local time below
    from app.core.time import local_now

    local_time = local_now(user.timezone, now=local_t).timetz().replace(tzinfo=None)
    if settings is not None and in_quiet_hours(settings, local_time):
        notification.scheduled_for = None
        notification.sent_at = None
    else:
        notification.scheduled_for = now
        notification.sent_at = now
    session.add(notification)
    session.flush()
    return notification


# --- per-user logic (testable) -------------------------------------------


def _run_streak_recompute(session: Session, user_id: int, now: datetime) -> None:
    found = _user_with_settings(session, user_id)
    if found is None:
        return
    user, settings = found
    today = local_date(user.timezone, now=now)
    yesterday = today - timedelta(days=1)

    active = _active_dates(session, user_id)
    state = recompute_streak(active, today)

    streak = session.execute(select(Streak).where(Streak.user_id == user_id)).scalar_one_or_none()
    if streak is None:
        streak = Streak(user_id=user_id)
        session.add(streak)
    streak.current_daily = state.current_daily
    streak.longest = max(streak.longest, state.longest)
    streak.weekly_count = state.weekly_count
    streak.monthly_count = state.monthly_count
    streak.freeze_balance = state.freeze_balance
    session.flush()

    # If yesterday was missed (not active), nudge with an accountability message.
    if yesterday not in active and not _already_notified_today(
        session, user_id, NotificationType.ACCOUNTABILITY, today, user.timezone
    ):
        _emit(
            session,
            user,
            settings,
            ntype=NotificationType.ACCOUNTABILITY,
            event=mentor.EVENT_ACCOUNTABILITY,
            now=now,
        )


def _run_streak_protection(session: Session, user_id: int, now: datetime) -> None:
    found = _user_with_settings(session, user_id)
    if found is None:
        return
    user, settings = found
    today = local_date(user.timezone, now=now)
    if _checked_in_today(session, user_id, today):
        return  # day already secured

    streak = session.execute(select(Streak).where(Streak.user_id == user_id)).scalar_one_or_none()
    current = streak.current_daily if streak else 0
    if current <= 0:
        return
    if _already_notified_today(
        session, user_id, NotificationType.STREAK_PROTECTION, today, user.timezone
    ):
        return
    _emit(
        session,
        user,
        settings,
        ntype=NotificationType.STREAK_PROTECTION,
        event=mentor.EVENT_STREAK_PROTECTION,
        now=now,
        streak=current,
    )


def _weekly_checkins(session: Session, user_id: int, today: date) -> int:
    start = today - timedelta(days=today.weekday())
    count = session.execute(
        select(func.count()).where(
            HabitCheckin.user_id == user_id,
            HabitCheckin.local_date >= start,
            HabitCheckin.local_date <= today,
        )
    ).scalar_one()
    return int(count)


def _monthly_checkins(session: Session, user_id: int, today: date) -> int:
    start = today.replace(day=1)
    count = session.execute(
        select(func.count()).where(
            HabitCheckin.user_id == user_id,
            HabitCheckin.local_date >= start,
            HabitCheckin.local_date <= today,
        )
    ).scalar_one()
    return int(count)


def _run_review(session: Session, user_id: int, now: datetime, *, monthly: bool) -> None:
    found = _user_with_settings(session, user_id)
    if found is None:
        return
    user, settings = found
    today = local_date(user.timezone, now=now)
    if _already_notified_today(session, user_id, NotificationType.REVIEW, today, user.timezone):
        return
    if monthly:
        checkins = _monthly_checkins(session, user_id, today)
        event = mentor.EVENT_REVIEW_MONTHLY
    else:
        checkins = _weekly_checkins(session, user_id, today)
        event = mentor.EVENT_REVIEW_WEEKLY
    _emit(
        session,
        user,
        settings,
        ntype=NotificationType.REVIEW,
        event=event,
        now=now,
        checkins=checkins,
    )


# --- sweep planning (testable) -------------------------------------------


def _run_sweep(
    session: Session, now: datetime, enqueue: Callable[[str, int], None]
) -> list[tuple[int, str]]:
    prev = now - SWEEP_WINDOW
    users_tz = [(row[0], row[1]) for row in session.execute(select(User.id, User.timezone)).all()]
    plan = plan_sweep(users_tz, prev, now)
    for user_id, trigger in plan:
        enqueue(trigger, user_id)
    return plan


_TASK_NAMES: dict[str, str] = {
    STREAK_RECOMPUTE: "app.workers.tasks.streak_recompute",
    STREAK_PROTECTION: "app.workers.tasks.streak_protection_check",
    WEEKLY_REVIEW: "app.workers.tasks.weekly_review",
    MONTHLY_REVIEW: "app.workers.tasks.monthly_review",
}


# --- Celery task wrappers -------------------------------------------------


@celery_app.task(name="app.workers.tasks.sweep")
def sweep() -> int:
    now = utcnow()

    def enqueue(trigger: str, user_id: int) -> None:
        celery_app.send_task(_TASK_NAMES[trigger], args=[user_id])

    with sync_session_scope() as session:
        plan = _run_sweep(session, now, enqueue)
    return len(plan)


@celery_app.task(name="app.workers.tasks.streak_recompute")
def streak_recompute(user_id: int) -> None:
    with sync_session_scope() as session:
        _run_streak_recompute(session, user_id, utcnow())


@celery_app.task(name="app.workers.tasks.streak_protection_check")
def streak_protection_check(user_id: int) -> None:
    with sync_session_scope() as session:
        _run_streak_protection(session, user_id, utcnow())


@celery_app.task(name="app.workers.tasks.weekly_review")
def weekly_review(user_id: int) -> None:
    with sync_session_scope() as session:
        _run_review(session, user_id, utcnow(), monthly=False)


@celery_app.task(name="app.workers.tasks.monthly_review")
def monthly_review(user_id: int) -> None:
    with sync_session_scope() as session:
        _run_review(session, user_id, utcnow(), monthly=True)
