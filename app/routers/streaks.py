"""Streaks router: GET /streaks, POST /streaks/freeze."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.streak import FreezeResult, StreakRead
from app.services import streak_service
from app.services.streaks import evolution_stage

router = APIRouter(prefix="/streaks", tags=["Streaks"])


@router.get("", response_model=StreakRead)
async def get_streak(current_user: CurrentUser, session: DbSession) -> StreakRead:
    streak = await streak_service.get_fresh_streak(session, current_user)
    return StreakRead(
        current_daily=streak.current_daily,
        longest=streak.longest,
        weekly_count=streak.weekly_count,
        monthly_count=streak.monthly_count,
        freeze_balance=streak.freeze_balance,
        evolution_stage=evolution_stage(streak.current_daily),
    )


@router.post("/freeze", response_model=FreezeResult)
async def use_freeze(current_user: CurrentUser, session: DbSession) -> FreezeResult:
    streak, protected, message = await streak_service.apply_freeze(session, current_user)
    return FreezeResult(
        current_daily=streak.current_daily,
        freeze_balance=streak.freeze_balance,
        protected=protected,
        message=message,
    )
