"""Streak response schemas."""

from __future__ import annotations

from app.models.enums import EvolutionStage
from app.schemas.common import ORMModel


class StreakRead(ORMModel):
    current_daily: int
    longest: int
    weekly_count: int
    monthly_count: int
    freeze_balance: int
    evolution_stage: EvolutionStage


class FreezeResult(ORMModel):
    current_daily: int
    freeze_balance: int
    protected: bool
    message: str
