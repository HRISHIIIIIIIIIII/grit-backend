"""DB-backed scoring orchestration: XP ledger, streak cache, perfect-day bonus.

Pure math lives in ``gamification``, ``streaks`` and ``perfect_day``; this module
applies it against the database. It is the single place that mutates
``User.xp_total``, the ``XpEvent`` ledger and the ``Streak`` cache so habits,
roadmaps and goals all award XP consistently.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.streak import Streak
from app.models.user import User
from app.models.xp import XpEvent
from app.repositories import habit as habit_repo
from app.services import perfect_day as perfect_day_service
from app.services import streaks as streak_math
from app.services.gamification import XP_PERFECT_DAY
from app.services.habit_schedule import is_scheduled_on


async def award_xp(
    session: AsyncSession,
    user: User,
    *,
    amount: int,
    reason: XpReason,
    ref_id: int | None = None,
) -> XpEvent:
    """Append an XP event and keep ``user.xp_total`` in sync (integer math)."""
    event = XpEvent(user_id=user.id, amount=amount, reason=reason, ref_id=ref_id)
    session.add(event)
    user.xp_total = max(0, user.xp_total + amount)
    await session.flush()
    return event


async def revoke_xp_by_ref(
    session: AsyncSession, user: User, *, reason: XpReason, ref_id: int
) -> int:
    """Delete XP events matching (reason, ref_id) and refund ``xp_total``.

    Returns the total XP removed. Used when a check-in / topic / milestone is undone.
    """
    stmt = select(XpEvent).where(
        XpEvent.user_id == user.id, XpEvent.reason == reason, XpEvent.ref_id == ref_id
    )
    events = list((await session.execute(stmt)).scalars().all())
    removed = 0
    for event in events:
        removed += event.amount
        await session.delete(event)
    if removed:
        user.xp_total = max(0, user.xp_total - removed)
        await session.flush()
    return removed


async def reverse_perfect_day_if_broken(
    session: AsyncSession, user: User, day: date
) -> None:
    """Remove a previously awarded perfect-day bonus if the day is no longer perfect."""
    if not await _perfect_day_already_awarded(session, user.id, day):
        return
    scheduled = await scheduled_habit_ids(session, user.id, day)
    checked = await habit_repo.checked_in_habit_ids(session, user.id, day)
    if not perfect_day_service.is_perfect_day(scheduled, checked):
        await revoke_xp_by_ref(
            session, user, reason=XpReason.PERFECT_DAY, ref_id=day.toordinal()
        )


async def _get_or_create_streak(session: AsyncSession, user: User) -> Streak:
    streak = (
        await session.execute(select(Streak).where(Streak.user_id == user.id))
    ).scalar_one_or_none()
    if streak is None:
        streak = Streak(user_id=user.id)
        session.add(streak)
        await session.flush()
    return streak


async def sync_user_streak(session: AsyncSession, user: User, today: date) -> Streak:
    """Recompute the user's streak from check-in history and persist the cache."""
    active = await habit_repo.active_dates_for_user(session, user.id)
    state = streak_math.recompute_streak(active, today)
    streak = await _get_or_create_streak(session, user)
    streak.current_daily = state.current_daily
    streak.longest = max(streak.longest, state.longest)
    streak.weekly_count = state.weekly_count
    streak.monthly_count = state.monthly_count
    streak.freeze_balance = state.freeze_balance
    await session.flush()
    return streak


async def scheduled_habit_ids(session: AsyncSession, user_id: int, day: date) -> set[int]:
    habits = await habit_repo.active_habits(session, user_id)
    return {h.id for h in habits if is_scheduled_on(h.schedule, day)}


async def _perfect_day_already_awarded(
    session: AsyncSession, user_id: int, day: date
) -> bool:
    stmt = select(XpEvent.id).where(
        XpEvent.user_id == user_id,
        XpEvent.reason == XpReason.PERFECT_DAY,
        XpEvent.ref_id == day.toordinal(),
    )
    return (await session.execute(stmt)).first() is not None


async def maybe_award_perfect_day(
    session: AsyncSession, user: User, day: date
) -> XpEvent | None:
    """Award the perfect-day bonus once if all scheduled habits are checked in."""
    if await _perfect_day_already_awarded(session, user.id, day):
        return None
    scheduled = await scheduled_habit_ids(session, user.id, day)
    checked = await habit_repo.checked_in_habit_ids(session, user.id, day)
    if not perfect_day_service.is_perfect_day(scheduled, checked):
        return None
    return await award_xp(
        session,
        user,
        amount=XP_PERFECT_DAY,
        reason=XpReason.PERFECT_DAY,
        ref_id=day.toordinal(),
    )
