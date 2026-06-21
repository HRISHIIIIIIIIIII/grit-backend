"""Auth request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="Europe/Berlin", max_length=64)
    identity_word: str | None = Field(default=None, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserPublic(ORMModel):
    id: int
    email: str
    display_name: str
    avatar_seed: str | None
    timezone: str
    identity_word: str | None
    xp_total: int
    onboarding_completed: bool
    pact_accepted: bool
    focus_areas: list[str] | None
    created_at: datetime


class MeResponse(UserPublic):
    level: int
    level_name: str
    xp_to_next: int | None


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    identity_word: str | None = Field(default=None, max_length=60)
    timezone: str | None = Field(default=None, max_length=64)
    avatar_seed: str | None = Field(default=None, max_length=120)
