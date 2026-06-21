"""Progress (XP, level, heatmap, analytics) response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class LevelRead(BaseModel):
    level: int
    name: str
    xp_total: int
    current_threshold: int
    next_threshold: int | None
    xp_into_level: int
    xp_to_next: int | None
    progress_pct: int


class XpEventRead(BaseModel):
    amount: int
    reason: str
    ref_id: int | None
    created_at: object  # datetime; kept loose to avoid an extra import in callers

    model_config = {"from_attributes": True}


class XpSummary(BaseModel):
    xp_total: int
    level: int
    level_name: str
    recent_events: list[XpEventRead]


class HeatmapCell(BaseModel):
    date: date
    count: int


class HeatmapRead(BaseModel):
    range: str
    start: date
    end: date
    cells: list[HeatmapCell]


class CategoryCount(BaseModel):
    category: str
    count: int


class AnalyticsRead(BaseModel):
    period: str
    start: date
    end: date
    total_checkins: int
    active_days: int
    perfect_days: int
    xp_earned: int
    by_category: list[CategoryCount]
