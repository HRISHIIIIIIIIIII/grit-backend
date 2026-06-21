"""Data access for User + UserSettings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSettings


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def create(session: AsyncSession, *, user: User) -> User:
    session.add(user)
    await session.flush()
    return user


async def get_settings(session: AsyncSession, user_id: int) -> UserSettings | None:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()
