"""DB-facing streak reads for the API (freshly recomputed from check-ins)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_date
from app.models.streak import Streak
from app.models.user import User
from app.services import scoring
from app.services.streaks import evolution_stage


async def get_fresh_streak(session: AsyncSession, user: User) -> Streak:
    """Recompute and persist the streak cache, then return it."""
    today = local_date(user.timezone)
    return await scoring.sync_user_streak(session, user, today)


async def apply_freeze(session: AsyncSession, user: User) -> tuple[Streak, bool, str]:
    """Refresh streak protection.

    Streak freezes are auto-consumed by the recompute when a day is missed, so
    this endpoint recomputes and reports whether the streak is currently
    protected (a freeze is banked). Returns (streak, protected, message).
    """
    streak = await get_fresh_streak(session, user)
    if streak.freeze_balance > 0:
        return streak, True, f"{streak.freeze_balance} freeze(s) banked — your streak is protected."
    return streak, False, "No freezes available. Keep a 14-day run to earn one."


def stage_for(streak: Streak) -> str:
    return evolution_stage(streak.current_daily).value
