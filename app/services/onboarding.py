"""Onboarding completion service.

Atomically persists everything the onboarding wizard collects: identity word,
focus areas, the pact, daily target, reminder slot, mentor tone (from intensity),
and the selected starter habits. Reuses ``services.habits.create_habit`` so habit
creation stays consistent with the rest of the app.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserSettings
from app.repositories import notification as notification_repo
from app.schemas.habit import HabitCreate
from app.schemas.onboarding import OnboardingRequest
from app.services import habits as habit_service


async def complete_onboarding(
    session: AsyncSession, user: User, payload: OnboardingRequest
) -> int:
    """Persist onboarding data + create starter habits. Returns habits created."""
    user.identity_word = payload.identity_word or user.identity_word
    user.focus_areas = [c.value for c in payload.focus_areas]
    user.pact_accepted = payload.pact_accepted
    user.onboarding_completed = True

    settings = await notification_repo.settings_for(session, user.id)
    if settings is None:
        settings = UserSettings(user_id=user.id)
        session.add(settings)
    settings.daily_target = payload.daily_target
    settings.reminder_slot = payload.reminder_slot
    settings.mentor_tone = payload.intensity
    await session.flush()

    created = 0
    for habit in payload.habits:
        await habit_service.create_habit(
            session,
            user,
            HabitCreate(
                name=habit.name,
                category=habit.category,
                icon=habit.icon,
                xp_value=habit.xp_value,
            ),
        )
        created += 1
    await session.flush()
    return created
