"""Achievements router: GET /achievements (catalog + the user's progress)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.models.achievement import Achievement, UserAchievement
from app.schemas.achievement import AchievementRead
from app.services import achievements as achievement_service

router = APIRouter(prefix="/achievements", tags=["Achievements"])


def _to_read(achievement: Achievement, link: UserAchievement) -> AchievementRead:
    unlocked = link.unlocked_at is not None
    # Hidden achievements mask their name/criteria until unlocked.
    if achievement.hidden and not unlocked:
        return AchievementRead(
            code=achievement.code,
            name="Hidden Achievement",
            description="Keep going to discover how to unlock this one.",
            icon="❓",
            tier=achievement.tier.value,
            target=achievement.target,
            progress=0,
            unlocked=False,
            unlocked_at=None,
            hidden=True,
        )
    return AchievementRead(
        code=achievement.code,
        name=achievement.name,
        description=achievement.description,
        icon=achievement.icon,
        tier=achievement.tier.value,
        target=achievement.target,
        progress=link.progress,
        unlocked=unlocked,
        unlocked_at=link.unlocked_at,
        hidden=achievement.hidden,
    )


@router.get("", response_model=list[AchievementRead])
async def list_achievements(
    current_user: CurrentUser, session: DbSession
) -> list[AchievementRead]:
    rows = await achievement_service.list_with_progress(session, current_user)
    return [_to_read(a, link) for a, link in rows]
