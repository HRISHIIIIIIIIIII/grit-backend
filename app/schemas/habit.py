"""Habit request/response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import HabitCategory
from app.schemas.common import ORMModel


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: HabitCategory
    icon: str | None = Field(default=None, max_length=40)
    xp_value: int = Field(default=15, ge=1, le=1000)
    schedule: str = Field(default="daily", max_length=255)
    linked_roadmap_id: int | None = None


class HabitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: HabitCategory | None = None
    icon: str | None = Field(default=None, max_length=40)
    xp_value: int | None = Field(default=None, ge=1, le=1000)
    schedule: str | None = Field(default=None, max_length=255)
    linked_roadmap_id: int | None = None


class HabitRead(ORMModel):
    id: int
    name: str
    category: HabitCategory
    icon: str | None
    xp_value: int
    schedule: str
    archived: bool
    linked_roadmap_id: int | None
    created_at: datetime
    # Derived fields.
    current_streak: int = 0
    checked_in_today: bool = False


class CheckinRead(ORMModel):
    id: int
    habit_id: int
    local_date: date
    created_at: datetime


class CheckinResult(BaseModel):
    checkin: CheckinRead
    xp_awarded: int
    perfect_day: bool
    current_streak: int
