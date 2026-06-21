"""Notification engine.

Dispatch respects per-type toggles and quiet hours. ``mentor_tone`` selects the
ATLAS copy variant. Instant notifications (milestone/achievement) are dispatched
inline; recurring/timed ones are created by Celery tasks. Quiet hours defer a
notification's ``scheduled_for`` to the end of the quiet window rather than
sending immediately.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_now, start_of_local_day_utc, utcnow
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.user import User, UserSettings
from app.repositories import notification as notification_repo
from app.services import mentor

# Map each notification type to its per-type settings toggle attribute.
_TOGGLE_ATTR: dict[NotificationType, str] = {
    NotificationType.STREAK_PROTECTION: "notify_streak_protection",
    NotificationType.MILESTONE: "notify_milestone",
    NotificationType.ACCOUNTABILITY: "notify_accountability",
    NotificationType.REENGAGEMENT: "notify_reengagement",
    NotificationType.REVIEW: "notify_review",
    NotificationType.ACHIEVEMENT: "notify_achievement",
    NotificationType.ENCOURAGEMENT: "notify_encouragement",
    NotificationType.SOCIAL: "notify_social",
}


def is_type_enabled(settings: UserSettings | None, ntype: NotificationType) -> bool:
    if settings is None:
        return True
    value = getattr(settings, _TOGGLE_ATTR[ntype], True)
    # Column defaults aren't applied until flush; treat unset (None) as enabled.
    return True if value is None else bool(value)


def in_quiet_hours(settings: UserSettings | None, at_local: time) -> bool:
    if settings is None or settings.quiet_hours_start is None or settings.quiet_hours_end is None:
        return False
    start = settings.quiet_hours_start
    end = settings.quiet_hours_end
    if start == end:
        return False
    if start < end:  # same-day window, e.g. 13:00-15:00
        return start <= at_local < end
    # overnight window, e.g. 22:00-07:00
    return at_local >= start or at_local < end


def _quiet_end_utc(user: User, settings: UserSettings, now: datetime) -> datetime:
    """The UTC instant at which the current quiet window ends."""
    local = local_now(user.timezone, now=now)
    end = settings.quiet_hours_end
    assert end is not None
    end_today = datetime.combine(local.date(), end, tzinfo=local.tzinfo)
    if end_today <= local:
        end_today = datetime.combine(
            local.date() + timedelta(days=1), end, tzinfo=local.tzinfo
        )

    return end_today.astimezone(UTC)


async def create_notification(
    session: AsyncSession,
    user: User,
    *,
    ntype: NotificationType,
    title: str,
    body: str,
    action_label: str | None = None,
    action_url: str | None = None,
    now: datetime | None = None,
) -> Notification | None:
    """Create + dispatch a notification, honouring toggles and quiet hours.

    Returns the created ``Notification`` or ``None`` if the type is disabled.
    """
    settings = await notification_repo.settings_for(session, user.id)
    if not is_type_enabled(settings, ntype):
        return None

    now = now or utcnow()
    local = local_now(user.timezone, now=now)
    notification = Notification(
        user_id=user.id,
        type=ntype,
        title=title,
        body=body,
        action_label=action_label,
        action_url=action_url,
    )

    if settings is not None and in_quiet_hours(settings, local.timetz().replace(tzinfo=None)):
        # Defer delivery until the quiet window ends.
        notification.scheduled_for = _quiet_end_utc(user, settings, now)
        notification.sent_at = None
    else:
        notification.scheduled_for = now
        notification.sent_at = now

    session.add(notification)
    await session.flush()
    return notification


async def notify_event(
    session: AsyncSession,
    user: User,
    *,
    ntype: NotificationType,
    event: str,
    action_label: str | None = None,
    action_url: str | None = None,
    now: datetime | None = None,
    **context: object,
) -> Notification | None:
    """Build copy from ATLAS for the user's tone, then create the notification."""
    settings = await notification_repo.settings_for(session, user.id)
    tone = settings.mentor_tone if settings else None
    from app.models.enums import MentorTone

    message = mentor.generate_mentor_message(
        event, tone or MentorTone.HARD, name=user.display_name, **context
    )
    return await create_notification(
        session,
        user,
        ntype=ntype,
        title=message.title,
        body=message.body,
        action_label=action_label,
        action_url=action_url,
        now=now,
    )


async def list_notifications(session: AsyncSession, user: User) -> list[Notification]:
    return await notification_repo.list_for_user(session, user.id)


async def mark_read(session: AsyncSession, user: User, notification_id: int) -> Notification:
    from app.core.errors import NotFoundError

    notification = await notification_repo.get_owned(session, notification_id, user.id)
    if notification is None:
        raise NotFoundError("Notification not found")
    if notification.read_at is None:
        notification.read_at = utcnow()
        await session.flush()
    return notification


async def mark_all_read(session: AsyncSession, user: User) -> int:
    unread = await notification_repo.unread_for_user(session, user.id)
    stamp = utcnow()
    for n in unread:
        n.read_at = stamp
    await session.flush()
    return len(unread)


def already_sent_today(notification: Notification, day: date, tz: str) -> bool:
    """Whether a notification of its type was already sent on ``day`` (local)."""
    if notification.sent_at is None:
        return False
    start = start_of_local_day_utc(tz, day)
    end = start_of_local_day_utc(tz, day + timedelta(days=1))
    return start <= notification.sent_at < end
