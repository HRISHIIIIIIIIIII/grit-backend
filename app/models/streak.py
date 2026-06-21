"""Per-user Streak cache.

These columns are a materialised cache; the source of truth is always a
recompute from HabitCheckin history (see ``services.streaks``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import EvolutionStage  # noqa: F401 (referenced in services)

if TYPE_CHECKING:
    from app.models.user import User


class Streak(Base):
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    current_daily: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weekly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    freeze_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship(back_populates="streak")
