"""Data access for goals, milestones and goal-habit links."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.goal import Goal, GoalHabit, Milestone


async def get_detail(session: AsyncSession, goal_id: int, user_id: int) -> Goal | None:
    stmt = (
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == user_id)
        .options(selectinload(Goal.milestones), selectinload(Goal.habit_links))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: int) -> list[Goal]:
    stmt = (
        select(Goal)
        .where(Goal.user_id == user_id)
        .options(selectinload(Goal.milestones), selectinload(Goal.habit_links))
        .order_by(Goal.created_at, Goal.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_milestone(
    session: AsyncSession, goal_id: int, milestone_id: int
) -> Milestone | None:
    stmt = select(Milestone).where(
        Milestone.id == milestone_id, Milestone.goal_id == goal_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def habit_ids_for_goal(session: AsyncSession, goal_id: int) -> list[int]:
    stmt = select(GoalHabit.habit_id).where(GoalHabit.goal_id == goal_id)
    return list((await session.execute(stmt)).scalars().all())
