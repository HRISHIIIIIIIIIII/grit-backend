"""Achievement catalog and per-user unlock/progress tracking."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import AchievementTier

if TYPE_CHECKING:
    from app.models.user import User


class Achievement(Base):
    """Catalog entry. Hidden achievements don't reveal criteria until unlocked."""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    tier: Mapped[AchievementTier] = mapped_column(
        Enum(AchievementTier, native_enum=False, length=20), nullable=False
    )
    # Number of progress units required to unlock (1 = boolean-style).
    target: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user_links: Mapped[list[UserAchievement]] = relationship(
        back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="achievements")
    achievement: Mapped[Achievement] = relationship(back_populates="user_links")
