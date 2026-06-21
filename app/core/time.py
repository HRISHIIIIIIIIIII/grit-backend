"""Timezone-correct date/time helpers.

All persisted timestamps are timezone-aware UTC. A user's "day" is computed in
their stored timezone (default ``Europe/Berlin``) using :mod:`zoneinfo`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(tz=UTC)


def get_zone(tz_name: str) -> ZoneInfo:
    return ZoneInfo(tz_name)


def local_now(tz_name: str, *, now: datetime | None = None) -> datetime:
    """The given (or current) UTC instant expressed in ``tz_name``."""
    instant = now or utcnow()
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(get_zone(tz_name))


def local_date(tz_name: str, *, now: datetime | None = None) -> date:
    """The user's current local calendar date."""
    return local_now(tz_name, now=now).date()


def start_of_local_day_utc(tz_name: str, day: date) -> datetime:
    """UTC instant at 00:00 local time on ``day``."""
    local = datetime(day.year, day.month, day.day, tzinfo=get_zone(tz_name))
    return local.astimezone(UTC)
