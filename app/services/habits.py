"""Habit + check-in business logic.

Check-ins are idempotent per local day (DB unique constraint + an explicit guard
that returns a clean conflict error). A check-in awards the habit's ``xp_value``,
re-syncs the user's streak, and may award the perfect-day bonus.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.time import local_date
from app.models.enums import CheckinSource, XpReason
from app.models.habit import Habit, HabitCheckin
from app.models.user import User
from app.repositories import habit as habit_repo
from app.schemas.habit import HabitCreate, HabitUpdate
from app.services import scoring
from app.services.streaks import habit_current_streak


async def _require_habit(session: AsyncSession, habit_id: int, user: User) -> Habit:
    habit = await habit_repo.get_owned(session, habit_id, user.id)
    if habit is None:
        raise NotFoundError("Habit not found")
    return habit


async def create_habit(session: AsyncSession, user: User, payload: HabitCreate) -> Habit:
    habit = Habit(
        user_id=user.id,
        name=payload.name,
        category=payload.category,
        icon=payload.icon,
        xp_value=payload.xp_value,
        schedule=payload.schedule,
        linked_roadmap_id=payload.linked_roadmap_id,
    )
    session.add(habit)
    await session.flush()
    return habit


async def update_habit(
    session: AsyncSession, user: User, habit_id: int, payload: HabitUpdate
) -> Habit:
    habit = await _require_habit(session, habit_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    await session.flush()
    return habit


async def delete_habit(session: AsyncSession, user: User, habit_id: int) -> None:
    habit = await _require_habit(session, habit_id, user)
    await session.delete(habit)
    await session.flush()


async def set_archived(
    session: AsyncSession, user: User, habit_id: int, archived: bool
) -> Habit:
    habit = await _require_habit(session, habit_id, user)
    habit.archived = archived
    await session.flush()
    return habit


async def list_habits(
    session: AsyncSession, user: User, *, include_archived: bool
) -> list[tuple[Habit, int, bool]]:
    """Return (habit, current_streak, checked_in_today) for each habit."""
    habits = await habit_repo.list_for_user(session, user.id, include_archived=include_archived)
    today = local_date(user.timezone)
    result: list[tuple[Habit, int, bool]] = []
    for habit in habits:
        dates = await habit_repo.checkin_dates_for_habit(session, habit.id)
        streak = habit_current_streak(dates, today)
        result.append((habit, streak, today in set(dates)))
    return result


async def check_in(
    session: AsyncSession,
    user: User,
    habit_id: int,
    *,
    source: CheckinSource = CheckinSource.MANUAL,
) -> tuple[HabitCheckin, int, bool, int]:
    """Idempotently check in a habit for the user's current local day.

    Returns (checkin, xp_awarded, perfect_day, current_streak).
    """
    habit = await _require_habit(session, habit_id, user)
    today = local_date(user.timezone)

    existing = await habit_repo.checkin_for_day(session, habit.id, today)
    if existing is not None:
        raise ConflictError(
            "Habit already checked in for today", code="already_checked_in"
        )

    checkin = HabitCheckin(
        habit_id=habit.id, user_id=user.id, local_date=today, source=source
    )
    session.add(checkin)
    await session.flush()

    await scoring.award_xp(
        session, user, amount=habit.xp_value, reason=XpReason.HABIT, ref_id=checkin.id
    )
    perfect = await scoring.maybe_award_perfect_day(session, user, today)
    await scoring.sync_user_streak(session, user, today)

    dates = await habit_repo.checkin_dates_for_habit(session, habit.id)
    streak = habit_current_streak(dates, today)
    return checkin, habit.xp_value, perfect is not None, streak


async def undo_check_in(session: AsyncSession, user: User, habit_id: int) -> None:
    """Remove today's check-in and refund the XP it granted."""
    habit = await _require_habit(session, habit_id, user)
    today = local_date(user.timezone)

    checkin = await habit_repo.checkin_for_day(session, habit.id, today)
    if checkin is None:
        raise NotFoundError("No check-in to undo for today", code="no_checkin_today")

    checkin_id = checkin.id
    await session.delete(checkin)
    await session.flush()

    await scoring.revoke_xp_by_ref(session, user, reason=XpReason.HABIT, ref_id=checkin_id)
    await scoring.reverse_perfect_day_if_broken(session, user, today)
    await scoring.sync_user_streak(session, user, today)
