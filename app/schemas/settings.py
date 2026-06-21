"""User settings request/response schemas."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, Field

from app.models.enums import MentorTone
from app.schemas.common import ORMModel


class SettingsRead(ORMModel):
    theme: str
    accent_color: str
    mentor_tone: MentorTone
    sound_enabled: bool
    public_on_leaderboards: bool
    quiet_hours_start: time | None
    quiet_hours_end: time | None
    notify_streak_protection: bool
    notify_milestone: bool
    notify_accountability: bool
    notify_reengagement: bool
    notify_review: bool
    notify_achievement: bool
    notify_encouragement: bool
    notify_social: bool


class SettingsUpdate(BaseModel):
    theme: str | None = Field(default=None, max_length=20)
    accent_color: str | None = Field(default=None, max_length=20)
    mentor_tone: MentorTone | None = None
    sound_enabled: bool | None = None
    public_on_leaderboards: bool | None = None
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    notify_streak_protection: bool | None = None
    notify_milestone: bool | None = None
    notify_accountability: bool | None = None
    notify_reengagement: bool | None = None
    notify_review: bool | None = None
    notify_achievement: bool | None = None
    notify_encouragement: bool | None = None
    notify_social: bool | None = None
