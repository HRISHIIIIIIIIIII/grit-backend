"""Progress router: GET /xp, /level, /heatmap, /analytics."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.progress import AnalyticsRead, HeatmapRead, LevelRead, XpSummary
from app.services import progress as progress_service

router = APIRouter(tags=["Progress"])


@router.get("/xp", response_model=XpSummary)
async def get_xp(current_user: CurrentUser, session: DbSession) -> XpSummary:
    return await progress_service.xp_summary(session, current_user)


@router.get("/level", response_model=LevelRead)
async def get_level(current_user: CurrentUser) -> LevelRead:
    return progress_service.level_read(current_user)


@router.get("/heatmap", response_model=HeatmapRead)
async def get_heatmap(
    current_user: CurrentUser,
    session: DbSession,
    range: Literal["weeks", "year"] = Query(default="weeks"),
) -> HeatmapRead:
    return await progress_service.heatmap(session, current_user, range)


@router.get("/analytics", response_model=AnalyticsRead)
async def get_analytics(
    current_user: CurrentUser,
    session: DbSession,
    period: Literal["week", "month", "year"] = Query(default="week"),
) -> AnalyticsRead:
    return await progress_service.analytics(session, current_user, period)
