"""User, UserSettings (1:1), and Friendship ORM models."""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import FriendshipStatus, MentorTone

if TYPE_CHECKING:
    from app.models.achievement import UserAchievement
    from app.models.goal import Goal
    from app.models.habit import Habit, HabitCheckin
    from app.models.notification import Notification
    from app.models.roadmap import Roadmap
    from app.models.streak import Streak
    from app.models.xp import XpEvent


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_seed: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Berlin", nullable=False)
    identity_word: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # xp_total is a cached sum of XpEvent.amount; level is DERIVED, never stored.
    xp_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    settings: Mapped[UserSettings] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    habits: Mapped[list[Habit]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    checkins: Mapped[list[HabitCheckin]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[list[Goal]] = relationship(back_populates="user", cascade="all, delete-orphan")
    roadmaps: Mapped[list[Roadmap]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    streak: Mapped[Streak | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    xp_events: Mapped[list[XpEvent]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list[UserAchievement]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    theme: Mapped[str] = mapped_column(String(20), default="light", nullable=False)
    accent_color: Mapped[str] = mapped_column(String(20), default="#0EA47F", nullable=False)
    mentor_tone: Mapped[MentorTone] = mapped_column(
        Enum(MentorTone, native_enum=False, length=20),
        default=MentorTone.HARD,
        nullable=False,
    )
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    public_on_leaderboards: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Per-type notification toggles (all default on).
    notify_streak_protection: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_milestone: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_accountability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_reengagement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_achievement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_encouragement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_social: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="settings")


class Friendship(Base, TimestampMixin):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("user_id", "friend_id", name="uq_friendship_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    friend_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus, native_enum=False, length=20),
        default=FriendshipStatus.PENDING,
        nullable=False,
    )
