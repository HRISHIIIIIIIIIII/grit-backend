"""Progress read-models: XP summary, level, heatmap and analytics."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_date, start_of_local_day_utc
from app.models.user import User
from app.repositories import progress as progress_repo
from app.schemas.progress import (
    AnalyticsRead,
    CategoryCount,
    HeatmapCell,
    HeatmapRead,
    LevelRead,
    XpEventRead,
    XpSummary,
)
from app.services.gamification import level_info


def level_read(user: User) -> LevelRead:
    info = level_info(user.xp_total)
    return LevelRead(
        level=info.level,
        name=info.name,
        xp_total=user.xp_total,
        current_threshold=info.current_threshold,
        next_threshold=info.next_threshold,
        xp_into_level=info.xp_into_level,
        xp_to_next=info.xp_to_next,
        progress_pct=info.progress_pct,
    )


async def xp_summary(session: AsyncSession, user: User) -> XpSummary:
    info = level_info(user.xp_total)
    events = await progress_repo.recent_xp_events(session, user.id)
    return XpSummary(
        xp_total=user.xp_total,
        level=info.level,
        level_name=info.name,
        recent_events=[XpEventRead.model_validate(e) for e in events],
    )


def _heatmap_window(range_: str, today: date) -> tuple[date, date]:
    if range_ == "year":
        return today - timedelta(days=364), today
    # default: weeks (last 12 weeks)
    return today - timedelta(weeks=12) + timedelta(days=1), today


async def heatmap(session: AsyncSession, user: User, range_: str) -> HeatmapRead:
    today = local_date(user.timezone)
    start, end = _heatmap_window(range_, today)
    counts = await progress_repo.checkin_counts_by_day(session, user.id, start, end)
    cells = [
        HeatmapCell(date=start + timedelta(days=i), count=counts.get(start + timedelta(days=i), 0))
        for i in range((end - start).days + 1)
    ]
    return HeatmapRead(range=range_, start=start, end=end, cells=cells)


def _analytics_window(period: str, today: date) -> tuple[date, date]:
    if period == "month":
        return today.replace(day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    # default: week (ISO week, Monday start)
    return today - timedelta(days=today.weekday()), today


async def analytics(session: AsyncSession, user: User, period: str) -> AnalyticsRead:
    today = local_date(user.timezone)
    start, end = _analytics_window(period, today)

    total = await progress_repo.total_checkins(session, user.id, start, end)
    active = await progress_repo.active_day_count(session, user.id, start, end)
    perfect = await progress_repo.perfect_day_count(session, user.id, start, end)
    by_cat = await progress_repo.checkin_counts_by_category(session, user.id, start, end)

    start_dt = start_of_local_day_utc(user.timezone, start)
    end_dt = start_of_local_day_utc(user.timezone, end + timedelta(days=1))
    xp = await progress_repo.xp_earned_between(session, user.id, start_dt, end_dt)

    return AnalyticsRead(
        period=period,
        start=start,
        end=end,
        total_checkins=total,
        active_days=active,
        perfect_days=perfect,
        xp_earned=xp,
        by_category=[CategoryCount(category=c, count=n) for c, n in sorted(by_cat.items())],
    )
