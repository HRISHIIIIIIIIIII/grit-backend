"""Data access for habits and check-ins."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit, HabitCheckin


async def get(session: AsyncSession, habit_id: int) -> Habit | None:
    return await session.get(Habit, habit_id)


async def get_owned(session: AsyncSession, habit_id: int, user_id: int) -> Habit | None:
    habit = await session.get(Habit, habit_id)
    if habit is None or habit.user_id != user_id:
        return None
    return habit


async def list_for_user(
    session: AsyncSession, user_id: int, *, include_archived: bool = False
) -> list[Habit]:
    stmt = select(Habit).where(Habit.user_id == user_id)
    if not include_archived:
        stmt = stmt.where(Habit.archived.is_(False))
    stmt = stmt.order_by(Habit.created_at, Habit.id)
    return list((await session.execute(stmt)).scalars().all())


async def active_habits(session: AsyncSession, user_id: int) -> list[Habit]:
    return await list_for_user(session, user_id, include_archived=False)


async def checkin_for_day(
    session: AsyncSession, habit_id: int, day: date
) -> HabitCheckin | None:
    stmt = select(HabitCheckin).where(
        HabitCheckin.habit_id == habit_id, HabitCheckin.local_date == day
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def checkin_dates_for_habit(session: AsyncSession, habit_id: int) -> list[date]:
    stmt = select(HabitCheckin.local_date).where(HabitCheckin.habit_id == habit_id)
    return list((await session.execute(stmt)).scalars().all())


async def active_dates_for_user(session: AsyncSession, user_id: int) -> set[date]:
    stmt = select(HabitCheckin.local_date).where(HabitCheckin.user_id == user_id).distinct()
    return set((await session.execute(stmt)).scalars().all())


async def checked_in_habit_ids(session: AsyncSession, user_id: int, day: date) -> set[int]:
    stmt = select(HabitCheckin.habit_id).where(
        HabitCheckin.user_id == user_id, HabitCheckin.local_date == day
    )
    return set((await session.execute(stmt)).scalars().all())
