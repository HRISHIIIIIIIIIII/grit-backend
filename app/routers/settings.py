"""Settings router: GET/PATCH /settings."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.models.user import UserSettings
from app.repositories import notification as notification_repo
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


async def _require_settings(session: DbSession, user_id: int) -> UserSettings:
    settings = await notification_repo.settings_for(session, user_id)
    if settings is None:
        # Self-heal: every user should have settings, but never 500 if missing.
        settings = UserSettings(user_id=user_id)
        session.add(settings)
        await session.flush()
    return settings


@router.get("", response_model=SettingsRead)
async def get_settings(current_user: CurrentUser, session: DbSession) -> SettingsRead:
    settings = await _require_settings(session, current_user.id)
    return SettingsRead.model_validate(settings)


@router.patch("", response_model=SettingsRead)
async def update_settings(
    payload: SettingsUpdate, current_user: CurrentUser, session: DbSession
) -> SettingsRead:
    settings = await _require_settings(session, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await session.flush()
    return SettingsRead.model_validate(settings)
