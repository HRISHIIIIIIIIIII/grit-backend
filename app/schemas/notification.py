"""Notification response schemas."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import NotificationType
from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    type: NotificationType
    title: str
    body: str
    action_label: str | None
    action_url: str | None
    read_at: datetime | None
    scheduled_for: datetime | None
    sent_at: datetime | None
    created_at: datetime


class ReadAllResult(ORMModel):
    marked_read: int
