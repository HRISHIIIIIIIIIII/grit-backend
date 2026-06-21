"""Roadmap request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class TopicRead(ORMModel):
    id: int
    name: str
    done: bool
    completed_at: datetime | None
    order_index: int


class PhaseRead(ORMModel):
    id: int
    name: str
    duration_label: str | None
    order_index: int
    topics: list[TopicRead]
    done_count: int = 0
    total_count: int = 0
    complete: bool = False


class RoadmapSummary(ORMModel):
    id: int
    title: str
    icon: str | None
    color: str | None
    source: str
    is_dsa_linked: bool
    created_at: datetime
    total_topics: int = 0
    done_topics: int = 0
    progress_pct: int = 0


class RoadmapDetail(RoadmapSummary):
    phases: list[PhaseRead] = []


class RoadmapImportRequest(BaseModel):
    markdown: str = Field(min_length=1)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    is_dsa_linked: bool = False


class RoadmapCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    is_dsa_linked: bool = False


class TopicUpdate(BaseModel):
    done: bool


class TopicToggleResult(BaseModel):
    topic: TopicRead
    phase_complete: bool
    roadmap_progress_pct: int
    xp_awarded: int
    dsa_habit_credited: bool
