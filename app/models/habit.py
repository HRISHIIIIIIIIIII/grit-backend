"""Habit and HabitCheckin ORM models.

A habit's current streak is DERIVED from check-in history, not stored here.
``HabitCheckin`` enforces one completion per local day via a unique constraint.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import CheckinSource, HabitCategory

if TYPE_CHECKING:
    from app.models.user import User


class Habit(Base, TimestampMixin):
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[HabitCategory] = mapped_column(
        Enum(HabitCategory, native_enum=False, length=20), nullable=False
    )
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    xp_value: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    # schedule: "daily" | weekly mask (e.g. "1111100") | an RRULE string.
    schedule: Mapped[str] = mapped_column(String(255), default="daily", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linked_roadmap_id: Mapped[int | None] = mapped_column(
        ForeignKey("roadmaps.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="habits")
    checkins: Mapped[list[HabitCheckin]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )


class HabitCheckin(Base, TimestampMixin):
    __tablename__ = "habit_checkins"
    __table_args__ = (
        UniqueConstraint("habit_id", "local_date", name="uq_checkin_habit_local_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(
        ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    local_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[CheckinSource] = mapped_column(
        Enum(CheckinSource, native_enum=False, length=20),
        default=CheckinSource.MANUAL,
        nullable=False,
    )

    habit: Mapped[Habit] = relationship(back_populates="checkins")
    user: Mapped[User] = relationship(back_populates="checkins")
