"""Goal + milestone request/response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import GoalStatus
from app.schemas.common import ORMModel


class MilestoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    due_label: str | None = Field(default=None, max_length=60)
    order_index: int = 0


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    due_label: str | None = Field(default=None, max_length=60)
    done: bool | None = None
    order_index: int | None = None


class MilestoneRead(ORMModel):
    id: int
    name: str
    due_label: str | None
    done: bool
    completed_at: datetime | None
    order_index: int


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    deadline: date | None = None
    started_at: date | None = None
    milestones: list[MilestoneCreate] = []
    habit_ids: list[int] = []


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    deadline: date | None = None
    status: GoalStatus | None = None
    habit_ids: list[int] | None = None


class GoalRead(ORMModel):
    id: int
    name: str
    icon: str | None
    color: str | None
    deadline: date | None
    started_at: date | None
    status: GoalStatus
    created_at: datetime
    milestones: list[MilestoneRead] = []
    habit_ids: list[int] = []
    done_milestones: int = 0
    total_milestones: int = 0
    progress_pct: int = 0
