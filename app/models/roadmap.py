"""Roadmap, Phase, and Topic ORM models.

Roadmap progress = done topics / total topics. A phase auto-completes when all
its topics are done. Toggling a topic done on an ``is_dsa_linked`` roadmap
credits the user's linked DSA habit for today (handled in the service layer).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import RoadmapSource

if TYPE_CHECKING:
    from app.models.user import User


class Roadmap(Base, TimestampMixin):
    __tablename__ = "roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[RoadmapSource] = mapped_column(
        Enum(RoadmapSource, native_enum=False, length=20),
        default=RoadmapSource.IMPORTED,
        nullable=False,
    )
    is_dsa_linked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="roadmaps")
    phases: Mapped[list[Phase]] = relationship(
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="Phase.order_index",
    )


class Phase(Base):
    __tablename__ = "phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    roadmap: Mapped[Roadmap] = relationship(back_populates="phases")
    topics: Mapped[list[Topic]] = relationship(
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="Topic.order_index",
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    phase_id: Mapped[int] = mapped_column(
        ForeignKey("phases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    phase: Mapped[Phase] = relationship(back_populates="topics")
