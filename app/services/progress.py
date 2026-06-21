"""Progress read-models: XP summary, level, heatmap and analytics."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import get_zone, local_date, start_of_local_day_utc
from app.models.streak import Streak
from app.models.user import User
from app.repositories import progress as progress_repo
from app.schemas.progress import (
    AnalyticsRead,
    AnalyticsRecords,
    CategoryCount,
    HeatmapCell,
    HeatmapRead,
    LevelRead,
    TimeOfDayBucket,
    TrendPoint,
    VelocityItem,
    XpEventRead,
    XpSummary,
)
from app.services.gamification import level_info

# Time-of-day buckets (label, start_hour_inclusive, end_hour_exclusive).
_TIME_BUCKETS: tuple[tuple[str, int, int], ...] = (
    ("5–8a", 5, 8),
    ("8–12p", 8, 12),
    ("12–5p", 12, 17),
    ("5–9p", 17, 21),
    ("9p+", 21, 5),  # wraps past midnight
)


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


def _build_trend(period: str, counts: dict[date, int], start: date, end: date) -> list[TrendPoint]:
    """A consistency series sized to the period: daily (week), weekly (month), monthly (year)."""
    points: list[TrendPoint] = []
    if period == "year":
        # 12 monthly buckets ending at `end`.
        cursor = end.replace(day=1)
        months: list[date] = []
        for _ in range(12):
            months.append(cursor)
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        for m in reversed(months):
            total = sum(v for d, v in counts.items() if (d.year, d.month) == (m.year, m.month))
            points.append(TrendPoint(label=m.strftime("%b"), value=total))
    elif period == "month":
        # weekly buckets across the month window.
        cursor = start
        while cursor <= end:
            week_end = min(cursor + timedelta(days=6), end)
            total = sum(v for d, v in counts.items() if cursor <= d <= week_end)
            points.append(TrendPoint(label=cursor.strftime("%-d"), value=total))
            cursor = week_end + timedelta(days=1)
    else:  # week — daily points
        cursor = start
        while cursor <= end:
            points.append(TrendPoint(label=cursor.strftime("%a"), value=counts.get(cursor, 0)))
            cursor += timedelta(days=1)
    return points


def _bucket_time_of_day(timestamps: list[datetime], tz_name: str) -> list[TimeOfDayBucket]:
    zone = get_zone(tz_name)
    tallies = [0] * len(_TIME_BUCKETS)
    for ts in timestamps:
        hour = ts.astimezone(zone).hour
        for i, (_, lo, hi) in enumerate(_TIME_BUCKETS):
            in_bucket = lo <= hour < hi if lo < hi else (hour >= lo or hour < hi)
            if in_bucket:
                tallies[i] += 1
                break
    return [
        TimeOfDayBucket(label=label, count=tallies[i])
        for i, (label, _, _) in enumerate(_TIME_BUCKETS)
    ]


async def analytics(session: AsyncSession, user: User, period: str) -> AnalyticsRead:
    today = local_date(user.timezone)
    start, end = _analytics_window(period, today)

    total = await progress_repo.total_checkins(session, user.id, start, end)
    active = await progress_repo.active_day_count(session, user.id, start, end)
    perfect = await progress_repo.perfect_day_count(session, user.id, start, end)
    by_cat = await progress_repo.checkin_counts_by_category(session, user.id, start, end)
    counts = await progress_repo.checkin_counts_by_day(session, user.id, start, end)

    start_dt = start_of_local_day_utc(user.timezone, start)
    end_dt = start_of_local_day_utc(user.timezone, end + timedelta(days=1))
    xp = await progress_repo.xp_earned_between(session, user.id, start_dt, end_dt)

    timestamps = await progress_repo.checkin_timestamps(session, user.id, start_dt, end_dt)
    velocity_rows = await progress_repo.topics_done_by_roadmap(session, user.id)
    streak = (
        await session.execute(select(Streak).where(Streak.user_id == user.id))
    ).scalar_one_or_none()
    records = AnalyticsRecords(
        longest_streak=streak.longest if streak else 0,
        best_day_count=max(counts.values(), default=0),
        total_checkins=await progress_repo.total_checkins_all_time(session, user.id),
    )

    return AnalyticsRead(
        period=period,
        start=start,
        end=end,
        total_checkins=total,
        active_days=active,
        perfect_days=perfect,
        xp_earned=xp,
        by_category=[CategoryCount(category=c, count=n) for c, n in sorted(by_cat.items())],
        trend=_build_trend(period, counts, start, end),
        time_of_day=_bucket_time_of_day(timestamps, user.timezone),
        velocity=[
            VelocityItem(roadmap_id=r[0], title=r[1], topics_done=r[2]) for r in velocity_rows
        ],
        records=records,
    )
