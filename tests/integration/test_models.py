from __future__ import annotations

from datetime import date

import pytest
from app.models import Habit, HabitCheckin, User, UserSettings
from app.models.enums import HabitCategory
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_user(session: AsyncSession) -> User:
    user = User(
        email="jordan@example.com",
        password_hash="x",
        display_name="Jordan Reyes",
        timezone="Europe/Berlin",
        settings=UserSettings(),
    )
    session.add(user)
    await session.flush()
    return user


async def test_user_settings_one_to_one(session: AsyncSession) -> None:
    user = await _make_user(session)
    await session.commit()
    loaded = (await session.execute(select(User).where(User.id == user.id))).scalar_one()
    assert loaded.settings is not None
    assert loaded.settings.accent_color == "#0EA47F"


async def test_checkin_unique_per_local_day(session: AsyncSession) -> None:
    user = await _make_user(session)
    habit = Habit(user_id=user.id, name="Morning run", category=HabitCategory.FITNESS, xp_value=30)
    session.add(habit)
    await session.flush()

    today = date(2026, 6, 21)
    session.add(HabitCheckin(habit_id=habit.id, user_id=user.id, local_date=today))
    await session.flush()
    session.add(HabitCheckin(habit_id=habit.id, user_id=user.id, local_date=today))
    with pytest.raises(IntegrityError):
        await session.flush()
