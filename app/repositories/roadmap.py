"""Data access for roadmaps, phases and topics."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.habit import Habit
from app.models.roadmap import Phase, Roadmap, Topic


async def get_owned(session: AsyncSession, roadmap_id: int, user_id: int) -> Roadmap | None:
    roadmap = await session.get(Roadmap, roadmap_id)
    if roadmap is None or roadmap.user_id != user_id:
        return None
    return roadmap


async def get_detail(session: AsyncSession, roadmap_id: int, user_id: int) -> Roadmap | None:
    stmt = (
        select(Roadmap)
        .where(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
        .options(selectinload(Roadmap.phases).selectinload(Phase.topics))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: int) -> list[Roadmap]:
    stmt = (
        select(Roadmap)
        .where(Roadmap.user_id == user_id)
        .options(selectinload(Roadmap.phases).selectinload(Phase.topics))
        .order_by(Roadmap.created_at, Roadmap.id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_topic_owned(
    session: AsyncSession, topic_id: int, user_id: int
) -> tuple[Topic, Phase, Roadmap] | None:
    stmt = (
        select(Topic, Phase, Roadmap)
        .join(Phase, Topic.phase_id == Phase.id)
        .join(Roadmap, Phase.roadmap_id == Roadmap.id)
        .where(Topic.id == topic_id, Roadmap.user_id == user_id)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None
    return row[0], row[1], row[2]


async def phase_topics(session: AsyncSession, phase_id: int) -> list[Topic]:
    stmt = select(Topic).where(Topic.phase_id == phase_id)
    return list((await session.execute(stmt)).scalars().all())


async def all_topics(session: AsyncSession, roadmap_id: int) -> list[Topic]:
    stmt = (
        select(Topic).join(Phase, Topic.phase_id == Phase.id).where(Phase.roadmap_id == roadmap_id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def linked_dsa_habit(session: AsyncSession, user_id: int, roadmap_id: int) -> Habit | None:
    stmt = select(Habit).where(
        Habit.user_id == user_id,
        Habit.linked_roadmap_id == roadmap_id,
        Habit.archived.is_(False),
    )
    return (await session.execute(stmt)).scalars().first()
