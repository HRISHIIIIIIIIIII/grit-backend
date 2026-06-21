"""Achievement response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AchievementRead(BaseModel):
    code: str
    name: str
    description: str
    icon: str | None
    tier: str
    target: int
    progress: int
    unlocked: bool
    unlocked_at: datetime | None
    hidden: bool
