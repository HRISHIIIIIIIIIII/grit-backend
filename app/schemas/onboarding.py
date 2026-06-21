"""Onboarding request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import HabitCategory, MentorTone
from app.schemas.auth import MeResponse


class OnboardingHabit(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: HabitCategory
    icon: str | None = Field(default=None, max_length=40)
    xp_value: int = Field(default=20, ge=1, le=1000)


class OnboardingRequest(BaseModel):
    focus_areas: list[HabitCategory] = Field(default_factory=list)
    habits: list[OnboardingHabit] = Field(default_factory=list)
    daily_target: int = Field(default=3, ge=1, le=8)
    reminder_slot: str | None = Field(default=None, pattern="^(morning|midday|evening)$")
    intensity: MentorTone = MentorTone.HARD
    identity_word: str | None = Field(default=None, max_length=60)
    pact_accepted: bool = False


class OnboardingResponse(BaseModel):
    user: MeResponse
    habits_created: int
