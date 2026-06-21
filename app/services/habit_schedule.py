"""Pure helpers for interpreting a habit's ``schedule`` string.

Supported formats:
- ``"daily"``           — scheduled every day.
- a 7-char weekly mask  — e.g. ``"1111100"`` (Mon..Sun), '1' = scheduled.
- an RRULE string       — anything starting with ``RRULE:`` or ``FREQ=``.

RRULE handling is intentionally minimal (we only need day-level "is this habit
due today"): ``FREQ=DAILY`` is every day; ``FREQ=WEEKLY`` with ``BYDAY`` honours
the listed weekdays; anything else falls back to "scheduled" so we never hide a
habit from the user. Full RRULE expansion is out of scope for streak math.
"""

from __future__ import annotations

from datetime import date

_RRULE_DAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def is_scheduled_on(schedule: str, day: date) -> bool:
    """Whether a habit with ``schedule`` is due on ``day`` (local date)."""
    value = (schedule or "daily").strip()
    if not value or value.lower() == "daily":
        return True

    weekday = day.weekday()  # Mon=0 .. Sun=6

    # Weekly bitmask like "1111100".
    if len(value) == 7 and set(value) <= {"0", "1"}:
        return value[weekday] == "1"

    upper = value.upper()
    if upper.startswith("RRULE:") or upper.startswith("FREQ="):
        return _rrule_scheduled_on(upper, weekday)

    # Unknown format: don't hide the habit.
    return True


def _rrule_scheduled_on(rrule: str, weekday: int) -> bool:
    body = rrule.removeprefix("RRULE:")
    parts = dict(
        piece.split("=", 1) for piece in body.split(";") if "=" in piece
    )
    freq = parts.get("FREQ", "DAILY")
    if freq == "DAILY":
        return True
    if freq == "WEEKLY":
        byday = parts.get("BYDAY")
        if not byday:
            return True
        allowed = {_RRULE_DAYS[d] for d in byday.split(",") if d in _RRULE_DAYS}
        return weekday in allowed
    # MONTHLY/YEARLY/etc — treat as scheduled (coarse).
    return True
