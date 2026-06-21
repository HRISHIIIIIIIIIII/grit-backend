"""Data access for notifications and user settings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import UserSettings


async def list_for_user(
    session: AsyncSession, user_id: int, *, limit: int = 50
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_owned(
    session: AsyncSession, notification_id: int, user_id: int
) -> Notification | None:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        return None
    return notification


async def unread_for_user(session: AsyncSession, user_id: int) -> list[Notification]:
    stmt = select(Notification).where(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    )
    return list((await session.execute(stmt)).scalars().all())


async def settings_for(session: AsyncSession, user_id: int) -> UserSettings | None:
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()
