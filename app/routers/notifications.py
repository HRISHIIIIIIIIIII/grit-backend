"""Notifications router: list, mark read, mark all read."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.notification import NotificationRead, ReadAllResult
from app.services import notifications as notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    current_user: CurrentUser, session: DbSession
) -> list[NotificationRead]:
    items = await notification_service.list_notifications(session, current_user)
    return [NotificationRead.model_validate(n) for n in items]


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: int, current_user: CurrentUser, session: DbSession
) -> NotificationRead:
    notification = await notification_service.mark_read(
        session, current_user, notification_id
    )
    return NotificationRead.model_validate(notification)


@router.post("/read-all", response_model=ReadAllResult)
async def mark_all_read(current_user: CurrentUser, session: DbSession) -> ReadAllResult:
    count = await notification_service.mark_all_read(session, current_user)
    return ReadAllResult(marked_read=count)
