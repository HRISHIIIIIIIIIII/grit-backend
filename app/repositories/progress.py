"""Aggregation queries for XP, heatmap and analytics."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.habit import Habit, HabitCheckin
from app.models.xp import XpEvent


async def recent_xp_events(
    session: AsyncSession, user_id: int, *, limit: int = 20
) -> list[XpEvent]:
    stmt = (
        select(XpEvent)
        .where(XpEvent.user_id == user_id)
        .order_by(XpEvent.created_at.desc(), XpEvent.id.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def checkin_counts_by_day(
    session: AsyncSession, user_id: int, start: date, end: date
) -> dict[date, int]:
    stmt = (
        select(HabitCheckin.local_date, func.count())
        .where(
            HabitCheckin.user_id == user_id,
            HabitCheckin.local_date >= start,
            HabitCheckin.local_date <= end,
        )
        .group_by(HabitCheckin.local_date)
    )
    return {row[0]: row[1] for row in (await session.execute(stmt)).all()}


async def checkin_counts_by_category(
    session: AsyncSession, user_id: int, start: date, end: date
) -> dict[str, int]:
    stmt = (
        select(Habit.category, func.count())
        .join(HabitCheckin, HabitCheckin.habit_id == Habit.id)
        .where(
            HabitCheckin.user_id == user_id,
            HabitCheckin.local_date >= start,
            HabitCheckin.local_date <= end,
        )
        .group_by(Habit.category)
    )
    out: dict[str, int] = {}
    for category, count in (await session.execute(stmt)).all():
        key = category.value if hasattr(category, "value") else str(category)
        out[key] = count
    return out


async def total_checkins(session: AsyncSession, user_id: int, start: date, end: date) -> int:
    stmt = select(func.count()).where(
        HabitCheckin.user_id == user_id,
        HabitCheckin.local_date >= start,
        HabitCheckin.local_date <= end,
    )
    return int((await session.execute(stmt)).scalar_one())


async def active_day_count(session: AsyncSession, user_id: int, start: date, end: date) -> int:
    stmt = select(func.count(func.distinct(HabitCheckin.local_date))).where(
        HabitCheckin.user_id == user_id,
        HabitCheckin.local_date >= start,
        HabitCheckin.local_date <= end,
    )
    return int((await session.execute(stmt)).scalar_one())


async def perfect_day_count(session: AsyncSession, user_id: int, start: date, end: date) -> int:
    stmt = select(func.count()).where(
        XpEvent.user_id == user_id,
        XpEvent.reason == XpReason.PERFECT_DAY,
        XpEvent.ref_id >= start.toordinal(),
        XpEvent.ref_id <= end.toordinal(),
    )
    return int((await session.execute(stmt)).scalar_one())


async def xp_earned_between(
    session: AsyncSession, user_id: int, start_dt: object, end_dt: object
) -> int:
    stmt = select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
        XpEvent.user_id == user_id,
        XpEvent.created_at >= start_dt,
        XpEvent.created_at <= end_dt,
    )
    return int((await session.execute(stmt)).scalar_one())
