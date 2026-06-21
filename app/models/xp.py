"""XpEvent ledger. ``User.xp_total`` is the running sum; level is derived."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import XpReason

if TYPE_CHECKING:
    from app.models.user import User


class XpEvent(Base, TimestampMixin):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[XpReason] = mapped_column(
        Enum(XpReason, native_enum=False, length=20), nullable=False
    )
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="xp_events")
