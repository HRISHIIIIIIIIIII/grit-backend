"""Data access for leaderboards and friendships."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FriendshipStatus
from app.models.user import Friendship, User, UserSettings
from app.models.xp import XpEvent


async def public_users_by_xp(session: AsyncSession, *, limit: int = 100) -> list[User]:
    stmt = (
        select(User)
        .join(UserSettings, UserSettings.user_id == User.id)
        .where(UserSettings.public_on_leaderboards.is_(True))
        .order_by(User.xp_total.desc(), User.id)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def weekly_xp_for_users(
    session: AsyncSession, user_ids: list[int], since: datetime
) -> dict[int, int]:
    if not user_ids:
        return {}
    stmt = (
        select(XpEvent.user_id, func.coalesce(func.sum(XpEvent.amount), 0))
        .where(XpEvent.user_id.in_(user_ids), XpEvent.created_at >= since)
        .group_by(XpEvent.user_id)
    )
    return {row[0]: int(row[1]) for row in (await session.execute(stmt)).all()}


async def accepted_friend_ids(session: AsyncSession, user_id: int) -> list[int]:
    stmt = select(Friendship).where(
        Friendship.status == FriendshipStatus.ACCEPTED,
        or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
    )
    ids: list[int] = []
    for f in (await session.execute(stmt)).scalars().all():
        ids.append(f.friend_id if f.user_id == user_id else f.user_id)
    return ids


async def friendships_for(session: AsyncSession, user_id: int) -> list[Friendship]:
    stmt = select(Friendship).where(
        or_(Friendship.user_id == user_id, Friendship.friend_id == user_id)
    )
    return list((await session.execute(stmt)).scalars().all())


async def existing_friendship(session: AsyncSession, a: int, b: int) -> Friendship | None:
    stmt = select(Friendship).where(
        or_(
            (Friendship.user_id == a) & (Friendship.friend_id == b),
            (Friendship.user_id == b) & (Friendship.friend_id == a),
        )
    )
    return (await session.execute(stmt)).scalars().first()


async def users_by_ids(session: AsyncSession, ids: list[int]) -> dict[int, User]:
    if not ids:
        return {}
    stmt = select(User).where(User.id.in_(ids))
    return {u.id: u for u in (await session.execute(stmt)).scalars().all()}
