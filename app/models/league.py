"""Weekly League and LeaderboardEntry ORM models.

Weekly leagues of ~30 users ranked by XP earned this week; top 7 promote,
bottom N demote. Friends and Global all-time boards are computed from XpEvent
/ User.xp_total directly and need no extra tables.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class League(Base, TimestampMixin):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # ISO week boundaries (local Monday) this league covers.
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    entries: Mapped[list[LeaderboardEntry]] = relationship(
        back_populates="league", cascade="all, delete-orphan"
    )


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("league_id", "user_id", name="uq_league_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekly_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    league: Mapped[League] = relationship(back_populates="entries")
